# Loaders for the clean modeling tables built by 10_build_dataset.py.
#
# Leakage contract: every loader takes `before=` (the forecast year) and returns only
# information available in January of that year. 2008 phenotypes live in separate
# holdout files that only load_holdout_2008() reads.
import os, warnings, numpy as np, pandas as pd
from paths import S

M = f'{S}/model'
TRAITS = ['YLD', 'MST', 'TWT']


def _check(before):
    assert before is not None and 2001 <= before <= 2008, 'pass before=<forecast year>, e.g. before=2007'


def load_plots(before):
    """Plot-level training rows (one unreplicated plot of line x tester x trial) with YEAR < before."""
    _check(before)
    p = pd.read_parquet(f'{M}/plots_train.parquet')
    return p[p.YEAR < before].reset_index(drop=True)


def load_lines(before, cl=None):
    """Stage-1 line values for YEAR < before.
    y_w_<T>: line deviation from its population mean within trial (clean, within-family).
    pop_eff_<T>: that population's env-adjusted effect (relative within cluster-year).
    y_tot_<T> = pop_eff_<T> + y_w_<T>: the line's total testcross value on the year's scale.
    rel_<T>: reliability of y_w_<T> (vL / (vL + vE/n_plots)) from its own population."""
    _check(before)
    d = pd.read_parquet(f'{M}/lines_train.parquet')
    d = d[d.YEAR < before]
    return (d if cl is None else d[d.CL == cl]).reset_index(drop=True)


def load_pops(before, cl=None, include_target_year=True):
    """Population table. Rows with YEAR < before carry stage-1 effects.
    With include_target_year, the forecast year's populations are appended with
    pre-planting information only (parents, tester, generation, planned envs)."""
    _check(before)
    d = pd.read_parquet(f'{M}/pops.parquet')
    hist = d[d.YEAR < before]
    out = [hist]
    if include_target_year:
        t = d[d.YEAR == before].copy()
        t[[c for c in t.columns if c.startswith(('pop_eff_', 'pop_se_', 'vL_', 'vE_', 'H_', 'conn'))]] = np.nan
        out.append(t)
    d = pd.concat(out, ignore_index=True)
    return (d if cl is None else d[d.CL == cl]).reset_index(drop=True)


def load_candidates(year):
    """Lines of the forecast year's populations with pre-planting fields only (no phenotypes)."""
    _check(year)
    c = pd.read_parquet(f'{M}/candidates.parquet')
    return c[c.YEAR == year].reset_index(drop=True)


def load_env(before=None):
    """Environment table: one row per ENV (LOC_YEAR) with weather + soil and
    has_env flag. Weather of the forecast year is only known after the season;
    if before is given, rows with YEAR >= before are dropped."""
    e = pd.read_parquet(f'{M}/envs.parquet')
    return e if before is None else e[e.YEAR < before].reset_index(drop=True)


def load_holdout_2008():
    """Answer key: 2008 plot rows and stage-1 line/pop values. Final evaluation only."""
    return (pd.read_parquet(f'{M}/holdout_2008_plots.parquet'),
            pd.read_parquet(f'{M}/holdout_2008_lines.parquet'),
            pd.read_parquet(f'{M}/holdout_2008_pops.parquet'))


_geno_cache = {}
def load_geno(cl, keys=None, fill='pop_mean', source='hmm'):
    """Progeny genotypes (float32) for LINE_KEYs of cluster cl.
    source: 'hmm' (default) = parent-aware HMM dosages from 60_imputation_bench.py (continuous -1..1,
    complete; +18% within-family accuracy vs the provided files); 'imputed' = provided imputed files
    (-1/0/1 with NaN). Both share geno_{cl}_keys row order.
    fill: None keeps NaN; 'pop_mean' fills each NaN with that population's marker mean
    (then 0, the across-population midpoint). Returns (X, keys_found)."""
    ck = (cl, source)
    if ck not in _geno_cache:
        f = f'{M}/geno_{cl}.npy' if source == 'imputed' else f'{M}/geno_hmm_{cl}.npy'
        if not os.path.exists(f):
            raise FileNotFoundError(f'{f} missing: run 60_imputation_bench.py first (or pass source="imputed")')
        X = np.load(f, mmap_mode='r')
        k = pd.read_parquet(f'{M}/geno_{cl}_keys.parquet')
        _geno_cache[ck] = (X, k)
    X, k = _geno_cache[ck]
    if keys is not None:
        idx = pd.Series(k.index.values, index=k.LINE_KEY)
        keys = [x for x in keys if x in idx.index]
        k = k.iloc[idx[keys].values]
    out = np.array(X[k.index.values], dtype=np.float32)
    if fill == 'pop_mean':
        for pop, rows in k.reset_index(drop=True).groupby('POP').groups.items():
            sub = out[rows]
            with np.errstate(all='ignore'), warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)  # markers all-NaN within a pop -> 0
                mu = np.nanmean(sub, 0) if np.isnan(sub).any() else None
            if mu is not None:
                mu = np.nan_to_num(mu)
                r, c = np.where(np.isnan(sub)); sub[r, c] = mu[c]; out[rows] = sub
    return out, k.LINE_KEY.tolist()


def load_parent_geno(cl):
    """Parent inbred genotypes (index = parent id without 'PID'), 2,911 markers."""
    return pd.read_pickle(f'{S}/exploration/{cl}_parents_geno.pkl')


def marker_map():
    return pd.read_csv(f'{S}/exploration/C1_marker_map.csv')

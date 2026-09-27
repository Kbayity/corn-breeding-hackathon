# phase2/common.py
"""Shared loaders for phase 2. Everything downstream imports this. 2008 trait values are NaN from load time."""
import os, re, zipfile
import numpy as np, pandas as pd

PROJECT = '/home/ronitk/Ronit-Personal/Work/BayerHackathonDataset'
EXPL = os.path.join(PROJECT, 'exploration')
# Overridable for judge mode (run on sample_data/ with an isolated cache/output dir instead of the
# full 141MB datasets): MAIZE_DATA, MAIZE_CACHE, MAIZE_OUT. Relative values resolve against cwd.
DATA = os.path.abspath(os.environ['MAIZE_DATA']) if os.environ.get('MAIZE_DATA') else os.path.join(PROJECT, 'Simplified Hackathon Dataset V3')
CACHE = os.path.abspath(os.environ['MAIZE_CACHE']) if os.environ.get('MAIZE_CACHE') else os.path.join(EXPL, 'cache')
OUT = os.path.abspath(os.environ['MAIZE_OUT']) if os.environ.get('MAIZE_OUT') else os.path.join(EXPL, 'outputs')
os.makedirs(CACHE, exist_ok=True); os.makedirs(OUT, exist_ok=True)
TRAITS = ['YLD_BE', 'MST', 'TWT']
ALL_TRAITS = ['ERM', 'MST', 'PHT', 'RTLP', 'STLP', 'TWT', 'YLD_BE', 'EHT']
TEST_YEAR = 2008
FOLDS = [(2004, 2005), (2005, 2006), (2006, 2007)]   # (last training year, test year)
CLUSTERS = ['C1', 'C2']


def norm_num(s):
    """Normalize a progeny id: strip leading zeros of the numeric prefix, keep any suffix."""
    s = str(s)
    m = re.match(r'^0*(\d+)(.*)$', s)
    return (m.group(1) + m.group(2)) if m else s


def load_pheno():
    p = os.path.join(CACHE, 'pheno_v2.pkl')
    if os.path.exists(p):
        return pd.read_pickle(p)
    dfs = []
    for cl in CLUSTERS:
        f = os.path.join(DATA, f'{cl}_Phenotype_Data_V2.csv')
        if not os.path.exists(f):
            continue   # data-size guard: judge mode's sample_data/ omits C2 to stay small
        d = pd.read_csv(f, low_memory=False)
        d = d.rename(columns={'YEAR_x': 'YEAR', 'shorthand_x': 'POP'})
        d['CL'] = cl
        if cl == 'C2':
            v = d['LINE'].astype(float)
            is_int = v == np.floor(v)
            # C2 LINE is float; a small subset (e.g. pop C2.52) carries a genuine ".1"-style
            # suffix distinguishing a sub-line rather than being an integer with float noise.
            rest = pd.Series(np.where(is_int, np.floor(v).astype('int64').astype(str), v.astype(str)),
                             index=d.index)
        else:
            rest = d['LINE'].astype(str)
        d['LINE_ID'] = d['POP'] + '.' + rest.map(norm_num)
        dfs.append(d)
    ph = pd.concat(dfs, ignore_index=True)
    ph['ENV'] = ph['LOC'] + '_' + ph['YEAR'].astype(str)
    ph['TRIAL'] = ph['SET'].astype(str) + '_' + ph['LOC'] + '_' + ph['YEAR'].astype(str)
    ph['TESTER'] = ph['GERMPLASM_ID_TESTER'].map(lambda v: 'NA' if pd.isna(v) else str(int(v)))
    ph['GEN'] = ph['GENERATION_NAME']
    cr = ph['CROSS'].str.split('/', expand=True)
    p1raw, p2raw = cr[0], cr[1]
    ph['P1'] = p1raw.str.replace(r'\*\d+', '', regex=True)
    ph['P2'] = p2raw.str.replace(r'\*\d+', '', regex=True)
    ph['RECURRENT'] = np.where(p1raw.str.contains(r'\*'), ph['P1'],
                               np.where(p2raw.str.contains(r'\*'), ph['P2'], None))
    ph.loc[ph['YEAR'] == TEST_YEAR, ALL_TRAITS] = np.nan          # QUARANTINE
    keep = ['CL', 'POP', 'YEAR', 'LOC', 'ENV', 'SET', 'TRIAL', 'LINE_ID', 'TESTER', 'GEN',
            'P1', 'P2', 'RECURRENT', 'LONGITUDE', 'LATITUDE'] + ALL_TRAITS
    ph = ph[keep].copy()
    ph.to_pickle(p)
    return ph


def pop_table(ph):
    t = ph.groupby('POP').agg(CL=('CL', 'first'), YEAR=('YEAR', 'first'), GEN=('GEN', 'first'),
                              P1=('P1', 'first'), P2=('P2', 'first'), RECURRENT=('RECURRENT', 'first'),
                              TESTER=('TESTER', 'first'), n_lines=('LINE_ID', 'nunique'), n_locs=('LOC', 'nunique'))
    bc = t['GEN'].eq('BC') & t['RECURRENT'].notna()
    t['W1'] = np.where(bc, np.where(t['RECURRENT'] == t['P1'], 0.75, 0.25), 0.5)
    t['W2'] = 1.0 - t['W1']
    t['GEN_FLAG'] = np.where(t['GEN'].eq('BC') & t['RECURRENT'].isna(), 'BC_without_recurrent_marker', '')
    t['GEN_declared'] = t['GEN']
    t['RECURRENT_declared'] = t['RECURRENT']
    gpath = os.path.join(OUT, 'pop_generation_final.csv')
    if os.path.exists(gpath):
        g = pd.read_csv(gpath, index_col='POP')
        common_idx = t.index.intersection(g.index)
        t.loc[common_idx, 'GEN'] = g.loc[common_idx, 'GEN_OBS'].astype(str)
        t.loc[common_idx, 'RECURRENT'] = g.loc[common_idx, 'RECURRENT_final'].astype(str)
        t.loc[common_idx, 'W1'] = g.loc[common_idx, 'W1'].astype(float)
        t.loc[common_idx, 'W2'] = g.loc[common_idx, 'W2'].astype(float)
    return t


def line_means(ph, trait, block='TRIAL'):
    """Per line: mean of (plot - block mean). Training years only (2008 traits are NaN)."""
    d = ph.dropna(subset=[trait]).copy()
    d['dev'] = d[trait] - d.groupby(block)[trait].transform('mean')
    return d.groupby('LINE_ID').agg(y=('dev', 'mean'), n=('dev', 'size'), POP=('POP', 'first'),
                                    YEAR=('YEAR', 'first'), CL=('CL', 'first'))


def pop_means(ph, trait):
    """Per population: mean over its location-years of (population cell mean - location-year mean)."""
    d = ph.dropna(subset=[trait])
    env_mean = d.groupby('ENV')[trait].mean()
    cell = d.groupby(['POP', 'ENV'])[trait].agg(['mean', 'size']).reset_index()
    cell['dev'] = cell['mean'] - cell['ENV'].map(env_mean)
    pm = cell.groupby('POP').agg(dev=('dev', 'mean'), n_cells=('dev', 'size'), n_plots=('size', 'sum'))
    t = pop_table(ph)
    pm['CL'] = t.loc[pm.index, 'CL']; pm['YEAR'] = t.loc[pm.index, 'YEAR']
    return pm


def pop_h2(ph, trait, min_lines=20):
    """Line-mean heritability per population from TRIAL-adjusted plots (two-way ANOVA, unbalanced:
    ENV (column) effects removed before LINE_ID (row) effects)."""
    d = ph.dropna(subset=[trait]).copy()
    d['dev'] = d[trait] - d.groupby('TRIAL')[trait].transform('mean')
    rows = []
    for pop, g in d.groupby('POP'):
        piv = g.pivot_table(index='LINE_ID', columns='ENV', values='dev', aggfunc='mean').dropna(thresh=2)
        if piv.shape[1] < 2 or piv.shape[0] < min_lines:
            continue
        nE = piv.notna().sum(1).mean()
        piv = piv.sub(piv.mean(0), axis=1)   # two-way centering: remove the ENV (column) mean first
        ln = piv.mean(1)
        resid = piv.sub(ln, axis=0)
        ncell = resid.notna().sum().sum()
        n_lines = len(ln)
        dof = max(ncell - n_lines - (nE - 1) + 1, 1)
        msE = np.nanvar(resid.values) * ncell / dof
        vL = max((ln.var() * nE - msE) / nE, 0.0)
        H = vL / (vL + msE / nE) if (vL + msE / nE) > 0 else np.nan
        rows.append(dict(POP=pop, vL=vL, vE=msE, nE=nE, n=len(ln), H=H))
    return pd.DataFrame(rows).set_index('POP')


def imputed_dir(cl):
    d = os.path.join(CACHE, 'imputed', f'ImputedPopulations{cl}')
    if not os.path.isdir(d) or len(os.listdir(d)) < (499 if cl == 'C1' else 500):
        with zipfile.ZipFile(os.path.join(DATA, f'Imputed{cl}Populations.zip')) as z:
            z.extractall(os.path.join(CACHE, 'imputed'))
    return d


def load_imputed_pop(cl, pop):
    f = os.path.join(imputed_dir(cl), f'{pop}_Imputed.csv')
    df = pd.read_csv(f, index_col=0, na_values=['NA'], low_memory=False)
    df.index = df.index.astype(str)
    is_par = df.index.str.startswith('PID')
    par = df[is_par].astype('float32'); par.index = par.index.str.replace('PID', '')
    prog = df[~is_par].astype('float32'); prog.index = [pop + '.' + norm_num(i) for i in prog.index]
    return par, prog


def load_parents(cl):
    p = os.path.join(CACHE, f'parents_{cl}.pkl')
    if os.path.exists(p):
        return pd.read_pickle(p)
    f = os.path.join(DATA, f'Unimputed_{cl}_Genome_Data', f'{cl}_Genome_Data.csv')
    raw = pd.read_csv(f, dtype=str, na_values=['NA'], low_memory=False)
    mk = list(raw.columns[4:])
    par = raw[raw['LINE'].str.startswith('PID', na=False)].drop_duplicates('LINE')
    P = par[mk].apply(pd.to_numeric, errors='coerce').astype('float32')
    P.index = par['LINE'].str.replace('PID', '').values
    P.to_pickle(p)
    return P


def marker_map():
    f = os.path.join(DATA, 'Unimputed_C1_Genome_Data', 'C1_Genome_Data.csv')
    hdr = pd.read_csv(f, nrows=2)
    mk = list(hdr.columns[4:])
    return pd.DataFrame({'marker': mk, 'chrom': hdr.iloc[0, 4:].astype(float).values.astype(int),
                         'cM': hdr.iloc[1, 4:].astype(float).values})


def geno_matrix(cl, version='imputed'):
    """Stack progeny genotypes of all populations. version='imputed': provider files with NaN kept.
    version='filled': Task 4 output (no NaN). Cached as cache/{version}_{cl}_X.npy + keys.pkl."""
    px = os.path.join(CACHE, f'{version}_{cl}_X.npy'); pk = os.path.join(CACHE, f'{version}_{cl}_keys.pkl')
    if os.path.exists(px) and os.path.exists(pk):
        return np.load(px, mmap_mode='r'), pd.read_pickle(pk)
    if version != 'imputed':
        raise FileNotFoundError(f'{px} not built yet (Task 4 builds it)')
    mats, keys = [], []
    for fn in sorted(os.listdir(imputed_dir(cl))):
        pop = fn.split('_')[0]
        _, prog = load_imputed_pop(cl, pop)
        mats.append(prog.values.astype('float32')); keys += list(prog.index)
    X = np.vstack(mats)
    np.save(px, X); pd.to_pickle(keys, pk)
    return np.load(px, mmap_mode='r'), keys


def parent_grm(cl):
    """VanRaden GRM among the cluster's parents (NA filled by marker mean across parents; markers with MAF < 0.01 dropped)."""
    P = load_parents(cl)
    D = (P.values.astype(float) + 1.0)                      # dosage 0/1/2
    col = np.nanmean(D, 0); i = np.where(np.isnan(D)); D[i] = col[i[1]]
    p = D.mean(0) / 2; keep = (p > 0.01) & (p < 0.99); D = D[:, keep]; p = p[keep]
    Z = D - 2 * p
    G = Z @ Z.T / (2 * (p * (1 - p)).sum())
    return pd.DataFrame(G, index=P.index, columns=P.index)


def boot_corr(pred, obs, n_boot=1000, seed=0):
    from scipy.stats import spearmanr
    pred = np.asarray(pred, float); obs = np.asarray(obs, float)
    ok = ~np.isnan(pred) & ~np.isnan(obs); pred, obs = pred[ok], obs[ok]
    n = len(pred)
    if n < 3:
        return dict(pearson=np.nan, p_lo=np.nan, p_hi=np.nan, spearman=np.nan, s_lo=np.nan, s_hi=np.nan, n=n)
    degenerate = np.std(pred) < 1e-9 or np.std(obs) < 1e-9
    pe = np.nan if degenerate else np.corrcoef(pred, obs)[0, 1]
    sp = np.nan if degenerate else spearmanr(pred, obs)[0]
    rng = np.random.default_rng(seed)
    bp, bs = [], []
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        if np.std(pred[i]) == 0 or np.std(obs[i]) == 0:
            continue
        bp.append(np.corrcoef(pred[i], obs[i])[0, 1]); bs.append(spearmanr(pred[i], obs[i])[0])
    if len(bp) < 10:   # too few non-degenerate resamples for a stable CI
        return dict(pearson=pe, p_lo=np.nan, p_hi=np.nan, spearman=sp, s_lo=np.nan, s_hi=np.nan, n=n)
    return dict(pearson=pe, p_lo=np.percentile(bp, 2.5), p_hi=np.percentile(bp, 97.5),
                spearman=sp, s_lo=np.percentile(bs, 2.5), s_hi=np.percentile(bs, 97.5), n=n)

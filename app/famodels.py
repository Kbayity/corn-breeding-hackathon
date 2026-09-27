# Family-mean (population effect) predictors, shared by 30_popmean_h2h.py and 40_score.py.
# Every model is fit on historical families (`hist`, one row per POP with the target column)
# and returns, for the target families, a DataFrame with
#   gca    : line-side part (what the family's own parents contribute)
#   tester : tester part (nuisance for advancement decisions, part of the testcross hybrid)
# The testcross prediction is gca + tester.
# Contribution c of each parent: F2/DH 0.5/0.5; BC1 recurrent parent 0.75, donor 0.25.
import numpy as np, pandas as pd


def contrib(pops):
    """Long table POP, parent, c (genetic contribution of the parent to the family)."""
    rows = []
    for r in pops.itertuples():
        if isinstance(r.RP, str):
            donor = r.P2 if r.P1 == r.RP else r.P1
            rows += [(r.POP, r.RP, 0.75), (r.POP, donor, 0.25)]
        else:
            rows += [(r.POP, r.P1, 0.5), (r.POP, r.P2, 0.5)]
    return pd.DataFrame(rows, columns=['POP', 'parent', 'c'])


def _out(tgt, gca, tester):
    return pd.DataFrame({'gca': np.asarray(gca, float), 'tester': np.asarray(tester, float)}, index=tgt.index)


def tester_hist(hist, tgt, tcol, k=2.0):
    g = hist.groupby('TESTER')[tcol].agg(['sum', 'count'])
    val = g['sum'] / (g['count'] + k)                             # shrink toward 0 (cluster-year mean)
    return _out(tgt, np.zeros(len(tgt)), tgt.TESTER.map(val).fillna(0.0))


def parent_hist(hist, tgt, tcol, k=1.0):
    ch = contrib(hist).merge(hist[['POP', tcol]], on='POP')
    g = ch.assign(wy=ch.c * ch[tcol]).groupby('parent').agg(wy=('wy', 'sum'), w=('c', 'sum'))
    val = g.wy / (g.w + k * 0.5)
    ct = contrib(tgt); ct['v'] = ct.parent.map(val).fillna(0.0)
    gca = (ct.c * ct.v).groupby(ct.POP).sum().reindex(tgt.POP).values * 2
    return _out(tgt, gca, np.zeros(len(tgt)))


def _tester_onehot(d, ti, scale):
    T = np.zeros((len(d), len(ti)))
    for i, t in enumerate(d.TESTER):
        if t != 'NA' and t in ti: T[i, ti[t]] = scale
    return T


def _fit_split(Xh_g, Xh_t, Xt_g, Xt_t, y, lam):
    # ridge in dual form on [X_gca, X_tester]; coefficients recovered to split the prediction
    Xh = np.hstack([Xh_g, Xh_t]); mu = y.mean()
    a = np.linalg.solve(Xh @ Xh.T + lam * np.eye(len(y)), y - mu)
    b = Xh.T @ a; bg, bt = b[:Xh_g.shape[1]], b[Xh_g.shape[1]:]
    return mu + Xt_g @ bg, Xt_t @ bt


def ped_gca(hist, tgt, tcol, lam_a=1.0, lam_t=1.0):
    pars = sorted(set(contrib(hist).parent) | set(contrib(tgt).parent)); pi = {p: i for i, p in enumerate(pars)}
    ti = {t: i for i, t in enumerate(sorted(set(hist.TESTER) | set(tgt.TESTER)))}
    def G(d):
        M = np.zeros((len(d), len(pars))); pos = {p: i for i, p in enumerate(d.POP)}
        for r in contrib(d).itertuples(): M[pos[r.POP], pi[r.parent]] += r.c / np.sqrt(lam_a)
        return M
    g, t = _fit_split(G(hist), _tester_onehot(hist, ti, 1 / np.sqrt(lam_t)), G(tgt), _tester_onehot(tgt, ti, 1 / np.sqrt(lam_t)),
                      hist[tcol].values, 1.0)
    return _out(tgt, g, t)


def par_profile(d, PG):
    """Contribution-weighted parent marker profile per family (expected family mean genotype)."""
    M = np.zeros((len(d), PG.shape[1])); pos = {p: i for i, p in enumerate(d.POP)}
    for r in contrib(d).itertuples():
        if r.parent in PG.index: M[pos[r.POP]] += r.c * PG.loc[r.parent].values
    return M


def par_genomic(hist, tgt, tcol, PG, lam=1.0, s_t=1.0):
    ti = {t: i for i, t in enumerate(sorted(set(hist.TESTER) | set(tgt.TESTER)))}
    sc = 1 / np.sqrt(PG.shape[1] / 4)                                # ~unit-scale kernel
    g, t = _fit_split(par_profile(hist, PG) * sc, _tester_onehot(hist, ti, s_t), par_profile(tgt, PG) * sc,
                      _tester_onehot(tgt, ti, s_t), hist[tcol].values, lam)
    return _out(tgt, g, t)


GRIDS = {
    'tester_hist': [dict(k=k) for k in [0.5, 2, 8]],
    'parent_hist': [dict(k=k) for k in [0.25, 1, 4]],
    'ped_gca': [dict(lam_a=a, lam_t=t) for a in [0.3, 1, 3] for t in [1, 10]],
    'par_genomic': [dict(lam=l, s_t=s) for l in [0.3, 1, 3, 10] for s in [0.0, 1.0]],
}


def fit(method, hist, tgt, tcol, PG=None, **kw):
    if method == 'par_genomic': return par_genomic(hist, tgt, tcol, PG, **kw)
    return {'tester_hist': tester_hist, 'parent_hist': parent_hist, 'ped_gca': ped_gca}[method](hist, tgt, tcol, **kw)


def _r(p, t):
    ok = p.notna() & t.notna()
    return np.corrcoef(p[ok], t[ok])[0, 1] if ok.sum() > 2 and p[ok].std() > 0 else np.nan


def tune(method, hist, tcol, Y, PG=None):
    """Pick hyperparameters by inner forward split: fit on YEAR < Y-1, score r of gca+tester on Y-1."""
    ih = hist[hist.YEAR < Y - 1].reset_index(drop=True); iv = hist[hist.YEAR == Y - 1].reset_index(drop=True)
    grid = GRIDS[method]
    sc = [_r(fit(method, ih, iv, tcol, PG, **g).sum(1), iv[tcol]) for g in grid]
    return grid[int(np.nanargmax(sc))]

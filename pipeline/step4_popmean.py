"""Step 4: forward-year population-mean prediction head-to-head (histmean vs pedigree GCA ridge vs parent-kernel GBLUP)."""
import os, numpy as np, pandas as pd
from scipy import sparse
from scipy.sparse.linalg import lsqr
import common as C
from step1e_parents import parent_groups

ph = C.load_pheno(); t = C.pop_table(ph); pm = C.pop_means(ph, 'YLD_BE')
y_all = ph.dropna(subset=['YLD_BE'])
cells = y_all.groupby(['POP', 'ENV']).YLD_BE.agg(['mean', 'size']).reset_index()
cells['dev'] = cells['mean'] - cells.ENV.map(y_all.groupby('ENV').YLD_BE.mean())
cells = cells.join(t[['CL', 'YEAR', 'TESTER', 'P1', 'P2', 'W1', 'W2']], on='POP')

def fit_ridge(train_cells, test_pops, gp, lam_gca):
    tr = train_cells.copy(); tr['G1'] = tr.P1.map(gp); tr['G2'] = tr.P2.map(gp)
    te = test_pops.copy(); te['G1'] = te.P1.map(gp); te['G2'] = te.P2.map(gp)
    envs = sorted(tr.ENV.unique()); groups = sorted(set(tr.G1) | set(tr.G2) | set(te.G1) | set(te.G2)); tes = sorted(set(tr.TESTER) | set(te.TESTER))
    ei = {e: i for i, e in enumerate(envs)}; gi = {g: i for i, g in enumerate(groups)}; ti = {x: i for i, x in enumerate(tes)}
    nE, nG, nT = len(envs), len(groups), len(tes)
    def design(d, with_env):
        R = np.arange(len(d)); rows, cols, vals = [], [], []
        if with_env:
            rows += list(R); cols += [ei[e] for e in d.ENV]; vals += [1.0] * len(d)
        rows += list(R) * 2; cols += [nE + gi[g] for g in d.G1] + [nE + gi[g] for g in d.G2]; vals += list(d.W1) + list(d.W2)
        rows += list(R); cols += [nE + nG + ti[x] for x in d.TESTER]; vals += [1.0] * len(d)
        return sparse.csr_matrix((vals, (rows, cols)), shape=(len(d), nE + nG + nT))
    X = design(tr, True); mu = tr.dev.mean()
    pen = np.r_[np.full(nE, 0.01), np.full(nG, lam_gca), np.full(nT, 5.0)]
    A = sparse.vstack([X, sparse.diags(np.sqrt(pen))]); b = np.r_[tr.dev.values - mu, np.zeros(nE + nG + nT)]
    beta = lsqr(A, b, atol=1e-10, btol=1e-10, iter_lim=20000)[0]
    unseen_t = ~te.TESTER.isin(set(tr.TESTER)); te2 = te.copy(); te2.loc[unseen_t, 'TESTER'] = tes[0]
    pred = mu + design(te2, False) @ beta
    if unseen_t.any():
        pred[unseen_t.values] -= beta[nE + nG + ti[tes[0]]]
    return pred

def fit_gblup(train_pops, test_pops, G, lam_mult, iters=5):
    P = list(G.index); pi = {p: i for i, p in enumerate(P)}
    def Wmat(d):
        W = np.zeros((len(d), len(P)))
        for k, (p1, p2, w1, w2) in enumerate(zip(d.P1, d.P2, d.W1, d.W2)):
            W[k, pi[p1]] += w1; W[k, pi[p2]] += w2
        return W
    Wtr, Wte = Wmat(train_pops), Wmat(test_pops); Gv = G.values
    Ktt = Wtr @ Gv @ Wtr.T; Kte = Wte @ Gv @ Wtr.T; lam = lam_mult * np.mean(np.diag(Ktt))
    y = train_pops.dev.values; mu = y.mean(); tes = sorted(set(train_pops.TESTER)); ti = {x: i for i, x in enumerate(tes)}
    Zt = np.zeros((len(y), len(tes))); Zt[np.arange(len(y)), [ti[x] for x in train_pops.TESTER]] = 1
    u = np.zeros(len(y)); tcoef = np.zeros(len(tes)); Ainv = np.linalg.inv(Ktt + lam * np.eye(len(y)))
    for _ in range(iters):
        r = y - mu - u; tcoef = np.linalg.solve(Zt.T @ Zt + 5.0 * np.eye(len(tes)), Zt.T @ r)
        r = y - mu - Zt @ tcoef; alpha = Ainv @ r; u = Ktt @ alpha
    ute = Kte @ alpha
    tte = np.array([tcoef[ti[x]] if x in ti else 0.0 for x in test_pops.TESTER])
    return mu + ute + tte

def histmean(train_pops, test_pops, gp):
    tr = train_pops.copy(); tr['G1'] = tr.P1.map(gp); tr['G2'] = tr.P2.map(gp)
    long = pd.concat([tr[['G1', 'dev']].rename(columns={'G1': 'G'}), tr[['G2', 'dev']].rename(columns={'G2': 'G'})])
    m = long.groupby('G').dev.mean(); overall = tr.dev.mean()
    te = test_pops.copy(); te['G1'] = te.P1.map(gp); te['G2'] = te.P2.map(gp)
    return (te.W1 * te.G1.map(m).fillna(overall) + te.W2 * te.G2.map(m).fillna(overall)).values

def strata(train_pops, test_pops, gp):
    tr = train_pops.copy(); tr['G1'] = tr.P1.map(gp); tr['G2'] = tr.P2.map(gp); seen = set(tr.G1) | set(tr.G2)
    pairs = set(tuple(sorted(x)) for x in zip(tr.G1, tr.G2))
    te = test_pops.copy(); te['G1'] = te.P1.map(gp); te['G2'] = te.P2.map(gp)
    ps = te.G1.isin(seen).astype(int) + te.G2.isin(seen).astype(int)
    nr = [tuple(sorted(x)) in pairs for x in zip(te.G1, te.G2)]
    ts = te.TESTER.isin(set(tr.TESTER))
    return ps.values, np.array(nr), ts.values

out = []
md = ['# Step 4: population-mean head-to-head (forward-year)\n',
      'Target = mean over the population\'s location-years of (population cell mean − location-year mean), yield. Models: histmean, gca_ridge, parent_gblup (see plan). Training populations weighted equally.\n']
for cl in C.CLUSTERS:
    gp = parent_groups(cl); G = C.parent_grm(cl)
    pops = t[t.CL == cl].join(pm.dev)
    for last, test_year in C.FOLDS:
        trp = pops[pops.YEAR <= last].dropna(subset=['dev']); tep = pops[pops.YEAR == test_year].dropna(subset=['dev'])
        trc = cells[(cells.CL == cl) & (cells.YEAR <= last)]
        itr = pops[pops.YEAR <= last - 1].dropna(subset=['dev']); ite = pops[pops.YEAR == last].dropna(subset=['dev']); itc = cells[(cells.CL == cl) & (cells.YEAR <= last - 1)]
        best_l = max([1, 5, 25], key=lambda l: np.corrcoef(fit_ridge(itc, ite, gp, l), ite.dev)[0, 1])
        best_m = max([0.5, 1, 2, 4], key=lambda m: np.corrcoef(fit_gblup(itr, ite, G, m), ite.dev)[0, 1])
        p1 = histmean(trp, tep, gp); p2 = fit_ridge(trc, tep, gp, best_l); p3 = fit_gblup(trp, tep, G, best_m)
        ps, nr, ts = strata(trp, tep, gp)
        out.append(pd.DataFrame(dict(fold_test_year=test_year, CL=cl, POP=tep.index, obs_dev=tep.dev.values, pred_histmean=p1, pred_gca_ridge=p2, pred_parent_gblup=p3,
                                     parents_seen=ps, near_repeat=nr, tester_seen=ts, lam_gca=best_l, lam_mult=best_m)))
res = pd.concat(out, ignore_index=True); res.to_csv(os.path.join(C.OUT, 'step4_predictions.csv'), index=False)

def bc(pred, obs):
    # common.boot_corr(n<3) returns NaN metrics but assumes >=1 bootstrap resample has nonzero
    # variance in both arrays; small/degenerate strata (e.g. parents_seen=0, where histmean
    # predicts a single constant) can have zero variance in every resample, leaving its internal
    # bootstrap lists empty and crashing np.percentile([]). Guard here rather than in common.py
    # (out of scope for this task's commit) since this task is the caller producing the degenerate case.
    p = np.asarray(pred, float); o = np.asarray(obs, float)
    ok = ~np.isnan(p) & ~np.isnan(o); p, o = p[ok], o[ok]
    if len(p) < 3 or np.std(p) == 0 or np.std(o) == 0:
        return dict(pearson=np.nan, p_lo=np.nan, p_hi=np.nan, spearman=np.nan, s_lo=np.nan, s_hi=np.nan, n=len(p))
    return C.boot_corr(pred, obs)

rows = []
for (yr, cl), g in res.groupby(['fold_test_year', 'CL']):
    for m in ['histmean', 'gca_ridge', 'parent_gblup']:
        rows.append(dict(test_year=yr, CL=cl, model=m, stratum='all', **bc(g[f'pred_{m}'], g.obs_dev)))
        for s in [0, 1, 2]:
            gg = g[g.parents_seen == s]; rows.append(dict(test_year=yr, CL=cl, model=m, stratum=f'parents_seen={s}', **bc(gg[f'pred_{m}'], gg.obs_dev)))
        for s in [True, False]:
            gg = g[g.near_repeat == s]; rows.append(dict(test_year=yr, CL=cl, model=m, stratum=f'near_repeat={s}', **bc(gg[f'pred_{m}'], gg.obs_dev)))
for m in ['histmean', 'gca_ridge', 'parent_gblup']:
    for cl in C.CLUSTERS:
        g = res[res.CL == cl]; rows.append(dict(test_year='pooled', CL=cl, model=m, stratum='all', **bc(g[f'pred_{m}'], g.obs_dev)))
tab = pd.DataFrame(rows); tab.to_csv(os.path.join(C.OUT, 'step4_metrics.csv'), index=False)
md.append(tab.round(3).to_markdown(index=False) + '\n')
md.append('SD of observed population devs per fold (bu/ac): ' + repr(res.groupby(['fold_test_year', 'CL']).obs_dev.std().round(2).to_dict()) + '\n')
open(os.path.join(C.OUT, 'step4_popmean.md'), 'w').write('\n'.join(md))

def selfcheck():
    assert res.fold_test_year.nunique() == 3 and set(res.CL) == {'C1', 'C2'}
    assert res[['pred_histmean', 'pred_gca_ridge', 'pred_parent_gblup']].notna().all().all()
    assert (tab[(tab.stratum == 'all') & (tab.test_year != 'pooled')].n > 30).all()
selfcheck()

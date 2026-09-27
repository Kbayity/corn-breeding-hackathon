# phase2/step5_withinpop.py
"""Step 5: forward-year within-population prediction head-to-head (global rrBLUP, relatedness-weighted rrBLUP, Jacobson GCA model)."""
import os, time, numpy as np, pandas as pd
import common as C
from step1e_parents import parent_groups

AUDIT = ("Phase-1 probe (`08_acrosspop_probe.py`): cluster C1 only. Training set = every C1 line with YEAR < Y (Y = 2006: 54,844 lines; Y = 2007: 64,117 lines), "
         "target = mean over the line's plots of (plot yield − TRIAL mean), TRIAL = SET + LOC. Test set = every C1 line with YEAR = Y (2006: 9,273 lines in 58 populations; "
         "2007: 6,159 lines in 51 populations). Because every population is tested in exactly one year, no population and no line appears in both sets; no same-year data "
         "entered training. Two caveats: (1) test-line targets were centered with the test year's own TRIAL means, which include the line's own plot (≈1/170 of the mean), "
         "a negligible but non-zero self-contribution; (2) genotype NA was filled with the marker mean within the test population (genotypes only, no phenotypes). "
         "Ridge λ ∈ {2p, 10p} was fixed, not tuned. Result: within-population r (median over populations) 0.25 (2006) and 0.25–0.26 (2007); population-mean r ≈ 0 "
         "because TRIAL-adjustment removes population means for single-population SETs.")

ph = C.load_pheno(); t = C.pop_table(ph); lm = C.line_means(ph, 'YLD_BE', 'TRIAL'); h2 = C.pop_h2(ph, 'YLD_BE')
s4 = pd.read_csv(os.path.join(C.OUT, 'step4_predictions.csv')).set_index(['fold_test_year', 'POP'])

def solve_ridge(S, b, lam):
    return np.linalg.solve(S + lam * np.eye(len(S)), b)

def within_pop_beta(X, y, grid=(0.5, 1, 2, 5, 10), seed=0):
    n, p = X.shape; K = X @ X.T; folds = np.random.default_rng(seed).permutation(n) % 5; best, bl = -np.inf, None
    for m in grid:
        lam = m * p; pred = np.zeros(n)
        for f in range(5):
            tr = folds != f; te = ~tr; mu = y[tr].mean()
            a = np.linalg.solve(K[np.ix_(tr, tr)] + lam * np.eye(tr.sum()), y[tr] - mu); pred[te] = mu + K[np.ix_(te, tr)] @ a
        c = np.corrcoef(pred, y)[0, 1]
        if c > best:
            best, bl = c, lam
    a = np.linalg.solve(K + bl * np.eye(n), y - y.mean()); return X.T @ a

def per_pop_metrics(pred, y, pop):
    ok = ~np.isnan(pred) & ~np.isnan(y)
    if ok.sum() < 30:
        return dict(rMP=np.nan, rMG=np.nan, top10=np.nan, n=int(ok.sum()))
    r = np.corrcoef(pred[ok], y[ok])[0, 1]; H = h2.H.get(pop, np.nan); k = max(int(0.1 * ok.sum()), 1)
    top = len(set(np.argsort(-pred[ok])[:k]) & set(np.argsort(-y[ok])[:k])) / k
    return dict(rMP=r, rMG=r / np.sqrt(H) if H > 0.05 else np.nan, top10=top, n=int(ok.sum()))

def med_within(pred, d):
    return d.assign(pred=pred).groupby('POP').apply(lambda g: np.corrcoef(g.pred, g.y)[0, 1] if len(g) > 30 else np.nan).median()

md = ['# Step 5: within-population head-to-head (forward-year)\n', '## Audit of the phase-1 global rrBLUP probe\n', AUDIT + '\n', '## Models\n',
      'global rrBLUP; relatedness-weighted rrBLUP (weights 1 / 0.5 / 0.05 by shared parent groups); Jacobson 2014 GCA model. Targets = TRIAL-adjusted line means, yield. Genotypes = Task 4 filled matrix.\n']
perpop = []; t0 = time.time()
for cl in C.CLUSTERS:
    gp = parent_groups(cl); X_all, keys = C.geno_matrix(cl, 'filled'); kidx = pd.Series(np.arange(len(keys)), index=keys)
    P = C.load_parents(cl)
    lines = lm[(lm.CL == cl) & lm.index.isin(kidx.index)].copy(); lines['gi'] = kidx[lines.index].values
    tpop = t[t.CL == cl].copy(); tpop['G1'] = tpop.P1.map(gp); tpop['G2'] = tpop.P2.map(gp)
    for last, test_year in C.FOLDS:
        tr = lines[lines.YEAR <= last]; te = lines[lines.YEAR == test_year]
        Xtr = np.asarray(X_all[tr.gi.values], np.float64); cmean = Xtr.mean(0); Xtr -= cmean; ytr = tr.y.values
        Xte = np.asarray(X_all[te.gi.values], np.float64) - cmean; p = Xtr.shape[1]
        S_all = Xtr.T @ Xtr; b_all = Xtr.T @ ytr
        itr = tr[tr.YEAR <= last - 1]; ite = tr[tr.YEAR == last]
        Xi = np.asarray(X_all[itr.gi.values], np.float64); cm_i = Xi.mean(0); Xi -= cm_i; Si = Xi.T @ Xi; bi = Xi.T @ itr.y.values
        Xie = np.asarray(X_all[ite.gi.values], np.float64) - cm_i
        lam = max([p, 5 * p, 25 * p], key=lambda l: med_within(Xie @ solve_ridge(Si, bi, l) + itr.y.mean(), ite))
        beta_g = solve_ridge(S_all, b_all, lam); pred_global = ytr.mean() + Xte @ beta_g
        trpops = tpop.loc[tr.POP.unique()]
        # ponytail: on-the-fly Gram (below, per test population) instead of a precomputed dict of
        # (2911x2911) Grams for every training population — up to ~800 pops x 68MB would OOM.
        # Row indices per training pop are cheap (int arrays) and kept for both the GCA loop and this.
        pop_idx = {pop: np.where(tr.POP.values == pop)[0] for pop in trpops.index}
        wbeta = {}
        for pop in trpops.index:
            ii = pop_idx[pop]; Xp = Xtr[ii]; yp = ytr[ii]
            pa = P.loc[trpops.loc[pop].P1].values.astype(float); pb = P.loc[trpops.loc[pop].P2].values.astype(float)
            poly = (pa != pb) & ~np.isnan(pa) & ~np.isnan(pb)
            if poly.sum() < 50 or len(ii) < 40:
                continue
            dA = 1.0 + (Xp[:, poly] + cmean[poly]) * pa[poly][None, :]; dA = dA - dA.mean(0)
            beta = np.full(p, np.nan); beta[poly] = within_pop_beta(dA, yp)
            wbeta[pop] = beta                                             # effect per copy of the P1 allele
        pred_w = np.full(len(te), np.nan); pred_gca = np.full(len(te), np.nan)
        for pop in te.POP.unique():
            r = tpop.loc[pop]; jj = np.where(te.POP.values == pop)[0]; tg = {r.G1, r.G2}
            share2 = [q for q in trpops.index if {trpops.loc[q].G1, trpops.loc[q].G2} == tg]
            share1 = [q for q in trpops.index if q not in share2 and ({trpops.loc[q].G1, trpops.loc[q].G2} & tg)]
            S = 0.05 * S_all; b = 0.05 * b_all
            if share2:
                idx2 = np.concatenate([pop_idx[q] for q in share2]); Xs = Xtr[idx2]
                S = S + 0.95 * (Xs.T @ Xs); b = b + 0.95 * (Xs.T @ ytr[idx2])
            if share1:
                idx1 = np.concatenate([pop_idx[q] for q in share1]); Xs = Xtr[idx1]
                S = S + 0.45 * (Xs.T @ Xs); b = b + 0.45 * (Xs.T @ ytr[idx1])
            pred_w[jj] = ytr.mean() + Xte[jj] @ solve_ridge(S, b, lam)
            pa = P.loc[r.P1].values.astype(float); pb = P.loc[r.P2].values.astype(float); poly_t = (pa != pb) & ~np.isnan(pa) & ~np.isnan(pb)
            def side_effects(group, own_geno):
                eff, cnt = np.zeros(p), np.zeros(p)
                for q in wbeta:
                    qr = trpops.loc[q]
                    if group not in (qr.G1, qr.G2):
                        continue
                    sign = 1.0 if qr.G1 == group else -1.0
                    shared_geno = P.loc[qr.P1 if qr.G1 == group else qr.P2].values.astype(float)
                    flip = np.where(shared_geno == own_geno, 1.0, -1.0)
                    bq = wbeta[q] * sign * flip; ok = ~np.isnan(bq)
                    eff[ok] += bq[ok]; cnt[ok] += 1
                need = 2 if cnt.max() >= 2 else 1
                return np.where(cnt >= need, eff / np.maximum(cnt, 1), 0.0), cnt.max() > 0
            eA, okA = side_effects(r.G1, pa); eB, okB = side_effects(r.G2, pb)
            if okA or okB:
                dA = 1.0 + (Xte[jj][:, poly_t] + cmean[poly_t]) * pa[poly_t][None, :]
                pred_gca[jj] = ((eA - eB)[poly_t][None, :] * (dA - 1.0)).sum(1)
        pd.to_pickle(te.assign(pred_global=pred_global, pred_weighted=pred_w, pred_gca=pred_gca), os.path.join(C.CACHE, f'step5_linepred_{cl}_{test_year}.pkl'))
        for pop in te.POP.unique():
            jj = np.where(te.POP.values == pop)[0]; y = te.y.values[jj]
            s = s4.loc[(test_year, pop)] if (test_year, pop) in s4.index else None
            rec = dict(CL=cl, test_year=test_year, POP=pop, n_lines=len(jj), parents_seen=s.parents_seen if s is not None else np.nan,
                       near_repeat=s.near_repeat if s is not None else np.nan, tester_seen=s.tester_seen if s is not None else np.nan, H=h2.H.get(pop, np.nan), lam=lam)
            for m, pr in [('global', pred_global[jj]), ('weighted', pred_w[jj]), ('gca', pred_gca[jj])]:
                for k, v in per_pop_metrics(pr, y, pop).items():
                    rec[f'{m}_{k}'] = v
            perpop.append(rec)
        print(cl, test_year, 'done', round((time.time() - t0) / 60, 1), 'min', flush=True)
pp = pd.DataFrame(perpop); pp.to_csv(os.path.join(C.OUT, 'step5_perpop.csv'), index=False)
rng = np.random.default_rng(0); rows = []
def summ(g, m, name):
    v = g[f'{m}_rMP'].dropna().values; vg = g[f'{m}_rMG'].dropna().values; tp = g[f'{m}_top10'].dropna().values
    if len(v) < 3:
        return dict(stratum=name, model=m, n_pops=len(v))
    bm = [np.median(rng.choice(v, len(v))) for _ in range(1000)]
    return dict(stratum=name, model=m, n_pops=len(v), rMP_median=np.median(v), rMP_lo=np.percentile(bm, 2.5), rMP_hi=np.percentile(bm, 97.5), rMP_mean=v.mean(),
                rMG_median=np.median(vg) if len(vg) else np.nan, top10_mean=tp.mean(), frac_pos=(v > 0).mean())
for (cl, yr), g in pp.groupby(['CL', 'test_year']):
    for m in ['global', 'weighted', 'gca']:
        rows.append(dict(CL=cl, test_year=yr, **summ(g, m, 'all')))
        for s in [0, 1, 2]:
            rows.append(dict(CL=cl, test_year=yr, **summ(g[g.parents_seen == s], m, f'parents_seen={s}')))
        for s in [True, False]:
            rows.append(dict(CL=cl, test_year=yr, **summ(g[g.near_repeat == s], m, f'near_repeat={s}')))
        gs = g[g.tester_seen == True]
        if len(gs) >= 5:
            rows.append(dict(CL=cl, test_year=yr, **summ(gs, m, 'tester_seen=True')))
for cl in C.CLUSTERS:
    for m in ['global', 'weighted', 'gca']:
        rows.append(dict(CL=cl, test_year='pooled', **summ(pp[pp.CL == cl], m, 'all')))
tab = pd.DataFrame(rows); tab.to_csv(os.path.join(C.OUT, 'step5_metrics.csv'), index=False)
md.append('## Results\n'); md.append(tab.round(3).to_markdown(index=False) + '\n')
md.append(f'GCA-model coverage: {pp.gca_n.gt(0).mean():.2f} of test populations had at least one parent group with training populations (n={len(pp)}).\n')
open(os.path.join(C.OUT, 'step5_withinpop.md'), 'w').write('\n'.join(md))

def selfcheck():
    assert set(pp.CL) == {'C1', 'C2'} and pp.test_year.nunique() == 3
    assert pp.global_rMP.notna().mean() > 0.9
    assert os.path.exists(os.path.join(C.CACHE, 'step5_linepred_C1_2007.pkl'))
selfcheck()

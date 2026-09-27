# phase2/model_lib.py
"""Shared model functions for the final (Task 2) and judge-mode (Task 3) pipelines: the population
GBLUP fit, the within-population ridge/rrBLUP helpers, per-population metrics, and the confidence
rule. Both phase2/final_model.py and phase2/judge_mode.py import these instead of each keeping its
own copy, so a change to the model only has one place to make it.

Originally lifted (not imported) from step4_popmean.py/step5_withinpop.py -- those two are
run-on-import scripts with heavy top-level side effects (they reload data and rewrite step4/step5
outputs), so importing them was never viable; the small pure functions were copied out instead.
This module is that copy, now given its own home so final_model.py and judge_mode.py both import
it rather than each carrying a second copy.
"""
import numpy as np, pandas as pd


def fit_gblup(train_pops, test_pops, G, lam_mult, iters=5, weights=None):
    """weights: optional per-training-population array (same order as train_pops); replaces the
    lam*I ridge penalty with lam*diag(1/weights) (higher weight = less shrinkage for that pop).
    Default None reproduces the original unweighted behaviour exactly (used by every existing caller)."""
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
    u = np.zeros(len(y)); tcoef = np.zeros(len(tes))
    pen = lam * np.eye(len(y)) if weights is None else lam * np.diag(1.0 / np.asarray(weights, float))
    Ainv = np.linalg.inv(Ktt + pen)
    for _ in range(iters):
        r = y - mu - u; tcoef = np.linalg.solve(Zt.T @ Zt + 5.0 * np.eye(len(tes)), Zt.T @ r)
        r = y - mu - Zt @ tcoef; alpha = Ainv @ r; u = Ktt @ alpha
    ute = Kte @ alpha
    tte = np.array([tcoef[ti[x]] if x in ti else 0.0 for x in test_pops.TESTER])
    return mu + ute + tte


def strata(train_pops, test_pops, gp):
    tr = train_pops.copy(); tr['G1'] = tr.P1.map(gp); tr['G2'] = tr.P2.map(gp); seen = set(tr.G1) | set(tr.G2)
    pairs = set(tuple(sorted(x)) for x in zip(tr.G1, tr.G2))
    te = test_pops.copy(); te['G1'] = te.P1.map(gp); te['G2'] = te.P2.map(gp)
    ps = te.G1.isin(seen).astype(int) + te.G2.isin(seen).astype(int)
    nr = [tuple(sorted(x)) in pairs for x in zip(te.G1, te.G2)]
    ts = te.TESTER.isin(set(tr.TESTER))
    return ps.values, np.array(nr), ts.values


def solve_ridge(S, b, lam):
    return np.linalg.solve(S + lam * np.eye(len(S)), b)


def med_within(pred, d):
    return d.assign(pred=pred).groupby('POP').apply(lambda g: np.corrcoef(g.pred, g.y)[0, 1] if len(g) > 30 else np.nan).median()


def per_pop_metrics(pred, y, pop, h2):
    ok = ~np.isnan(pred) & ~np.isnan(y)
    if ok.sum() < 30:
        return dict(rMP=np.nan, rMG=np.nan, top10=np.nan, n=int(ok.sum()))
    r = np.corrcoef(pred[ok], y[ok])[0, 1]; H = h2.H.get(pop, np.nan); k = max(int(0.1 * ok.sum()), 1)
    top = len(set(np.argsort(-pred[ok])[:k]) & set(np.argsort(-y[ok])[:k])) / k
    return dict(rMP=r, rMG=r / np.sqrt(H) if H > 0.05 else np.nan, top10=top, n=int(ok.sum()))


def top10_enrichment(pred, true, n):
    k = max(int(round(0.1 * n)), 1)
    return (len(set(np.argsort(-pred)[:k]) & set(np.argsort(-true)[:k])) / k) / 0.10


def pick_lam(train, test, G, grid):
    return max(grid, key=lambda m: np.corrcoef(fit_gblup(train, test, G, m), test.dev)[0, 1])


def confidence(row):
    if row.parents_seen == 0 or row.n_locs_2008 < 4:
        return 'low'
    if row.parents_seen == 2 and row.n_locs_2008 >= 5 and not row.gen_flag:
        return 'high'
    return 'medium'

"""Rescore the frozen per-season predictions (from score_2008.py) against three family targets and run a
split-half value replay. Targets: raw mean, naive ENV-subtracted mean, joint ENV+family least squares.
Replay: plots of each line are split into halves A/B; line effects are estimated by a joint ENV+line fit on
each half; the model selects on its frozen score, the oracle selects on half A, and both are graded on half B.
Run from exploration/: python3 phase2/score_targets.py <score2008 outdir>
"""
import os, sys, numpy as np, pandas as pd, scipy.sparse as sp
from scipy.sparse.linalg import lsqr
from scipy.stats import pearsonr, spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

OUTDIR = sys.argv[1]
ph = pd.read_pickle(os.path.join(C.CACHE, 'unmasked', 'pheno_v2.pkl'))
L = pd.read_csv(os.path.join(OUTDIR, 'lines_by_season.csv')); Pp = pd.read_csv(os.path.join(OUTDIR, 'pops_by_season.csv'))
TR = 'YLD_BE'


def joint_fit(d, unit):
    """Least-squares y ~ ENV + unit (min-norm via lsqr); returns unit effects centered to mean 0."""
    e = pd.Categorical(d.ENV); u = pd.Categorical(d[unit])
    n = len(d); X = sp.hstack([sp.csr_matrix((np.ones(n), (np.arange(n), e.codes)), shape=(n, len(e.categories))),
                              sp.csr_matrix((np.ones(n), (np.arange(n), u.codes)), shape=(n, len(u.categories)))]).tocsr()
    beta = lsqr(X, d[TR].values - d[TR].mean(), atol=1e-10, btol=1e-10, iter_lim=20000)[0]
    eff = pd.Series(beta[len(e.categories):], index=u.categories); return eff - eff.mean()


def top_caught(pred, true):
    k = max(int(round(0.1 * len(pred))), 1)
    return len(set(np.argsort(-pred)[:k]) & set(np.argsort(-true)[:k])) / k


rows = []
for Y in [2007, 2008]:
    for cl in C.CLUSTERS:
        d = ph[(ph.YEAR == Y) & (ph.CL == cl)].dropna(subset=[TR]).copy()
        q = Pp[(Pp.season == Y) & (Pp.CL == cl)].set_index('POP')
        raw = d.groupby('POP')[TR].mean(); d['dev'] = d[TR] - d.groupby('ENV')[TR].transform('mean')
        naive = d.groupby('POP').dev.mean(); joint = joint_fit(d, 'POP')
        l = L[(L.season == Y) & (L.CL == cl)].set_index('LINE_ID')
        lraw = d.groupby('LINE_ID')[TR].mean(); ljoint = joint_fit(d, 'LINE_ID')
        l['raw'] = lraw.reindex(l.index); l['joint'] = ljoint.reindex(l.index); l = l.dropna(subset=['raw', 'joint'])
        rows.append(dict(season=Y, CL=cl, n_fam=len(q), n_lines=len(l),
                         fam_r_raw=pearsonr(q.pred, raw.reindex(q.index))[0], fam_r_naive=pearsonr(q.pred, naive.reindex(q.index))[0],
                         fam_r_joint=pearsonr(q.pred, joint.reindex(q.index))[0],
                         line_spearman_joint=spearmanr(l.score, l.joint)[0], top10_overall_joint=top_caught(l.score.values, l.joint.values),
                         top10_overall_raw=top_caught(l.score.values, l.raw.values),
                         within_rank_joint=np.mean([spearmanr(g.score, g.joint)[0] for _, g in l.groupby('POP') if len(g) >= 20])))
T = pd.DataFrame(rows); T.to_csv(os.path.join(OUTDIR, 'targets_table.csv'), index=False); print(T.round(3).to_string(index=False))


def select(d, budget, cap, key):
    d = d.sort_values(key, ascending=False); size = d.POP.value_counts(); B = d.n.sum() * budget; taken = {}; plots = 0; keep = []
    for r in d.itertuples():
        c = max(1, int(size[r.POP] * cap))
        if taken.get(r.POP, 0) >= c or plots + r.n > B:
            continue
        taken[r.POP] = taken.get(r.POP, 0) + 1; plots += r.n; keep.append(r.Index)
    return d.loc[keep]


rep = []
for Y in [2007, 2008]:
    d = ph[ph.YEAR == Y].dropna(subset=[TR]).copy()
    d = d[d.groupby('LINE_ID').LINE_ID.transform('size') >= 2]
    l = L[L.season == Y].set_index('LINE_ID')
    for seed in range(3):
        d = d.sample(frac=1, random_state=seed); d['h'] = d.groupby('LINE_ID').cumcount() % 2
        effA = pd.concat([joint_fit(d[(d.h == 0) & (d.CL == cl)], 'LINE_ID') for cl in C.CLUSTERS])
        effB = pd.concat([joint_fit(d[(d.h == 1) & (d.CL == cl)], 'LINE_ID') for cl in C.CLUSTERS])
        x = l.copy(); x['A'] = effA.reindex(x.index); x['B'] = effB.reindex(x.index); x = x.dropna(subset=['A', 'B'])
        base = x.B.mean()
        for b in [0.15, 0.25, 0.5]:
            m = select(x, b, 0.4, 'score'); o = select(x, b, 0.4, 'A')
            rep.append(dict(season=Y, seed=seed, budget=b, n_kept=len(m), model_gain=m.B.mean() - base, oracle_gain=o.B.mean() - base,
                            model_top10_share=(m.B >= x.B.quantile(.9)).mean(), oracle_top10_share=(o.B >= x.B.quantile(.9)).mean()))
R = pd.DataFrame(rep).groupby(['season', 'budget']).mean().drop(columns='seed').reset_index()
R.to_csv(os.path.join(OUTDIR, 'replay_table.csv'), index=False); print(R.round(3).to_string(index=False))

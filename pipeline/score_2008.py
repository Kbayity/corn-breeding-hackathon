"""Rolling per-season scoring 2003..2008 of the final two-layer model, INCLUDING the sealed 2008 season.

This is the only script in the repo that reads 2008 trait values (user-authorized, 2026-09-26).
Every season Y is predicted from seasons <= Y-1 only; grids are chosen on the (<=Y-2 -> Y-1) fold.
Metrics follow the teammate's table (family r, top-10% families caught, within-family rank corr,
top-10% within family caught, top-10% overall caught) plus our per-cluster metrics and a split-half
noise reference. Run from the exploration/ dir: python3 phase2/score_2008.py <outdir>
"""
import os, sys, time, numpy as np, pandas as pd
from scipy.stats import pearsonr, spearmanr
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import common as C
from model_lib import fit_gblup, solve_ridge, med_within, pick_lam

t0 = time.time()
def log(*a): print(*a, f'[{(time.time() - t0) / 60:.1f} min]', flush=True)

OUTDIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(C.OUT, 'score2008')
os.makedirs(OUTDIR, exist_ok=True)
SEASONS = [2003, 2004, 2005, 2006, 2007, 2008]
POP_GRID = [0.25, 0.5, 1, 2, 4, 8, 16, 32]
WGRID = [1, 3, 10]
TRAIT = 'YLD_BE'

# ---- unmasked phenotypes: same loader, quarantine off, separate cache file ----
masked_cache = C.CACHE
C.TEST_YEAR = 9999
C.CACHE = os.path.join(masked_cache, 'unmasked'); os.makedirs(C.CACHE, exist_ok=True)
ph = C.load_pheno()
C.CACHE = masked_cache
assert ph.loc[ph.YEAR == 2008, TRAIT].notna().sum() > 0, 'unmasked load failed'
log('pheno rows', len(ph), '2008 plots with yield', int(ph.loc[ph.YEAR == 2008, TRAIT].notna().sum()))

t = C.pop_table(ph)
pm = C.pop_means(ph, TRAIT)
lm_trial = C.line_means(ph, TRAIT, 'TRIAL'); lm_env = C.line_means(ph, TRAIT, 'ENV')

lines_out, pops_out = [], []
for cl in C.CLUSTERS:
    G = C.parent_grm(cl); pops = t[t.CL == cl].join(pm['dev'])
    X_all, keys = C.geno_matrix(cl, 'filled'); kidx = pd.Series(np.arange(len(keys)), index=keys); p = X_all.shape[1]
    lines = lm_trial[(lm_trial.CL == cl) & lm_trial.index.isin(kidx.index)].copy(); lines['gi'] = kidx[lines.index].values

    def gram(df):
        X = np.asarray(X_all[df.gi.values], np.float64); cm = X.mean(0); X -= cm
        return X.T @ X, X.T @ df.y.values, cm, df.y.values.mean()

    def predict(gi, beta, cm, mu):
        return mu + (np.asarray(X_all[gi], np.float64) - cm) @ beta

    for Y in SEASONS:
        trP = pops[pops.YEAR <= Y - 2].dropna(subset=['dev']); vaP = pops[pops.YEAR == Y - 1].dropna(subset=['dev'])
        lam = pick_lam(trP, vaP, G, POP_GRID)
        tr = pops[pops.YEAR <= Y - 1].dropna(subset=['dev']); te = pops[pops.YEAR == Y].dropna(subset=['dev'])
        pp = pd.Series(fit_gblup(tr, te, G, lam), index=te.index)
        pops_out.append(pd.DataFrame(dict(POP=te.index, CL=cl, season=Y, n_lines=te.n_lines.values, pred=pp.values, obs=te.dev.values)))

        trW = lines[lines.YEAR <= Y - 2]; vaW = lines[lines.YEAR == Y - 1]
        S, b, cm, mu = gram(trW)
        lamw = max(WGRID, key=lambda m: med_within(predict(vaW.gi.values, solve_ridge(S, b, m * p), cm, mu), vaW))
        trW2 = lines[lines.YEAR <= Y - 1]; teW = lines[lines.YEAR == Y]
        S, b, cm, mu = gram(trW2)
        pw = predict(teW.gi.values, solve_ridge(S, b, lamw * p), cm, mu)
        df = teW[['POP', 'n']].copy(); df['pred_within'] = pw; df['pred_pop'] = df.POP.map(pp)
        df['y_env'] = lm_env.y.reindex(df.index).values
        df = df.dropna(subset=['pred_pop', 'y_env']); df['score'] = df.pred_pop + df.pred_within
        df['CL'] = cl; df['season'] = Y
        lines_out.append(df.reset_index())
        log(cl, Y, 'lam_pop', lam, 'lam_w/p', lamw, 'pops', len(te), 'lines', len(df))

L = pd.concat(lines_out, ignore_index=True); Pp = pd.concat(pops_out, ignore_index=True)
L.to_csv(os.path.join(OUTDIR, 'lines_by_season.csv'), index=False)
Pp.to_csv(os.path.join(OUTDIR, 'pops_by_season.csv'), index=False)


def top_caught(pred, true):
    k = max(int(round(0.1 * len(pred))), 1)
    return len(set(np.argsort(-pred)[:k]) & set(np.argsort(-true)[:k])) / k


def within_stats(df, min_lines=20):
    rs, tops = [], []
    for pop, g in df.groupby('POP'):
        if len(g) < min_lines:
            continue
        rs.append(spearmanr(g.score, g.y_env)[0]); tops.append(top_caught(g.score.values, g.y_env.values))
    return np.mean(rs), np.mean(tops), len(rs)


def split_half(Y, seeds=5):
    d = ph[(ph.YEAR == Y)].dropna(subset=[TRAIT]).copy()
    d['dev'] = d[TRAIT] - d.groupby('ENV')[TRAIT].transform('mean')
    d = d[d.groupby('LINE_ID').LINE_ID.transform('size') >= 2]
    vals = []
    for s in range(seeds):
        d = d.sample(frac=1, random_state=s)
        d['h'] = d.groupby('LINE_ID').cumcount() % 2
        hm = d.pivot_table(index='LINE_ID', columns='h', values='dev', aggfunc='mean').dropna()
        vals.append(top_caught(hm[0].values, hm[1].values))
    return float(np.mean(vals))


rows = []
for Y in SEASONS:
    for scope in ['pooled', 'C1', 'C2']:
        l = L[L.season == Y] if scope == 'pooled' else L[(L.season == Y) & (L.CL == scope)]
        q = Pp[Pp.season == Y] if scope == 'pooled' else Pp[(Pp.season == Y) & (Pp.CL == scope)]
        if len(l) < 50 or len(q) < 5:
            continue
        wr, wt, nf = within_stats(l)
        rows.append(dict(season=Y, scope=scope, n_families=len(q), n_lines=len(l),
                         family_r=pearsonr(q.pred, q.obs)[0], family_spearman=spearmanr(q.pred, q.obs)[0],
                         top10_families_caught=top_caught(q.pred.values, q.obs.values),
                         within_rank_corr=wr, top10_within_caught=wt, families_scored=nf,
                         top10_overall_caught=top_caught(l.score.values, l.y_env.values),
                         overall_spearman=spearmanr(l.score, l.y_env)[0],
                         split_half_top10=split_half(Y) if scope == 'pooled' and Y >= 2007 else np.nan))
R = pd.DataFrame(rows); R.to_csv(os.path.join(OUTDIR, 'rolling_table.csv'), index=False)

md = ['# Rolling per-season scoring, 2003-2008 (2008 unsealed)\n',
      'Each season predicted from earlier seasons only; grids chosen on the fold before. Random = 10% caught, r = 0.\n',
      R.round(3).to_markdown(index=False), '']
open(os.path.join(OUTDIR, 'score2008.md'), 'w').write('\n'.join(md))
print(R.round(3).to_string(index=False)); log('done')

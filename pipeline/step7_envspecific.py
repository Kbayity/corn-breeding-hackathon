# phase2/step7_envspecific.py
"""Step 7: within-location ranking, broad vs broad + marker×location deviations, 2007 fold."""
import os, sys, numpy as np, pandas as pd
from scipy.stats import spearmanr
import common as C
WW = sys.argv[1] if len(sys.argv) > 1 else 'global'; WP = sys.argv[2] if len(sys.argv) > 2 else 'parent_gblup'
ph = C.load_pheno(); t = C.pop_table(ph)
s4 = pd.read_csv(os.path.join(C.OUT, 'step4_predictions.csv')); s4 = s4[s4.fold_test_year == 2007].set_index('POP')
d = ph.dropna(subset=['YLD_BE']).copy(); d['dev'] = d.YLD_BE - d.groupby('TRIAL').YLD_BE.transform('mean')
ly = C.line_means(ph, 'YLD_BE')
loc_years = d[d.YEAR < 2007].groupby('LOC').YEAR.nunique(); elig = set(loc_years[loc_years >= 3].index)
rows = []
for cl in C.CLUSTERS:
    lp = pd.read_pickle(os.path.join(C.CACHE, f'step5_linepred_{cl}_2007.pkl')); X_all, keys = C.geno_matrix(cl, 'filled'); kidx = pd.Series(np.arange(len(keys)), index=keys)
    lp['broad'] = lp.POP.map(s4[f'pred_{WP}']).fillna(0) + lp[f'pred_{WW}'].fillna(0)
    te = d[(d.CL == cl) & (d.YEAR == 2007) & d.LINE_ID.isin(lp.index)]
    for L in sorted(set(te.LOC) & elig):
        trL = d[(d.CL == cl) & (d.YEAR < 2007) & (d.LOC == L) & d.LINE_ID.isin(kidx.index)]
        if len(trL) < 200:
            continue
        dev = trL.dev.values - ly.y.reindex(trL.LINE_ID).values
        X = np.asarray(X_all[kidx[trL.LINE_ID].values], np.float64); cm = X.mean(0); X -= cm; p = X.shape[1]
        beta = np.linalg.solve(X.T @ X + 5 * p * np.eye(p), X.T @ (dev - dev.mean()))
        teL = te[te.LOC == L]; Xt = np.asarray(X_all[kidx[teL.LINE_ID].values], np.float64) - cm
        broad = lp.broad.reindex(teL.LINE_ID).values; spec = broad + Xt @ beta; obs = teL.dev.values
        sa = spearmanr(broad, obs)[0]; sb = spearmanr(spec, obs)[0]
        wp = []
        for pop, g in teL.assign(broad=broad, spec=spec).groupby('POP'):
            if len(g) >= 30:
                wp.append((spearmanr(g.broad, g.dev)[0], spearmanr(g.spec, g.dev)[0]))
        wp = np.array(wp) if wp else np.full((0, 2), np.nan)
        rows.append(dict(CL=cl, LOC=L, prior_years=int(loc_years[L]), n_train_plots=len(trL), n_test_lines=len(teL), n_test_pops=teL.POP.nunique(),
                         sp_broad=sa, sp_spec=sb, gain=sb - sa, within_pop_broad=np.nanmean(wp[:, 0]) if len(wp) else np.nan, within_pop_spec=np.nanmean(wp[:, 1]) if len(wp) else np.nan))
r = pd.DataFrame(rows); r.to_csv(os.path.join(C.OUT, 'step7_perloc.csv'), index=False)
d08 = ph[ph.YEAR == 2008]; ly08 = d[d.YEAR < 2008].groupby('LOC').YEAR.nunique(); elig08 = set(ly08[ly08 >= 3].index)
share = d08.LOC.isin(elig08).mean()
rng = np.random.default_rng(0); g = r.gain.dropna().values
ci = np.percentile([np.mean(rng.choice(g, len(g))) for _ in range(1000)], [2.5, 97.5]) if len(g) > 2 else [np.nan, np.nan]
md = [f'# Step 7: broad vs environment-specific (2007 fold; within = {WW}, population = {WP})\n',
      f'Locations with ≥ 3 prior years and ≥ 200 training plots: {len(r)} (C1 {len(r[r.CL == "C1"])}, C2 {len(r[r.CL == "C2"])}). '
      f'Mean within-location Spearman (pooled across populations): broad {r.sp_broad.mean():.3f}, broad + marker×location {r.sp_spec.mean():.3f}; '
      f'mean gain {r.gain.mean():.3f} (95% CI {ci[0]:.3f} to {ci[1]:.3f}); locations with gain > 0: {(r.gain > 0).mean():.2f}. '
      f'Within population × location: broad {r.within_pop_broad.mean():.3f}, specific {r.within_pop_spec.mean():.3f}.\n',
      f'Share of 2008 plots at locations with ≥ 3 prior years (< 2008): {share:.3f} ({d08.LOC.isin(elig08).sum()} of {len(d08)} plots; {len(set(d08.LOC) & elig08)} of {d08.LOC.nunique()} locations).\n',
      r.round(3).to_markdown(index=False)]
open(os.path.join(C.OUT, 'step7_envspecific.md'), 'w').write('\n'.join(md))

def selfcheck():
    assert len(r) >= 10 and 0 < share < 1
selfcheck()

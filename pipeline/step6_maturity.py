# phase2/step6_maturity.py
"""Step 6: within-family yield–moisture correlation, moisture-adjusted yield ranking, and MST/TWT forward-year prediction."""
import os, sys, numpy as np, pandas as pd
import common as C
WINNER_WITHIN = sys.argv[1] if len(sys.argv) > 1 else 'global'
ph = C.load_pheno(); t = C.pop_table(ph)
md = [f'# Step 6: maturity (winning within-pop model for yield = {WINNER_WITHIN})\n']
ly = C.line_means(ph, 'YLD_BE'); lmst = C.line_means(ph, 'MST'); j = ly.join(lmst.y.rename('mst'), how='inner')
corr = j.groupby('POP').apply(lambda g: np.corrcoef(g.y, g.mst)[0, 1] if len(g) > 30 else np.nan).dropna()
md.append(f'Within-family correlation of yield with moisture (TRIAL-adjusted line means, n={len(corr)} populations): median {corr.median():.3f}, mean {corr.mean():.3f}, '
          f'IQR {corr.quantile(.25):.3f}–{corr.quantile(.75):.3f}; fraction > 0.1: {(corr > 0.1).mean():.2f}.\n')
d = ph.dropna(subset=['YLD_BE', 'MST']).copy()
def resid(g):
    x = g.MST.values; y = g.YLD_BE.values; b = np.cov(x, y)[0, 1] / max(np.var(x), 1e-9); return pd.Series(y - b * (x - x.mean()), index=g.index)
d['YLD_ADJ'] = d.groupby('ENV', group_keys=False).apply(resid)
ladj = C.line_means(d, 'YLD_ADJ'); jj = ly.join(ladj.y.rename('yadj'), how='inner')
over = []
for pop, g in jj.groupby('POP'):
    if len(g) < 30:
        continue
    k = max(int(0.1 * len(g)), 1); a = set(g.y.nlargest(k).index); b = set(g.yadj.nlargest(k).index); over.append(len(a & b) / k)
md.append(f'Top-10% overlap between raw yield and moisture-adjusted yield within family: mean {np.mean(over):.3f} (n={len(over)} populations); i.e. {100 * (1 - np.mean(over)):.0f}% of the top set changes.\n')
rows = []
for trait in ['MST', 'TWT']:
    lt = C.line_means(ph, trait); h2t = C.pop_h2(ph, trait)
    for cl in C.CLUSTERS:
        X_all, keys = C.geno_matrix(cl, 'filled'); kidx = pd.Series(np.arange(len(keys)), index=keys)
        lines = lt[(lt.CL == cl) & lt.index.isin(kidx.index)].copy(); lines['gi'] = kidx[lines.index].values
        for last, ty in C.FOLDS:
            tr = lines[lines.YEAR <= last]; te = lines[lines.YEAR == ty]
            Xtr = np.asarray(X_all[tr.gi.values], np.float64); cm = Xtr.mean(0); Xtr -= cm; Xte = np.asarray(X_all[te.gi.values], np.float64) - cm; p = Xtr.shape[1]
            beta = np.linalg.solve(Xtr.T @ Xtr + 5 * p * np.eye(p), Xtr.T @ (tr.y.values - tr.y.mean())); pred = tr.y.mean() + Xte @ beta
            r = te.assign(pred=pred).groupby('POP').apply(lambda g: np.corrcoef(g.pred, g.y)[0, 1] if len(g) > 30 else np.nan).dropna()
            rg = (r / np.sqrt(h2t.H.reindex(r.index).clip(lower=0.05))).median()
            rows.append(dict(trait=trait, CL=cl, test_year=ty, n_pops=len(r), rMP_median=r.median(), rMP_mean=r.mean(), rMG_median=rg))
sec = pd.DataFrame(rows); sec.to_csv(os.path.join(C.OUT, 'step6_secondary_metrics.csv'), index=False)
md.append('## MST and TWT within-population forward-year accuracy (global rrBLUP, λ = 5p)\n'); md.append(sec.round(3).to_markdown(index=False) + '\n')
md.append('Note: secondary traits were predicted with the global rrBLUP regardless of the yield winner, to keep runtime under 15 minutes.\n')
open(os.path.join(C.OUT, 'step6_maturity.md'), 'w').write('\n'.join(md))

def selfcheck():
    assert len(corr) > 700 and len(sec) == 12
selfcheck()

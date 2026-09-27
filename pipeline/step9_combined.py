"""Step 9: combined population-mean + within-population score across lines (forward-year)."""
import os, numpy as np, pandas as pd
from scipy.stats import spearmanr
import common as C

ph = C.load_pheno()
lm_env = C.line_means(ph, 'YLD_BE', 'ENV')
s4 = pd.read_csv(os.path.join(C.OUT, 'step4_predictions.csv'))


def top10_enrichment(pred, true, n):
    k = max(int(round(0.1 * n)), 1)
    top_pred = set(np.argsort(-pred)[:k])
    top_true = set(np.argsort(-true)[:k])
    return (len(top_pred & top_true) / k) / 0.10


rows = []
for cl in C.CLUSTERS:
    s4c = s4[s4.CL == cl]
    for last, test_year in C.FOLDS:
        d = pd.read_pickle(os.path.join(C.CACHE, f'step5_linepred_{cl}_{test_year}.pkl'))
        y_env = lm_env.reindex(d.index)['y']
        pp = s4c[s4c.fold_test_year == test_year].set_index('POP')['pred_parent_gblup']
        pop_pred = d['POP'].map(pp)
        keep = pop_pred.notna() & y_env.notna() & d['pred_global'].notna()
        n_dropped = int((~keep).sum())
        yv = y_env[keep].values; pv = pop_pred[keep].values; gv = d.loc[keep, 'pred_global'].values
        pop_of = d.loc[keep, 'POP'].values
        combined = pv + gv
        oracle_pop_mean = pd.Series(yv).groupby(pop_of).transform('mean').values
        oracle = oracle_pop_mean + gv
        n = len(yv)
        rows.append(dict(
            CL=cl, test_year=test_year, n_lines=n, n_dropped=n_dropped,
            spearman_combined=spearmanr(combined, yv)[0],
            spearman_pop=spearmanr(pv, yv)[0],
            spearman_global=spearmanr(gv, yv)[0],
            top10_enrichment=top10_enrichment(combined, yv, n),
            spearman_oracle=spearmanr(oracle, yv)[0],
        ))

tab = pd.DataFrame(rows)
METRIC_COLS = ['spearman_combined', 'spearman_pop', 'spearman_global', 'top10_enrichment', 'spearman_oracle']


def summarize(sub, label):
    r = dict(CL='ALL', test_year=label, n_lines=int(sub.n_lines.sum()), n_dropped=int(sub.n_dropped.sum()))
    for c in METRIC_COLS:
        r[c] = sub[c].mean()
    return r


tab_full = pd.concat([tab, pd.DataFrame([summarize(tab, 'mean_all_folds'), summarize(tab[tab.test_year == 2007], '2007_folds')])], ignore_index=True)
tab_full['test_year'] = tab_full['test_year'].astype(object)
tab_full.to_csv(os.path.join(C.OUT, 'step9_combined.csv'), index=False)

md = ['# Step 9: combined score across lines (forward-year)\n',
      "Per fold: combined = pred_parent_gblup (population layer, Step 4) + pred_global (within-population rrBLUP, Step 5) for each test-year line; "
      "target y_env = ENV-adjusted line mean (common.line_means, block='ENV'). Lines whose population has no Step-4 parent_gblup prediction for that "
      "fold are dropped and counted in n_dropped. Oracle = true (test-set) population mean of y_env in place of the population-layer prediction, plus pred_global.\n",
      tab_full.round(3).to_markdown(index=False) + '\n',
      "The two 2007 folds (C1 and C2) are the closest analogue to scoring 2008, since 2007 is the last training year before the quarantined 2008 test year. "
      "The oracle row shows how much of the combined score's ceiling is set by the population layer rather than the within-population layer: replacing the "
      "model's population prediction with the true population mean would still leave the same within-population term, so the oracle-vs-combined gap is the "
      "room left for a better population-mean model.\n"]
open(os.path.join(C.OUT, 'step9_combined.md'), 'w').write('\n'.join(md))


def selfcheck():
    assert len(tab) == 6
    for c in ['spearman_combined', 'spearman_pop', 'spearman_global', 'spearman_oracle']:
        assert np.isfinite(tab[c]).all(), c


selfcheck()

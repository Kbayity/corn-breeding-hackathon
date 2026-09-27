"""Task 2: final model -- 2007 validation and 2008 predictions.

Population layer: fit_gblup (parent GRM kernel + tester ridge, final W1/W2). lam_mult grid.
Within layer: global rrBLUP on TRIAL-adjusted line means (Task-4 filled genotype matrix). lambda grid
(units of p, the marker count). Traits: YLD_BE, MST, TWT for both layers.

Two grid selections per (cluster, trait, layer):
  - chosen on the 2005->2006 internal fold, applied to the train<=2006 -> predict 2007 fit
    (these are the "2007 validation" numbers).
  - re-chosen on the 2006->2007 fold (train<=2006 -> predict 2007, same split, picking the grid
    value that is *best on this fold's true result*), applied to the train<=2007 -> predict 2008 fit
    (these are the final 2008 predictions).

fit_gblup/strata/solve_ridge/med_within/per_pop_metrics/top10_enrichment/pick_lam/confidence live in
model_lib.py (shared with judge_mode.py), not here: they were originally copied (not imported) from
step4_popmean.py/step5_withinpop.py, since both those files are run-on-import scripts with heavy
top-level side effects (they reload data and rewrite step4/step5 outputs); model_lib.py is that copy
given a proper shared home instead of being duplicated a second time into judge_mode.py.
"""
import os, time, numpy as np, pandas as pd
from scipy.stats import pearsonr, spearmanr
import common as C
from step1e_parents import parent_groups
from model_lib import fit_gblup, strata, solve_ridge, med_within, per_pop_metrics, top10_enrichment, pick_lam, confidence

t0 = time.time()


def log(*a):
    print(*a, f'[{(time.time() - t0) / 60:.1f} min]', flush=True)


TRAITS = ['YLD_BE', 'MST', 'TWT']
POP_LAM_GRID = [0.25, 0.5, 1, 2, 4, 8, 16, 32]
WITHIN_MULT_GRID = [0.1, 0.3, 1, 3, 10, 25]
# ponytail: FINAL_MODEL_FAST shrinks both grids to 1 value for a quick local smoke test of the
# pipeline's plumbing (shapes/merges/selfcheck) before the real run on the box; never set in the
# real run since it also changes the *reported* chosen lambda.
if os.environ.get('FINAL_MODEL_FAST'):
    POP_LAM_GRID = [1, 4]
    WITHIN_MULT_GRID = [1, 10]

def within_summary(df, pred, h2):
    """Per-pop rMP/rMG/top10 -> median/median/mean across pops in df (df has .y, .POP)."""
    recs = [per_pop_metrics(g.assign(pred=pred[df.index.get_indexer(g.index)]).pred.values, g.y.values, pop, h2)
            for pop, g in df.groupby('POP')]
    r = pd.DataFrame(recs)
    return dict(rMP_median=r.rMP.median(), rMG_median=r.rMG.median(), top10_mean=r.top10.mean(), n_pops=len(r))


# ==================== data ====================
ph = C.load_pheno()
t = C.pop_table(ph)
gpop = pd.read_csv(os.path.join(C.OUT, 'pop_generation_final.csv'), index_col='POP')
t['gen_flag'] = (t['GEN'].astype(str) != t['GEN_declared'].astype(str)) | (t.index.map(gpop['flag']) == 'reversed')
pm_by_trait = {tr: C.pop_means(ph, tr) for tr in TRAITS}
h2_by_trait = {tr: C.pop_h2(ph, tr) for tr in TRAITS}

pop_result = {}      # (cl, trait) -> dict
within_result = {}   # (cl, trait) -> dict
design_by_cl = {}    # cl -> per-line 2008 design frame (POP, P1, P2, TESTER, n_locs_2008, n_plots_2008)
conf_by_cl = {}      # cl -> per-pop 2008 confidence frame (parents_seen, near_repeat, tester_seen, n_hist_lines_parents)

d8 = ph[ph.YEAR == 2008]

for cl in C.CLUSTERS:
    log('=== cluster', cl, '===')
    G = C.parent_grm(cl)
    pops_cl = t[t.CL == cl]
    gp = parent_groups(cl)

    # ---- population layer, all 3 traits ----
    for trait in TRAITS:
        pops = pops_cl.join(pm_by_trait[trait]['dev'])
        trA = pops[pops.YEAR <= 2005].dropna(subset=['dev']); teA = pops[pops.YEAR == 2006].dropna(subset=['dev'])
        lam_val = pick_lam(trA, teA, G, POP_LAM_GRID)
        trB = pops[pops.YEAR <= 2006].dropna(subset=['dev']); teB = pops[pops.YEAR == 2007].dropna(subset=['dev'])
        pred_2007 = fit_gblup(trB, teB, G, lam_val)
        lam_final = pick_lam(trB, teB, G, POP_LAM_GRID)
        trC = pops[pops.YEAR <= 2007].dropna(subset=['dev']); teC = pops[pops.YEAR == 2008]
        pred_2008 = fit_gblup(trC, teC, G, lam_final)
        pop_result[(cl, trait)] = dict(lam_val=lam_val, lam_final=lam_final,
                                        trB=trB, teB=teB, pred_2007=pred_2007,
                                        idx_2008=teC.index, pred_2008=pred_2008)
        log('pop layer', cl, trait, 'lam_val', lam_val, 'lam_final', lam_final)

    # ---- confidence / strata (population level, pedigree-based; YLD_BE historical footprint) ----
    hist_all = pops_cl[pops_cl.YEAR <= 2007].copy()
    hist_all['G1'] = hist_all.P1.map(gp); hist_all['G2'] = hist_all.P2.map(gp)
    test_pops2008 = pops_cl[pops_cl.YEAR == 2008].copy()
    ps, nr, ts = strata(hist_all, test_pops2008, gp)
    test_pops2008 = test_pops2008.assign(G1=test_pops2008.P1.map(gp), G2=test_pops2008.P2.map(gp),
                                          parents_seen=ps, near_repeat=nr, tester_seen=ts)
    n_hist = []
    for _, row in test_pops2008.iterrows():
        grp = {row.G1, row.G2}
        n_hist.append(int(hist_all.loc[hist_all.G1.isin(grp) | hist_all.G2.isin(grp), 'n_lines'].sum()))
    test_pops2008['n_hist_lines_parents'] = n_hist
    conf_by_cl[cl] = test_pops2008

    # ---- within layer, all 3 traits (genotype matrix shared, loaded once per cluster) ----
    X_all, keys = C.geno_matrix(cl, 'filled')
    kidx = pd.Series(np.arange(len(keys)), index=keys)
    p = X_all.shape[1]
    grid_abs = [m * p for m in WITHIN_MULT_GRID]
    design_lines = sorted(d8[d8.CL == cl].LINE_ID.unique())
    teC_gi = kidx.loc[design_lines].values

    def build(train_df):
        X = np.asarray(X_all[train_df.gi.values], np.float64)
        cmean = X.mean(0); X = X - cmean
        return X.T @ X, X.T @ train_df.y.values, cmean, train_df.y.values.mean()

    def predict(gi, beta, cmean, ymean):
        Xte = np.asarray(X_all[gi], np.float64) - cmean
        return ymean + Xte @ beta

    for trait in TRAITS:
        lm = C.line_means(ph, trait, 'TRIAL')
        lines = lm[(lm.CL == cl) & lm.index.isin(kidx.index)].copy()
        lines['gi'] = kidx[lines.index].values

        trA = lines[lines.YEAR <= 2005]; teA = lines[lines.YEAR == 2006]
        SA, bA, cmA, muA = build(trA)
        lam_val = max(grid_abs, key=lambda l: med_within(predict(teA.gi.values, solve_ridge(SA, bA, l), cmA, muA), teA))
        log('within grid-A (2005->2006)', cl, trait, 'lam_val/p', round(lam_val / p, 2))

        trB = lines[lines.YEAR <= 2006]; teB = lines[lines.YEAR == 2007]
        SB, bB, cmB, muB = build(trB)
        preds_by_lam = {l: predict(teB.gi.values, solve_ridge(SB, bB, l), cmB, muB) for l in grid_abs}
        pred_2007 = preds_by_lam[lam_val]
        lam_final = max(grid_abs, key=lambda l: med_within(preds_by_lam[l], teB))
        log('within grid-B (2006->2007, re-chosen)', cl, trait, 'lam_final/p', round(lam_final / p, 2))

        trC = lines[lines.YEAR <= 2007]
        SC, bC, cmC, muC = build(trC)
        beta_final = solve_ridge(SC, bC, lam_final)
        pred_2008 = predict(teC_gi, beta_final, cmC, muC)

        within_result[(cl, trait)] = dict(lam_val=lam_val, lam_final=lam_final, p=p,
                                           teB=teB, pred_2007=pred_2007,
                                           idx_2008=design_lines, pred_2008=pred_2008)
        log('within layer done', cl, trait)

    # ---- per-line 2008 design attributes (POP/P1/P2/TESTER/n_locs/n_plots) ----
    d8cl = d8[d8.CL == cl]
    design = d8cl.groupby('LINE_ID').agg(POP=('POP', 'first'), P1=('P1', 'first'), P2=('P2', 'first'),
                                          TESTER=('TESTER', 'first'), n_locs_2008=('LOC', 'nunique'),
                                          n_plots_2008=('LOC', 'size'))
    design_by_cl[cl] = design

log('all fits done')

# ==================== moisture slope b (pooled within-ENV, 2005-2007 plots, both clusters) ====================
plots = ph[(ph.YEAR >= 2005) & (ph.YEAR <= 2007)].dropna(subset=['YLD_BE', 'MST']).copy()
plots['dev_y'] = plots['YLD_BE'] - plots.groupby('ENV')['YLD_BE'].transform('mean')
plots['dev_m'] = plots['MST'] - plots.groupby('ENV')['MST'].transform('mean')
b_slope = float((plots.dev_y * plots.dev_m).sum() / (plots.dev_m ** 2).sum())
log('moisture slope b', b_slope)

# ==================== assemble 2008 predictions ====================
frames = []
for cl in C.CLUSTERS:
    design = design_by_cl[cl].copy()
    design['CL'] = cl
    design['GEN_OBS'] = design['POP'].map(t['GEN'])
    for trait, col in [('YLD_BE', 'pred_pop'), ('MST', 'pred_pop_MST'), ('TWT', 'pred_pop_TWT')]:
        pr = pop_result[(cl, trait)]
        s = pd.Series(pr['pred_2008'], index=pr['idx_2008'])
        design[col] = design['POP'].map(s)
    for trait, col in [('YLD_BE', 'pred_within'), ('MST', 'pred_within_MST'), ('TWT', 'pred_within_TWT')]:
        wr = within_result[(cl, trait)]
        s = pd.Series(wr['pred_2008'], index=wr['idx_2008'])
        design[col] = s.reindex(design.index).values
    design['score'] = design['pred_pop'] + design['pred_within']
    design['pred_MST'] = design['pred_pop_MST'] + design['pred_within_MST']
    design['pred_TWT'] = design['pred_pop_TWT'] + design['pred_within_TWT']
    design['score_adj'] = design['score'] - b_slope * design['pred_MST']

    cp = conf_by_cl[cl]  # indexed by POP (subset of pop_table, already POP-indexed)
    design['parents_seen'] = design['POP'].map(cp['parents_seen'])
    design['n_hist_lines_parents'] = design['POP'].map(cp['n_hist_lines_parents'])
    design['near_repeat'] = design['POP'].map(cp['near_repeat'])
    design['tester_seen'] = design['POP'].map(cp['tester_seen'])
    design['gen_flag'] = design['POP'].map(t['gen_flag'])

    # pop_reliability: validated 2007 Pearson (YLD_BE, pop layer) for the line's own parents_seen stratum
    prB = pop_result[(cl, 'YLD_BE')]
    psB, _, _ = strata(prB['trB'], prB['teB'], gp := parent_groups(cl))
    rel_by_stratum = {}
    for s in [0, 1, 2]:
        mask = psB == s
        rel_by_stratum[s] = pearsonr(prB['pred_2007'][mask], prB['teB'].dev.values[mask])[0] if mask.sum() >= 3 else np.nan
    design['pop_reliability'] = design['parents_seen'].map(rel_by_stratum)

    design = design.reset_index().rename(columns={'index': 'LINE_ID'})
    frames.append(design)

full = pd.concat(frames, ignore_index=True)
full['confidence'] = full.apply(confidence, axis=1)
full['rank_cluster'] = full.groupby('CL')['score'].rank(method='first', ascending=False).astype(int)
full['rank_overall'] = full['score'].rank(method='first', ascending=False).astype(int)
full['pct_in_pop'] = full.groupby('POP')['score'].rank(pct=True) * 100
full['rank_adj'] = full.groupby('CL')['score_adj'].rank(method='first', ascending=False).astype(int)

PRED_COLS = ['LINE_ID', 'CL', 'POP', 'P1', 'P2', 'GEN_OBS', 'TESTER', 'n_locs_2008', 'pred_pop', 'pred_within',
             'score', 'rank_cluster', 'rank_overall', 'pct_in_pop', 'pred_MST', 'pred_TWT', 'score_adj', 'rank_adj',
             'parents_seen', 'n_hist_lines_parents', 'near_repeat', 'tester_seen', 'gen_flag', 'pop_reliability',
             'confidence']
full[PRED_COLS].to_csv(os.path.join(C.OUT, 'predictions_2008.csv'), index=False)
log('wrote predictions_2008.csv', len(full), 'rows')


def selfcheck():
    assert len(full) == 15968, len(full)
    assert full['score'].notna().all()
    for cl, g in full.groupby('CL'):
        assert g['rank_cluster'].is_unique, cl
    log('selfcheck OK')


selfcheck()

# ==================== 2007 validation report ====================
val_rows = []
combined_rows = []
rel_rows = []
for cl in C.CLUSTERS:
    for trait in TRAITS:
        pr = pop_result[(cl, trait)]
        bc = C.boot_corr(pr['pred_2007'], pr['teB'].dev.values)
        wr = within_result[(cl, trait)]
        ws = within_summary(wr['teB'], wr['pred_2007'], h2_by_trait[trait])
        val_rows.append(dict(CL=cl, trait=trait, lam_mult_val=pr['lam_val'], lam_mult_final=pr['lam_final'],
                              pop_pearson=bc['pearson'], pop_pearson_lo=bc['p_lo'], pop_pearson_hi=bc['p_hi'],
                              pop_spearman=bc['spearman'], pop_spearman_lo=bc['s_lo'], pop_spearman_hi=bc['s_hi'],
                              pop_n=bc['n'], within_lam_over_p_val=round(wr['lam_val'] / wr['p'], 2),
                              within_lam_over_p_final=round(wr['lam_final'] / wr['p'], 2),
                              within_rMP_median=ws['rMP_median'], within_rMG_median=ws['rMG_median'],
                              within_top10_mean=ws['top10_mean'], within_n_pops=ws['n_pops']))
        gp = parent_groups(cl)
        psB, _, _ = strata(pr['trB'], pr['teB'], gp)
        for s in [0, 1, 2]:
            mask = psB == s
            if mask.sum() >= 3:
                r = pearsonr(pr['pred_2007'][mask], pr['teB'].dev.values[mask])[0]
            else:
                r = np.nan
            rel_rows.append(dict(CL=cl, trait=trait, parents_seen=s, n_pops=int(mask.sum()), pearson=r))

    # combined score (YLD_BE): pop pred (mapped by POP) + within pred, vs ENV-adjusted line mean
    prY = pop_result[(cl, 'YLD_BE')]; wrY = within_result[(cl, 'YLD_BE')]
    y_env = C.line_means(ph, 'YLD_BE', 'ENV')['y']
    pop_pred_s = pd.Series(prY['pred_2007'], index=prY['teB'].index)
    line_pop = wrY['teB']['POP'].map(pop_pred_s)
    yv = y_env.reindex(wrY['teB'].index)
    keep = line_pop.notna() & yv.notna()
    combined = (line_pop[keep] + wrY['pred_2007'][keep.values]).values
    yv = yv[keep].values
    combined_rows.append(dict(CL=cl, n_lines=int(keep.sum()),
                               spearman_combined=spearmanr(combined, yv)[0],
                               top10_enrichment=top10_enrichment(combined, yv, len(yv))))

val_tab = pd.DataFrame(val_rows)
rel_tab = pd.DataFrame(rel_rows)
combined_tab = pd.DataFrame(combined_rows)
val_tab.to_csv(os.path.join(C.OUT, 'final_validation.csv'), index=False)

vmd = ['# Final model: 2007 validation\n',
       'Population layer (fit_gblup, parent GRM kernel) and within-population layer (global rrBLUP on '
       'Task-4 filled genotype matrix) trained on YEAR<=2006, predicting YEAR=2007. Grids (lam_mult for '
       'the population layer, lambda/p for the within layer) chosen on the internal 2005->2006 fold. '
       '"final" lambda columns show the value re-chosen on the 2006->2007 fold for the actual 2008 fit '
       '(reported here for comparison only; the 2008 predictions use it, not the 2007 numbers above).\n',
       val_tab.round(3).to_markdown(index=False) + '\n',
       '## Combined score (YLD_BE): pred_pop + pred_within vs ENV-adjusted line mean\n',
       combined_tab.round(3).to_markdown(index=False) + '\n',
       '## Population-layer reliability (Pearson) by parents_seen stratum (train<=2006 -> test 2007)\n',
       rel_tab.round(3).to_markdown(index=False) + '\n',
       f'## Moisture slope\nb (pooled within-ENV yield-on-moisture slope, 2005-2007 plots, both clusters) = {b_slope:.4f}\n']
open(os.path.join(C.OUT, 'final_validation.md'), 'w').write('\n'.join(vmd))
log('wrote final_validation.md/csv')

# ==================== final_model_report.md ====================
conf_dist = full.groupby(['CL', 'confidence']).size().unstack(fill_value=0)
top20 = (full.sort_values(['CL', 'score'], ascending=[True, False]).groupby('CL').head(20)
         [['CL', 'LINE_ID', 'POP', 'score', 'score_adj', 'confidence']])

# allocation table: budgets by fraction of total 2008 plots (design rows), score-ranked, 40% per-pop cap
total_plots = int(full['n_plots_2008'].sum())
alloc_rows = []
for frac in [0.25, 0.5, 0.75]:
    budget = frac * total_plots
    cap = full.groupby('POP')['LINE_ID'].transform('count').mul(0.4).apply(lambda x: max(1, int(x)))
    order = full.sort_values('score', ascending=False)
    cap_map = cap.reindex(order.index)
    kept_idx, used, taken_per_pop = [], 0, {}
    for idx, row in order.iterrows():
        if used + row.n_plots_2008 > budget:
            continue
        pop_cap = int(cap_map.loc[idx])
        if taken_per_pop.get(row.POP, 0) >= pop_cap:
            continue
        kept_idx.append(idx); used += row.n_plots_2008; taken_per_pop[row.POP] = taken_per_pop.get(row.POP, 0) + 1
    alloc_rows.append(dict(budget_pct=int(frac * 100), plots_used=used, plots_budget=round(budget),
                           n_lines_kept=len(kept_idx), n_pops_kept=len(taken_per_pop)))
alloc_tab = pd.DataFrame(alloc_rows)

y7 = combined_tab['top10_enrichment'].mean()

rmd = ['# Final model report (Task 2)\n',
       '## 2007 validation\n', 'See final_validation.md for the full table; summary reproduced below.\n',
       val_tab.round(3).to_markdown(index=False) + '\n',
       combined_tab.round(3).to_markdown(index=False) + '\n',
       '## Chosen grid values (final fit, re-chosen on 2006->2007)\n',
       pd.DataFrame([dict(CL=cl, trait=tr, pop_lam_mult_final=pop_result[(cl, tr)]['lam_final'],
                          within_lam_over_p_final=round(within_result[(cl, tr)]['lam_final'] / within_result[(cl, tr)]['p'], 2))
                    for cl in C.CLUSTERS for tr in TRAITS]).to_markdown(index=False) + '\n',
       f'## Moisture slope\nb = {b_slope:.4f} bu/ac per point of MST (pooled within-ENV, 2005-2007 plots).\n',
       '## Confidence distribution\n', conf_dist.to_markdown() + '\n',
       '## Top-20 lines per cluster by score\n', top20.round(3).to_markdown(index=False) + '\n',
       '## Plot-allocation table (lines kept by score, 40% per-population cap)\n',
       f'Total planned 2008 plots (design rows): {total_plots}.\n',
       alloc_tab.to_markdown(index=False) + '\n',
       f'Validated (2007, YLD_BE combined-score) top-10% enrichment for reference: {y7:.2f}x random '
       '(no ground truth exists for 2008, so this validated number -- not a per-budget computation -- '
       'is the expected quality context for the allocation above).\n']
open(os.path.join(C.OUT, 'final_model_report.md'), 'w').write('\n'.join(rmd))
log('wrote final_model_report.md -- done')

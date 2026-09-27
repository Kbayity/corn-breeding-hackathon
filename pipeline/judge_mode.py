"""Judge mode: end-to-end pipeline on sample_data/ (3 C1 populations -- two historical, 2006 and
2007, both sharing parent 1414691 with the third, a 2008 population). Runs generation
classification -> genotype fill -> population GBLUP -> within-population rrBLUP -> 2008
predictions, in well under 2 minutes.

Every modeling function here (fit_gblup, strata, solve_ridge, med_within, pick_lam, confidence)
is imported from phase2/model_lib.py, the module phase2/final_model.py also imports them from --
never re-implemented, never duplicated a second time. The per-population fill loop body reuses
phase2/impute.py's fill_parent/fill_population unchanged (copied from phase2/step1d_fill.py's loop,
since that script is a run-on-import script with top-level side effects, same reasoning
model_lib.py's own docstring gives for why its functions were copied out of step4_popmean.py/
step5_withinpop.py in the first place). phase2/step10_generation.py *is* imported directly: it only
defines functions at module scope (its side effects are gated behind `if __name__ == '__main__':`),
so importing it is safe and reuses it exactly as the full run does.

The only divergence from the full run is iterating over CLUSTERS_PRESENT (clusters that actually
have phenotype rows) instead of the fixed C.CLUSTERS -- a data-size guard for the C2-free sample,
not a different algorithm. With only 1-2 historical populations per cluster, the lambda grids have
nothing to discriminate on and pick an arbitrary (first) grid value -- expected and documented in
the README, not a bug.

Run (from the exploration/ directory):
    MAIZE_DATA="sample_data/Simplified Hackathon Dataset V3" MAIZE_CACHE=cache_judge \
    MAIZE_OUT=outputs_judge python3 phase2/judge_mode.py
Writes outputs_judge/judge_mode_output.csv with the same columns as outputs/predictions_2008.csv.
"""
import os, sys, shutil, time, warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)   # sample data is tiny: empty/near-empty folds produce harmless nan-mean/nan-corrcoef warnings (see pick_lam note below)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import common as C
import impute as I
import step10_generation as GEN
from step1e_parents import parent_groups
from model_lib import fit_gblup, strata, solve_ridge, med_within, pick_lam, confidence

t0 = time.time()


def log(*a):
    print(*a, f'[{time.time() - t0:.1f}s]', flush=True)


TRAITS = ['YLD_BE', 'MST', 'TWT']
POP_LAM_GRID = [0.25, 0.5, 1, 2, 4, 8, 16, 32]
WITHIN_MULT_GRID = [0.1, 0.3, 1, 3, 10, 25]
GEN_MAP = {'F2': 'F2', 'DH': 'DH', 'BC1': 'BC', 'BC1F2': 'BC1F2'}

# fit_gblup, strata, solve_ridge, med_within, pick_lam, confidence: imported from model_lib.py above
# (shared with final_model.py). Note on pick_lam with this tiny sample: with <2 populations on one
# side of a fold this is degenerate (nan for every grid value) and falls through to grid[0] -- the
# "arbitrary" grid choice the README calls out, not a crash: np.corrcoef of an all-nan array warns
# (suppressed above) but returns nan, and max() over all-equal (nan) keys keeps the first candidate.

PRED_COLS = ['LINE_ID', 'CL', 'POP', 'P1', 'P2', 'GEN_OBS', 'TESTER', 'n_locs_2008', 'pred_pop', 'pred_within',
             'score', 'rank_cluster', 'rank_overall', 'pct_in_pop', 'pred_MST', 'pred_TWT', 'score_adj', 'rank_adj',
             'parents_seen', 'n_hist_lines_parents', 'near_repeat', 'tester_seen', 'gen_flag', 'pop_reliability',
             'confidence']

# ==================== step 1: generation classification (reused as-is) ====================
gen_out, gen_t = GEN.run()
GEN.write_md(gen_out, gen_t)
log('generation classification done', len(gen_out), 'populations')

# ==================== reference artifacts judge mode reuses rather than recomputing ====================
# parent_groups_{cl}.csv is a phase-1 IBS-clustering artifact over ALL parents in the full dataset;
# recomputing it here would require the full parent genome file we deliberately don't ship in
# sample_data/. Copy the precomputed C1 file into the (isolated) judge OUT dir so parent_groups()
# -- unmodified -- finds it there instead of clobbering the real outputs/ directory.
_real_out = os.path.join(C.EXPL, 'outputs')
for fn in ['parent_groups_C1.csv']:
    src, dst = os.path.join(_real_out, fn), os.path.join(C.OUT, fn)
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy(src, dst)

# ==================== step 2: fill (copied loop body from phase2/step1d_fill.py) ====================
ph = C.load_pheno()
t = C.pop_table(ph)
gpop = pd.read_csv(os.path.join(C.OUT, 'pop_generation_final.csv'), index_col='POP')
t['gen_flag'] = (t['GEN'].astype(str) != t['GEN_declared'].astype(str)) | (t.index.map(gpop['flag']) == 'reversed')
mp_df = C.marker_map()
mp = {'chrom': mp_df.chrom.values, 'cM': mp_df.cM.values}

CLUSTERS_PRESENT = [cl for cl in C.CLUSTERS if (t.CL == cl).any()]   # data-size guard: C2 absent from sample_data
log('clusters present', CLUSTERS_PRESENT)

for cl in CLUSTERS_PRESENT:
    P = C.load_parents(cl); panel_sign = np.sign(np.nan_to_num(np.nanmean(P.values, 0))); panel_sign[panel_sign == 0] = 1
    mats, keys = [], []
    for pop in t.index[t.CL == cl]:
        r = t.loc[pop]
        par, prog = C.load_imputed_pop(cl, pop)
        A_id = r.RECURRENT if pd.notna(r.RECURRENT) else r.P1
        B_id = r.P2 if A_id == r.P1 else r.P1
        parA, fa, pa = I.fill_parent(par.loc[A_id].values.astype(float), mp, panel_sign)
        parB, fb, pb = I.fill_parent(par.loc[B_id].values.astype(float), mp, panel_sign)
        gen = GEN_MAP.get(r.GEN, 'F2')
        V = prog.values.astype(float)
        filled = I.fill_population(V, parA, parB, gen, mp)
        mats.append(filled); keys += list(prog.index)
    X = np.vstack(mats).astype(np.float32); assert not np.isnan(X).any()
    np.save(os.path.join(C.CACHE, f'filled_{cl}_X.npy'), X); pd.to_pickle(keys, os.path.join(C.CACHE, f'filled_{cl}_keys.pkl'))
    log('filled', cl, X.shape)

# ==================== steps 3-4: population GBLUP + within rrBLUP + 2008 predictions ====================
# (copied from phase2/final_model.py's per-cluster loop, scoped to CLUSTERS_PRESENT; see module docstring)
pm_by_trait = {tr: C.pop_means(ph, tr) for tr in TRAITS}
d8 = ph[ph.YEAR == 2008]
pop_result = {}; within_result = {}; design_by_cl = {}; conf_by_cl = {}

for cl in CLUSTERS_PRESENT:
    log('=== cluster', cl, '===')
    G = C.parent_grm(cl)
    pops_cl = t[t.CL == cl]
    gp = parent_groups(cl)

    for trait in TRAITS:
        pops = pops_cl.join(pm_by_trait[trait]['dev'])
        trA = pops[pops.YEAR <= 2005].dropna(subset=['dev']); teA = pops[pops.YEAR == 2006].dropna(subset=['dev'])
        lam_val = pick_lam(trA, teA, G, POP_LAM_GRID)
        trB = pops[pops.YEAR <= 2006].dropna(subset=['dev']); teB = pops[pops.YEAR == 2007].dropna(subset=['dev'])
        lam_final = pick_lam(trB, teB, G, POP_LAM_GRID)
        trC = pops[pops.YEAR <= 2007].dropna(subset=['dev']); teC = pops[pops.YEAR == 2008]
        pred_2008 = fit_gblup(trC, teC, G, lam_final)
        pop_result[(cl, trait)] = dict(idx_2008=teC.index, pred_2008=pred_2008, lam_final=lam_final,
                                        trB=trB, teB=teB, pred_2007=fit_gblup(trB, teB, G, lam_val))
        log('pop layer', cl, trait, 'lam_final', lam_final)

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
        if len(trA) and len(teA):
            SA, bA, cmA, muA = build(trA)
            lam_val = max(grid_abs, key=lambda l: med_within(predict(teA.gi.values, solve_ridge(SA, bA, l), cmA, muA), teA))
        else:
            lam_val = grid_abs[0]   # arbitrary: no 2004/2005 populations in the sample (see README)

        trB = lines[lines.YEAR <= 2006]; teB = lines[lines.YEAR == 2007]
        if len(trB) and len(teB):
            SB, bB, cmB, muB = build(trB)
            preds_by_lam = {l: predict(teB.gi.values, solve_ridge(SB, bB, l), cmB, muB) for l in grid_abs}
            lam_final = max(grid_abs, key=lambda l: med_within(preds_by_lam[l], teB))
        else:
            lam_final = grid_abs[0]

        trC = lines[lines.YEAR <= 2007]
        SC, bC, cmC, muC = build(trC)
        beta_final = solve_ridge(SC, bC, lam_final)
        pred_2008 = predict(teC_gi, beta_final, cmC, muC)

        within_result[(cl, trait)] = dict(lam_final=lam_final, p=p, idx_2008=design_lines, pred_2008=pred_2008)
        log('within layer', cl, trait, 'lam_final/p', round(lam_final / p, 2))

    d8cl = d8[d8.CL == cl]
    design = d8cl.groupby('LINE_ID').agg(POP=('POP', 'first'), P1=('P1', 'first'), P2=('P2', 'first'),
                                          TESTER=('TESTER', 'first'), n_locs_2008=('LOC', 'nunique'),
                                          n_plots_2008=('LOC', 'size'))
    design_by_cl[cl] = design

# ==================== moisture slope b (pooled within-ENV, historical plots present) ====================
plots = ph[(ph.YEAR >= 2005) & (ph.YEAR <= 2007)].dropna(subset=['YLD_BE', 'MST']).copy()
plots['dev_y'] = plots['YLD_BE'] - plots.groupby('ENV')['YLD_BE'].transform('mean')
plots['dev_m'] = plots['MST'] - plots.groupby('ENV')['MST'].transform('mean')
b_slope = float((plots.dev_y * plots.dev_m).sum() / (plots.dev_m ** 2).sum()) if len(plots) else 0.0
log('moisture slope b', b_slope)

# ==================== assemble judge_mode_output.csv (same columns as predictions_2008.csv) ====================
from scipy.stats import pearsonr

frames = []
for cl in CLUSTERS_PRESENT:
    design = design_by_cl[cl].copy(); design['CL'] = cl; design['GEN_OBS'] = design['POP'].map(t['GEN'])
    for trait, col in [('YLD_BE', 'pred_pop'), ('MST', 'pred_pop_MST'), ('TWT', 'pred_pop_TWT')]:
        pr = pop_result[(cl, trait)]
        design[col] = design['POP'].map(pd.Series(pr['pred_2008'], index=pr['idx_2008']))
    for trait, col in [('YLD_BE', 'pred_within'), ('MST', 'pred_within_MST'), ('TWT', 'pred_within_TWT')]:
        wr = within_result[(cl, trait)]
        design[col] = pd.Series(wr['pred_2008'], index=wr['idx_2008']).reindex(design.index).values
    design['score'] = design['pred_pop'] + design['pred_within']
    design['pred_MST'] = design['pred_pop_MST'] + design['pred_within_MST']
    design['pred_TWT'] = design['pred_pop_TWT'] + design['pred_within_TWT']
    design['score_adj'] = design['score'] - b_slope * design['pred_MST']

    cp = conf_by_cl[cl]
    design['parents_seen'] = design['POP'].map(cp['parents_seen'])
    design['n_hist_lines_parents'] = design['POP'].map(cp['n_hist_lines_parents'])
    design['near_repeat'] = design['POP'].map(cp['near_repeat'])
    design['tester_seen'] = design['POP'].map(cp['tester_seen'])
    design['gen_flag'] = design['POP'].map(t['gen_flag'])

    prB = pop_result[(cl, 'YLD_BE')]
    psB, _, _ = strata(prB['trB'], prB['teB'], gp)
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

full[PRED_COLS].to_csv(os.path.join(C.OUT, 'judge_mode_output.csv'), index=False)
log('wrote judge_mode_output.csv', len(full), 'rows')
# The deliverable also always lands at the canonical outputs/judge_mode_output.csv (the path the
# task lists), even when MAIZE_OUT points at an isolated dir like outputs_judge/ -- see README.
_canon = os.path.join(C.EXPL, 'outputs', 'judge_mode_output.csv')
if os.path.abspath(_canon) != os.path.abspath(os.path.join(C.OUT, 'judge_mode_output.csv')):
    full[PRED_COLS].to_csv(_canon, index=False)
    log('also wrote', _canon)


def selfcheck():
    assert len(full) > 0
    assert set(PRED_COLS) <= set(full.columns)
    assert full['score'].notna().all()
    for cl, g in full.groupby('CL'):
        assert g['rank_cluster'].is_unique, cl
    real_cols = pd.read_csv(os.path.join(C.EXPL, 'outputs', 'predictions_2008.csv'), nrows=0).columns
    assert list(real_cols) == PRED_COLS, 'judge_mode_output.csv columns must match predictions_2008.csv'
    log('selfcheck OK')


selfcheck()

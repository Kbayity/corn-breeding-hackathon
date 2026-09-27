"""Phase 2c: accuracy experiments (E1-E6) on top of the final_model.py baseline, YLD_BE, tuned on
2005->2006, evaluated on 2006->2007.

Baseline reproduction copies the population/within-layer fit calls from final_model.py rather than
importing it: final_model.py is a run-on-import script (fits every trait/cluster and writes
outputs/predictions_2008.csv etc. as soon as it's imported), so importing it would re-run the whole
Task-2 pipeline and could clobber protected outputs. model_lib.py and step1e_parents.py have no such
side effects (parent_groups just reads a CSV), so their functions are imported directly and the
minimal data-prep loop is copied here, using the FINAL grid values already chosen on the 2005->2006
fold in outputs/final_validation.csv (lam_mult_val / within_lam_over_p_val columns) instead of
re-running pick_lam.

Two run stages (so Deliverable 1 can be copied off the box before the experiments finish):
  python accuracy_experiments.py val    -> writes outputs/val2007_lines.csv, then exits
  python accuracy_experiments.py exp    -> (re)computes baseline fits + runs E1-E6, writes
                                            outputs/accuracy_experiments.md
  python accuracy_experiments.py all    -> both, in order (default)
"""
import os, sys, time
import numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr
from scipy.optimize import nnls
import common as C
from step1e_parents import parent_groups
from model_lib import fit_gblup, solve_ridge, med_within, top10_enrichment

t0 = time.time()


def log(*a):
    print(*a, f'[{(time.time() - t0) / 60:.1f} min]', flush=True)


FOLD_A = (2005, 2006)   # tune here
FOLD_B = (2006, 2007)   # evaluate here (== the "2007 validation" fold the brief's baseline numbers are from)

fv = pd.read_csv(os.path.join(C.OUT, 'final_validation.csv')).set_index(['CL', 'trait'])
POP_LAM = fv['lam_mult_val']               # pinned population-layer lam_mult (already chosen on fold A)
WITHIN_MULT = fv['within_lam_over_p_val']  # pinned within-layer lambda/p (already chosen on fold A)

# published baseline (brief), YLD_BE, 2007 fold -- self-check target for Deliverable 1
BASELINE = {
    'C1': dict(pop_pearson=0.380, within_rMP_median=0.287, combined_spearman=0.201, top10_enrichment=1.27),
    'C2': dict(pop_pearson=0.303, within_rMP_median=0.194, combined_spearman=0.215, top10_enrichment=1.04),
}


# ==================== data (loaded once, shared by baseline + all experiments) ====================
def load_all():
    ph = C.load_pheno()
    t = C.pop_table(ph)
    pm_by_trait = {tr: C.pop_means(ph, tr) for tr in ['YLD_BE', 'MST', 'TWT']}
    return ph, t, pm_by_trait


# ==================== population layer ====================
def pop_frame(cl, trait, t, pm_by_trait, train_max, test_year):
    pops = t[t.CL == cl].join(pm_by_trait[trait]['dev'])
    tr = pops[pops.YEAR <= train_max].dropna(subset=['dev'])
    te = pops[pops.YEAR == test_year].dropna(subset=['dev'])
    return tr, te


def pop_fit(cl, trait, G, t, pm_by_trait, lam, train_max, test_year):
    tr, te = pop_frame(cl, trait, t, pm_by_trait, train_max, test_year)
    return tr, te, fit_gblup(tr, te, G, lam)


# ==================== within (line) layer ====================
def within_frame(cl, trait, ph, kidx, train_max, test_year):
    lm = C.line_means(ph, trait, 'TRIAL')
    lines = lm[(lm.CL == cl) & lm.index.isin(kidx.index)].copy()
    lines['gi'] = kidx[lines.index].values
    return lines[lines.YEAR <= train_max], lines[lines.YEAR == test_year]


def within_fit(X_all, tr, te, lam_mult):
    X = np.asarray(X_all[tr.gi.values], np.float64)
    cmean = X.mean(0); X = X - cmean
    S = X.T @ X; b = X.T @ tr.y.values; p = X.shape[1]
    beta = solve_ridge(S, b, lam_mult * p)
    Xte = np.asarray(X_all[te.gi.values], np.float64) - cmean
    return tr.y.values.mean() + Xte @ beta, p


# ==================== relatedness-weighted within rrBLUP (E5; see step5_withinpop.py "weighted") ====================
def within_weighted_fit(X_all, cl, t, gp, tr, te, lam_mult):
    """Blend weight per training population: 0.95 to pops sharing both parent groups with the test
    population, 0.45 sharing one, 0.05 baseline (matches step5_withinpop.py's pred_weighted scheme;
    reuses the pinned global lam -- no extra grid search, to keep this inside the box time budget)."""
    tpop = t[t.CL == cl].copy(); tpop['G1'] = tpop.P1.map(gp); tpop['G2'] = tpop.P2.map(gp)
    X = np.asarray(X_all[tr.gi.values], np.float64); cmean = X.mean(0); X = X - cmean
    p = X.shape[1]; lam = lam_mult * p
    S_all = X.T @ X; b_all = X.T @ tr.y.values
    Xte = np.asarray(X_all[te.gi.values], np.float64) - cmean
    trpops = tpop.loc[tr.POP.unique()]
    pop_idx = {pop: np.where(tr.POP.values == pop)[0] for pop in trpops.index}
    pred = np.full(len(te), np.nan)
    for pop in te.POP.unique():
        r = tpop.loc[pop]; jj = np.where(te.POP.values == pop)[0]; tg = {r.G1, r.G2}
        share2 = [q for q in trpops.index if {trpops.loc[q].G1, trpops.loc[q].G2} == tg]
        share1 = [q for q in trpops.index if q not in share2 and ({trpops.loc[q].G1, trpops.loc[q].G2} & tg)]
        S = 0.05 * S_all; b = 0.05 * b_all
        if share2:
            idx2 = np.concatenate([pop_idx[q] for q in share2]); Xs = X[idx2]
            S = S + 0.95 * (Xs.T @ Xs); b = b + 0.95 * (Xs.T @ tr.y.values[idx2])
        if share1:
            idx1 = np.concatenate([pop_idx[q] for q in share1]); Xs = X[idx1]
            S = S + 0.45 * (Xs.T @ Xs); b = b + 0.45 * (Xs.T @ tr.y.values[idx1])
        pred[jj] = tr.y.values.mean() + Xte[jj] @ solve_ridge(S, b, lam)
    return pred


# ==================== historical-mean population models (E2; reimplemented, see step4_popmean.py) ====================
def histmean_pred(train_pops, test_pops, gp):
    tr = train_pops.copy(); tr['G1'] = tr.P1.map(gp); tr['G2'] = tr.P2.map(gp)
    long = pd.concat([tr[['G1', 'dev']].rename(columns={'G1': 'G'}), tr[['G2', 'dev']].rename(columns={'G2': 'G'})])
    m = long.groupby('G').dev.mean(); overall = tr.dev.mean()
    te = test_pops.copy(); te['G1'] = te.P1.map(gp); te['G2'] = te.P2.map(gp)
    return (te.W1 * te.G1.map(m).fillna(overall) + te.W2 * te.G2.map(m).fillna(overall)).values


def tester_mean_pred(train_pops, test_pops):
    m = train_pops.groupby('TESTER').dev.mean(); overall = train_pops.dev.mean()
    return test_pops.TESTER.map(m).fillna(overall).values


# ==================== metrics ====================
def cluster_metrics(pop_pred, pop_te, within_pred, within_te, score, y_true):
    """pop_pred/pop_te: population-level (order-aligned). within_pred/within_te: line-level
    (order-aligned, within_te has POP+y for med_within). score/y_true: line-level Series, any order
    (aligned to each other by pandas index)."""
    pop_pearson = pearsonr(np.asarray(pop_pred, float), pop_te.dev.values)[0]
    within_rmp = med_within(np.asarray(within_pred, float), within_te)
    score = pd.Series(score); y_true = pd.Series(y_true)
    keep = score.notna() & y_true.notna()
    s, y = score[keep].values, y_true[keep].values
    return dict(pop_pearson=pop_pearson, within_rMP_median=within_rmp,
                combined_spearman=spearmanr(s, y)[0], top10_enrichment=top10_enrichment(s, y, len(y)))


def bootstrap_delta_ci(pop_of, baseline_score, exp_score, y_true, n_boot=1000, seed=0):
    """95% CI over populations for (exp combined-Spearman - baseline combined-Spearman)."""
    pop_of = np.asarray(pop_of)
    baseline_score = np.asarray(baseline_score, float); exp_score = np.asarray(exp_score, float); y_true = np.asarray(y_true, float)
    ok = ~np.isnan(baseline_score) & ~np.isnan(exp_score) & ~np.isnan(y_true)
    pop_of, b, e, y = pop_of[ok], baseline_score[ok], exp_score[ok], y_true[ok]
    pops = np.array(sorted(set(pop_of)))
    idx_by_pop = {p: np.where(pop_of == p)[0] for p in pops}
    rng = np.random.default_rng(seed)
    deltas = np.empty(n_boot)
    for i in range(n_boot):
        samp = rng.choice(pops, len(pops), replace=True)
        rows = np.concatenate([idx_by_pop[p] for p in samp])
        deltas[i] = spearmanr(e[rows], y[rows])[0] - spearmanr(b[rows], y[rows])[0]
    return dict(delta_mean=float(np.mean(deltas)), lo=float(np.percentile(deltas, 2.5)), hi=float(np.percentile(deltas, 97.5)))


# ==================== Deliverable 1: val2007_lines.csv ====================
def write_val2007_lines():
    ph, t, pm_by_trait = load_all()
    rows, metrics = [], {}
    for cl in C.CLUSTERS:
        G = C.parent_grm(cl)
        X_all, keys = C.geno_matrix(cl, 'filled'); kidx = pd.Series(np.arange(len(keys)), index=keys)

        pop_tr, pop_te, pop_pred = pop_fit(cl, 'YLD_BE', G, t, pm_by_trait, POP_LAM[(cl, 'YLD_BE')], *FOLD_B)
        w_tr, w_te = within_frame(cl, 'YLD_BE', ph, kidx, *FOLD_B)
        w_pred, p = within_fit(X_all, w_tr, w_te, WITHIN_MULT[(cl, 'YLD_BE')])
        log('baseline fit done', cl, 'YLD_BE')

        df = w_te[['POP', 'n']].rename(columns={'n': 'n_plots'}).copy()
        df['CL'] = cl
        df['pred_within'] = w_pred
        df['pred_pop'] = df['POP'].map(pd.Series(pop_pred, index=pop_te.index))
        df['score'] = df['pred_pop'] + df['pred_within']
        df['y_true'] = C.line_means(ph, 'YLD_BE', 'ENV')['y'].reindex(df.index)
        metrics[cl] = cluster_metrics(pop_pred, pop_te, w_pred, w_te, df['score'], df['y_true'])

        for trait in ['MST', 'TWT']:
            ptr, pte, ppred = pop_fit(cl, trait, G, t, pm_by_trait, POP_LAM[(cl, trait)], *FOLD_B)
            wtr, wte = within_frame(cl, trait, ph, kidx, *FOLD_B)
            wpred, _ = within_fit(X_all, wtr, wte, WITHIN_MULT[(cl, trait)])
            df[f'pred_{trait}'] = df['POP'].map(pd.Series(ppred, index=pte.index)) + pd.Series(wpred, index=wte.index).reindex(df.index)
            df[f'y_true_{trait}'] = C.line_means(ph, trait, 'ENV')['y'].reindex(df.index)
            log('baseline fit done', cl, trait)

        df = df.reset_index().rename(columns={'index': 'LINE_ID'})
        rows.append(df[['LINE_ID', 'CL', 'POP', 'y_true', 'n_plots', 'pred_pop', 'pred_within', 'score',
                         'pred_MST', 'pred_TWT', 'y_true_MST', 'y_true_TWT']])

    val = pd.concat(rows, ignore_index=True)
    val.to_csv(os.path.join(C.OUT, 'val2007_lines.csv'), index=False)
    log('wrote val2007_lines.csv', len(val), 'rows')

    for cl in C.CLUSTERS:
        m, exp = metrics[cl], BASELINE[cl]
        log('selfcheck', cl, {k: round(v, 3) for k, v in m.items()}, 'vs published', exp)
        assert abs(m['pop_pearson'] - exp['pop_pearson']) < 0.01, (cl, m, exp)
        assert abs(m['within_rMP_median'] - exp['within_rMP_median']) < 0.01, (cl, m, exp)
        assert abs(m['combined_spearman'] - exp['combined_spearman']) < 0.01, (cl, m, exp)
        assert abs(m['top10_enrichment'] - exp['top10_enrichment']) < 0.05, (cl, m, exp)
    log('selfcheck OK: reproduces published baseline (YLD_BE, 2007 fold)')
    return val


# ==================== experiments E1-E6 ====================
def run_experiments():
    ph, t, pm_by_trait = load_all()
    y_env = C.line_means(ph, 'YLD_BE', 'ENV')['y']
    results, ci, winners = {}, {}, {}

    def line_frame(within_te, within_pred, pop_te, pop_pred):
        d = within_te[['POP']].copy()
        d['pred_within'] = within_pred
        d['pred_pop'] = d['POP'].map(pd.Series(pop_pred, index=pop_te.index))
        d['y_true'] = y_env.reindex(d.index)
        d['score'] = d['pred_pop'] + d['pred_within']
        return d

    for cl in C.CLUSTERS:
        G = C.parent_grm(cl)
        X_all, keys = C.geno_matrix(cl, 'filled'); kidx = pd.Series(np.arange(len(keys)), index=keys)
        gp = parent_groups(cl)
        lam_pop, lam_within = POP_LAM[(cl, 'YLD_BE')], WITHIN_MULT[(cl, 'YLD_BE')]

        popA_tr, popA_te, popA_pred = pop_fit(cl, 'YLD_BE', G, t, pm_by_trait, lam_pop, *FOLD_A)
        popB_tr, popB_te, popB_pred = pop_fit(cl, 'YLD_BE', G, t, pm_by_trait, lam_pop, *FOLD_B)
        wA_tr, wA_te = within_frame(cl, 'YLD_BE', ph, kidx, *FOLD_A)
        wA_pred, _ = within_fit(X_all, wA_tr, wA_te, lam_within)
        wB_tr, wB_te = within_frame(cl, 'YLD_BE', ph, kidx, *FOLD_B)
        wB_pred, p = within_fit(X_all, wB_tr, wB_te, lam_within)
        log('baseline both folds done', cl)

        lineA = line_frame(wA_te, wA_pred, popA_te, popA_pred)
        lineB = line_frame(wB_te, wB_pred, popB_te, popB_pred)
        results[(cl, 'baseline')] = cluster_metrics(popB_pred, popB_te, wB_pred, wB_te, lineB['score'], lineB['y_true'])
        log('baseline metrics', cl, results[(cl, 'baseline')])

        combo = {}   # accumulates winning overrides (fold-A-improved) for E6

        # ---------------- E1: combined weights via NNLS ----------------
        XA = np.column_stack([lineA['pred_pop'].values, lineA['pred_within'].values])
        okA = ~np.isnan(XA).any(1) & lineA['y_true'].notna().values
        (a, b), _ = nnls(XA[okA], lineA['y_true'].values[okA])
        scoreB_e1 = a * lineB['pred_pop'] + b * lineB['pred_within']
        results[(cl, 'E1_weights')] = dict(cluster_metrics(popB_pred, popB_te, wB_pred, wB_te, scoreB_e1, lineB['y_true']), a=a, b=b)
        scoreA_e1 = a * lineA['pred_pop'] + b * lineA['pred_within']
        winA = spearmanr(scoreA_e1[okA], lineA['y_true'].values[okA])[0] > spearmanr(lineA['score'].values[okA], lineA['y_true'].values[okA])[0]
        winners[(cl, 'E1_weights')] = winA
        ci[(cl, 'E1_weights')] = bootstrap_delta_ci(lineB['POP'].values, lineB['score'].values, scoreB_e1.values, lineB['y_true'].values)
        if winA:
            combo['E1'] = (a, b)
        log('E1 done', cl, 'a,b=', round(a, 3), round(b, 3), 'win on fold A:', winA)

        # ---------------- E2: population-layer NNLS blend (gblup + histmean + tester mean) ----------------
        histA, histB = histmean_pred(popA_tr, popA_te, gp), histmean_pred(popB_tr, popB_te, gp)
        testA, testB = tester_mean_pred(popA_tr, popA_te), tester_mean_pred(popB_tr, popB_te)
        (w1, w2, w3), _ = nnls(np.column_stack([popA_pred, histA, testA]), popA_te.dev.values)
        popB_e2 = w1 * popB_pred + w2 * histB + w3 * testB
        lineB_e2 = lineB.copy(); lineB_e2['pred_pop'] = lineB_e2['POP'].map(pd.Series(popB_e2, index=popB_te.index))
        lineB_e2['score'] = lineB_e2['pred_pop'] + lineB_e2['pred_within']
        results[(cl, 'E2_pop_blend')] = dict(cluster_metrics(popB_e2, popB_te, wB_pred, wB_te, lineB_e2['score'], lineB_e2['y_true']), w1=w1, w2=w2, w3=w3)
        popA_e2 = w1 * popA_pred + w2 * histA + w3 * testA
        winA = pearsonr(popA_e2, popA_te.dev.values)[0] > pearsonr(popA_pred, popA_te.dev.values)[0]
        winners[(cl, 'E2_pop_blend')] = winA
        ci[(cl, 'E2_pop_blend')] = bootstrap_delta_ci(lineB['POP'].values, lineB['score'].values, lineB_e2['score'].values, lineB['y_true'].values)
        if winA:
            combo['E2'] = (w1, w2, w3)
        log('E2 done', cl, 'weights', round(w1, 3), round(w2, 3), round(w3, 3), 'win on fold A:', winA)

        # ---------------- E3: recency weighting in population GBLUP ----------------
        best_tau, best_r = None, -np.inf
        for tau in [2, 4, 8]:
            wA_ = np.exp(-(FOLD_A[1] - 1 - popA_tr.YEAR.values) / tau)
            r = pearsonr(fit_gblup(popA_tr, popA_te, G, lam_pop, weights=wA_), popA_te.dev.values)[0]
            if r > best_r:
                best_r, best_tau = r, tau
        winA = best_r > pearsonr(popA_pred, popA_te.dev.values)[0]
        winners[(cl, 'E3_recency')] = winA
        wB_ = np.exp(-(FOLD_B[1] - 1 - popB_tr.YEAR.values) / best_tau)
        popB_e3 = fit_gblup(popB_tr, popB_te, G, lam_pop, weights=wB_)
        lineB_e3 = lineB.copy(); lineB_e3['pred_pop'] = lineB_e3['POP'].map(pd.Series(popB_e3, index=popB_te.index))
        lineB_e3['score'] = lineB_e3['pred_pop'] + lineB_e3['pred_within']
        results[(cl, 'E3_recency')] = dict(cluster_metrics(popB_e3, popB_te, wB_pred, wB_te, lineB_e3['score'], lineB_e3['y_true']), tau=best_tau)
        ci[(cl, 'E3_recency')] = bootstrap_delta_ci(lineB['POP'].values, lineB['score'].values, lineB_e3['score'].values, lineB['y_true'].values)
        if winA:
            combo['E3'] = best_tau
        log('E3 done', cl, 'tau', best_tau, 'win on fold A:', winA)

        # ---------------- E4: reliability weighting (n_lines / (n_lines+k)) ----------------
        best_k, best_r = None, -np.inf
        for k in [20, 50, 100]:
            wA_ = popA_tr.n_lines.values / (popA_tr.n_lines.values + k)
            r = pearsonr(fit_gblup(popA_tr, popA_te, G, lam_pop, weights=wA_), popA_te.dev.values)[0]
            if r > best_r:
                best_r, best_k = r, k
        winA = best_r > pearsonr(popA_pred, popA_te.dev.values)[0]
        winners[(cl, 'E4_reliability')] = winA
        wB_ = popB_tr.n_lines.values / (popB_tr.n_lines.values + best_k)
        popB_e4 = fit_gblup(popB_tr, popB_te, G, lam_pop, weights=wB_)
        lineB_e4 = lineB.copy(); lineB_e4['pred_pop'] = lineB_e4['POP'].map(pd.Series(popB_e4, index=popB_te.index))
        lineB_e4['score'] = lineB_e4['pred_pop'] + lineB_e4['pred_within']
        results[(cl, 'E4_reliability')] = dict(cluster_metrics(popB_e4, popB_te, wB_pred, wB_te, lineB_e4['score'], lineB_e4['y_true']), k=best_k)
        ci[(cl, 'E4_reliability')] = bootstrap_delta_ci(lineB['POP'].values, lineB['score'].values, lineB_e4['score'].values, lineB['y_true'].values)
        if winA:
            combo['E4'] = best_k
        log('E4 done', cl, 'k', best_k, 'win on fold A:', winA)

        # ---------------- E5: within-layer blend (global rrBLUP + relatedness-weighted rrBLUP) ----------------
        # Lines are tested in exactly one year per population, so no 2007 population has historical
        # (prior-year) siblings -- E5 as literally specified (blend with a per-population rrBLUP
        # fitted only on the test population's own historical siblings) is undefined. Falling back
        # to the brief's named alternative: blend with the relatedness-weighted rrBLUP already
        # validated in step5_withinpop.py ("pred_weighted": 0.95/0.45/0.05 by shared parent groups),
        # reusing its pinned lam (no extra grid search, to stay in the box time budget).
        relA = within_weighted_fit(X_all, cl, t, gp, wA_tr, wA_te, lam_within)
        relB = within_weighted_fit(X_all, cl, t, gp, wB_tr, wB_te, lam_within)
        log('E5 relatedness-weighted rrBLUP fit done', cl)
        (u1, u2), _ = nnls(np.column_stack([wA_pred, relA]), wA_te.y.values)
        winA = med_within(u1 * wA_pred + u2 * relA, wA_te) > med_within(wA_pred, wA_te)
        winners[(cl, 'E5_within_blend')] = winA
        wB_e5 = u1 * wB_pred + u2 * relB
        lineB_e5 = lineB.copy(); lineB_e5['pred_within'] = wB_e5; lineB_e5['score'] = lineB_e5['pred_pop'] + lineB_e5['pred_within']
        results[(cl, 'E5_within_blend')] = dict(cluster_metrics(popB_pred, popB_te, wB_e5, wB_te, lineB_e5['score'], lineB_e5['y_true']),
                                                 u1=u1, u2=u2, note='relatedness-weighted fallback (see module docstring / E5 comment)')
        ci[(cl, 'E5_within_blend')] = bootstrap_delta_ci(lineB['POP'].values, lineB['score'].values, lineB_e5['score'].values, lineB['y_true'].values)
        if winA:
            combo['E5'] = (u1, u2, relB)
        log('E5 done', cl, 'u1,u2', round(u1, 3), round(u2, 3), 'win on fold A:', winA)

        # ---------------- E6: stack every winning change from E1-E5 (this cluster), eval once on 2007 ----------------
        pop_pred_final, within_pred_final, applied = popB_pred, wB_pred, []
        if 'E2' in combo:
            w1, w2, w3 = combo['E2']; pop_pred_final = w1 * popB_pred + w2 * histB + w3 * testB; applied.append('E2')
        elif 'E4' in combo:
            wB_ = popB_tr.n_lines.values / (popB_tr.n_lines.values + combo['E4'])
            pop_pred_final = fit_gblup(popB_tr, popB_te, G, lam_pop, weights=wB_); applied.append('E4')
            if 'E3' in combo:
                applied.append('E3_skipped_conflict_with_E4')
        elif 'E3' in combo:
            wB_ = np.exp(-(FOLD_B[1] - 1 - popB_tr.YEAR.values) / combo['E3'])
            pop_pred_final = fit_gblup(popB_tr, popB_te, G, lam_pop, weights=wB_); applied.append('E3')
        if 'E5' in combo:
            u1, u2, relB_ = combo['E5']; within_pred_final = u1 * wB_pred + u2 * relB_; applied.append('E5')
        line_final = lineB.copy()
        line_final['pred_pop'] = line_final['POP'].map(pd.Series(pop_pred_final, index=popB_te.index))
        line_final['pred_within'] = within_pred_final
        line_final['score'] = line_final['pred_pop'] + line_final['pred_within']
        if 'E1' in combo:
            a, b = combo['E1']; line_final['score'] = a * line_final['pred_pop'] + b * line_final['pred_within']; applied.append('E1')
        results[(cl, 'E6_combo')] = dict(cluster_metrics(pop_pred_final, popB_te, within_pred_final, wB_te, line_final['score'], line_final['y_true']),
                                          applied=applied or ['none (nothing won on fold A)'])
        ci[(cl, 'E6_combo')] = bootstrap_delta_ci(lineB['POP'].values, lineB['score'].values, line_final['score'].values, lineB['y_true'].values)
        log('E6 done', cl, 'applied', applied)

    write_report(results, ci)


def write_report(results, ci):
    order = ['baseline', 'E1_weights', 'E2_pop_blend', 'E3_recency', 'E4_reliability', 'E5_within_blend', 'E6_combo']
    rows = []
    for cl in C.CLUSTERS:
        for name in order:
            m = results[(cl, name)]
            row = dict(CL=cl, experiment=name, pop_pearson=m['pop_pearson'], within_rMP_median=m['within_rMP_median'],
                       combined_spearman=m['combined_spearman'], top10_enrichment=m['top10_enrichment'])
            if name != 'baseline':
                b = results[(cl, 'baseline')]
                row['delta_combined_spearman'] = m['combined_spearman'] - b['combined_spearman']
                c = ci[(cl, name)]
                row['delta_ci_lo'], row['delta_ci_hi'] = c['lo'], c['hi']
            rows.append(row)
    tab = pd.DataFrame(rows)

    adopt = []
    for name in order[1:]:
        cis = [ci[(cl, name)] for cl in C.CLUSTERS]
        excludes0 = any(not (c['lo'] <= 0 <= c['hi']) for c in cis)
        worsens = any(results[(cl, name)]['combined_spearman'] < results[(cl, 'baseline')]['combined_spearman'] - 1e-6 for cl in C.CLUSTERS)
        if excludes0 and not worsens:
            adopt.append(name)

    applied_note = '; '.join(f"{cl}: {results[(cl, 'E6_combo')]['applied']}" for cl in C.CLUSTERS)
    md = ['# Accuracy experiments (YLD_BE, tuned on 2005->2006, evaluated on 2006->2007)\n',
          tab.round(4).to_markdown(index=False) + '\n',
          '## Conclusion\n',
          f'- Adopt: {", ".join(adopt) if adopt else "none"} (95% bootstrap CI over populations excludes 0 for the '
          'combined-Spearman delta on at least one cluster, and neither cluster gets worse).\n',
          '- Everything else above is within noise: its bootstrap CI on the combined-Spearman delta straddles 0 on '
          'both clusters, or it makes at least one cluster worse.\n',
          '- E5 could not be run as literally specified (no 2007 population has historical same-year-tested '
          'siblings, since every population is tested in exactly one year); it blends global rrBLUP with the '
          'relatedness-weighted rrBLUP already validated in step5_withinpop.py instead.\n',
          f'- E6 stacks, per cluster, only the changes whose OWN fold-A (2005->2006) metric improved: {applied_note}.\n',
          '- Grids matched the brief (tau in {2,4,8}, k in {20,50,100}); E5 skipped its own extra lambda grid '
          '(reused the pinned global lam) to stay inside the 90-minute box budget.\n']
    open(os.path.join(C.OUT, 'accuracy_experiments.md'), 'w').write('\n'.join(md))
    log('wrote accuracy_experiments.md')
    print(tab.round(4).to_string())


if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if stage in ('val', 'all'):
        write_val2007_lines()
    if stage in ('exp', 'all'):
        run_experiments()

# Precompute the prediction tables the app reads (so the app is instant and never fits a genotype model live).
#   python app/precompute.py            (~40 min; writes cache/app/)
# For target season Y in 2005-2008 and data cutoff k in 1..3 (newest training season = Y-k, i.e. what was known on
# 1 Nov of that season, after its harvest), per cluster:
#   family parts from each family model separately (pedigree 'ped_gca' / DNA 'par_genomic': gca and tester parts),
#   the traditional parent-history baseline, and the within-family DNA deviation D (rrBLUP on HMM genotypes);
#   marker effects (beta) are stored so the app can score custom crosses live.
# Truth for evaluation: season Y stage-1 values; 2008 from the answer key, flagged posthoc=True (2008 was evaluated
# once on 2026-09-26; nothing here or in the app is tuned on it).
import os, sys, json, numpy as np, pandas as pd, warnings
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import hackdata as H, famodels as F, gp
from paths import S
warnings.filterwarnings('ignore')
OUT = f'{S}/app'; os.makedirs(OUT, exist_ok=True); TC = 'pop_eff_YLD'
YEARS = [int(y) for y in os.environ.get('APP_YEARS', '2005 2006 2007 2008').split()]; KS = [1, 2, 3]
def log(*a): print(*a, flush=True)

allp_hist = pd.concat([H.load_pops(before=2008, include_target_year=False), H.load_holdout_2008()[2]], ignore_index=True)
meta_all = pd.read_parquet(f'{S}/model/pops.parquet')                 # pre-planting family info for every season
lines_all = pd.concat([H.load_lines(before=2008), H.load_holdout_2008()[1]], ignore_index=True)
L_rows, F_rows, betas, info = [], [], {}, []
for Y in YEARS:
    for cl in ['C1', 'C2']:
        PG = H.load_parent_geno(cl); PG = PG.fillna(PG.mean()).fillna(0.0)
        tgt0 = meta_all[(meta_all.YEAR == Y) & (meta_all.CL == cl)].reset_index(drop=True)
        cand = H.load_candidates(Y); cand = cand[(cand.CL == cl) & cand.has_geno]
        Xc, kc = H.load_geno(cl, cand.LINE_KEY); cand = cand.set_index('LINE_KEY').loc[kc].reset_index()
        for k in KS:
            last = Y - k
            hist = allp_hist[(allp_hist.CL == cl) & (allp_hist.YEAR <= last)].dropna(subset=[TC]).reset_index(drop=True)
            tgt = tgt0.copy(); seen = set(hist.P1) | set(hist.P2); tseen = set(hist.TESTER)
            tgt['n_par_seen'] = tgt.P1.isin(seen).astype(int) + tgt.P2.isin(seen).astype(int); tgt['tester_seen'] = tgt.TESTER.isin(tseen)
            fr = tgt[['POP', 'CL', 'P1', 'P2', 'RP', 'GEN', 'TESTER', 'n_par_seen', 'tester_seen']].copy(); fr['YEAR'] = Y; fr['k'] = k; fr['train_last'] = last
            for m, tag in [('ped_gca', 'ped'), ('par_genomic', 'dna')]:
                o = F.fit(m, hist, tgt, TC, PG, **F.tune(m, hist, TC, last + 1, PG)); fr[f'gca_{tag}'] = o.gca.values; fr[f'tst_{tag}'] = o.tester.values
            fr['gca_parent_history'] = F.parent_hist(hist, tgt, TC, **F.tune('parent_hist', hist, TC, last + 1)).gca.values
            F_rows.append(fr)
            tr = lines_all[(lines_all.CL == cl) & (lines_all.YEAR <= last) & lines_all.has_geno].dropna(subset=['y_w_YLD']).reset_index(drop=True)
            Xtr, kk = H.load_geno(cl, tr.LINE_KEY); tr = tr.set_index('LINE_KEY').loc[kk].reset_index()
            model, beta, lam, inner_r, slope = gp.fit_within_model(tr, Xtr, last + 1); del Xtr
            slope = float(np.clip(slope, 0.5, 3.0)); m_ = model.predict(Xc, beta)
            D = slope * (m_ - pd.Series(m_).groupby(cand.POP.values).transform('mean').values)
            L_rows.append(pd.DataFrame({'LINE_KEY': cand.LINE_KEY, 'CL': cl, 'POP': cand.POP, 'YEAR': Y, 'k': k, 'D': D}))
            betas[f'{cl}_{Y}_{k}'] = beta.astype(np.float32); betas[f'{cl}_{Y}_{k}_mu'] = model.mu_x.astype(np.float32)
            info.append(dict(cl=cl, year=Y, k=k, train_last=last, slope_D=slope, lam=lam, n_train_lines=len(tr), n_hist_fam=len(hist),
                             n_plots_hist=None))
            log(f'{Y} {cl} k={k} (train <= {last}): {len(tgt)} families, {len(cand)} lines, {len(tr)} training lines')
        del Xc
Lp = pd.concat(L_rows, ignore_index=True); Fp = pd.concat(F_rows, ignore_index=True)
Lp.to_parquet(f'{OUT}/line_preds.parquet'); Fp.to_parquet(f'{OUT}/family_preds.parquet'); np.savez_compressed(f'{OUT}/betas.npz', **betas)
pd.DataFrame(info).to_csv(f'{OUT}/fit_info.csv', index=False)
# truth (evaluation only)
tl = lines_all[lines_all.YEAR.isin(YEARS)][['LINE_KEY', 'CL', 'POP', 'YEAR', 'y_tot_YLD', 'y_w_YLD', 'pop_eff_YLD']].copy(); tl['posthoc'] = tl.YEAR == 2008
tl.to_parquet(f'{OUT}/truth_lines.parquet')
tf = allp_hist[allp_hist.YEAR.isin(YEARS)][['POP', 'CL', 'YEAR', TC, 'pop_eff_MST', 'pop_eff_TWT']].copy(); tf['posthoc'] = tf.YEAR == 2008
tf.to_parquet(f'{OUT}/truth_families.parquet')
# data availability counts per season (for "data points used")
pl = pd.concat([H.load_plots(before=2008), H.load_holdout_2008()[0]], ignore_index=True)
pl.groupby(['CL', 'YEAR']).agg(plots=('YLD', 'size'), lines=('LINE_KEY', 'nunique'), families=('POP', 'nunique'), locations=('LOC', 'nunique')).reset_index().to_csv(f'{OUT}/season_counts.csv', index=False)
log('done ->', OUT)

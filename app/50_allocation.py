# Step 5: plot allocation under a budget -- conservative vs aggressive selection, validated on 2006 and 2007.
#
# Simulated season per cluster-year (scores from 40_score.py, i.e. January information only):
#   1. January: a strategy picks budget b of the candidate lines to receive testcross plots.
#   2. Field:   the program advances the top 5% of ALL candidates, chosen among planted lines by their
#               observed yield in half A of the family's locations (phenotypic selection).
#   3. Score:   realized merit of the advanced lines = their yield in the OTHER half B of locations,
#               so lucky plots in A are not rewarded.
# Two truths:
#   gca        plot yield minus location and tester effects -> the line's own merit (advancement decision)
#   testcross  plot yield minus location effects only -> raw hybrid performance, tester included
# Strategies score lines with the matching prediction (gca = F + D, or testcross = F + T + D).
# Risk: R replicates, each = random A/B location split + bootstrap resample of families.
#
# Strategies:
#   random            no information
#   parent_history    family by parents' past families (traditional pedigree), random within family
#   markers_within    spread: every family gets its proportional share, best lines inside each by markers (D)
#   tilt<tau>         every family keeps a share, scaled by clip(1 + tau * z(family prediction), 0, 3)
#   kappa<k>[_cap]    rank all lines by score + k * sd (k < 0 penalizes uncertainty, > 0 rewards upside);
#                     _cap limits any family to 2x its proportional share
import numpy as np, pandas as pd, os, time
import hackdata as H, famodels as F
from paths import S

OUT = f'{S}/results'; FIG = f'{OUT}/figs'; os.makedirs(FIG, exist_ok=True)
TRUTHS = ['gca', 'testcross']
FIELD_LAMBDA = float(os.environ.get('FIELD_INDEX_LAMBDA', '0'))   # weight on the DNA prediction in the field-stage index
YEARS = [int(y) for y in os.environ.get('ALLOC_YEARS', '2006 2007').split()]; BUDGETS = [float(b) for b in os.environ.get('ALLOC_BUDGETS', '0.10 0.25 0.50 0.75 1.00').split()]; FINAL = 0.05; R = 100
KAPPAS = [-2, -1, -0.5, 0, 0.5, 1, 2]; TAUS = [0.25, 0.5, 1, 2]; CAP_MULT = 2.0
rng = np.random.default_rng(7)
t0 = time.time()
def log(*a): print(f'[{time.time()-t0:5.0f}s]', *a, flush=True)


def adjusted(p, tester=True, iters=15):
    """Residual of plot yield after ENV (and, if tester, additive TESTER) effects (alternating means)."""
    y = p.YLD.values; ge, gt = p.ENV.values, p.TESTER.values
    if not tester:
        return y - pd.Series(y).groupby(ge).transform('mean').values
    mu = y.mean(); env = np.zeros(len(p)); tst = np.zeros(len(p))
    for _ in range(iters):
        env = pd.Series(y - mu - tst).groupby(ge).transform('mean').values
        tst = pd.Series(y - mu - env).groupby(gt).transform('mean').values
    return y - mu - env - tst


def select(score, inst, n_b, cap=None):
    """Indices of the n_b best by score; with cap, at most cap[instance] lines per family instance, then fill."""
    order = np.argsort(-score, kind='stable')
    if cap is None: return order[:n_b]
    fo = inst[order]
    rank_in_fam = pd.Series(np.ones(len(fo))).groupby(fo).cumsum().values - 1
    ok = rank_in_fam < cap[fo]
    first = order[ok][:n_b]
    if len(first) < n_b:
        first = np.concatenate([first, order[~ok][:n_b - len(first)]])
    return first


def quota(kind, sizes, b, zfam):
    """Per-family-instance line cap. kind: None | 'cap' | 'even' | ('tilt', tau); zfam: z-score per instance."""
    if kind is None: return None
    if kind == 'cap': return np.ceil(CAP_MULT * b * sizes).astype(int)
    if kind == 'even': return np.ceil(b * sizes).astype(int)
    w = np.clip(1 + kind[1] * zfam, 0, 3); w = w * sizes.sum() / (w * sizes).sum()
    return np.ceil(b * sizes * w).astype(int)


def season(sel, vA, vB, n_final, pool_B, pred=None, lam=0.0):
    """Field stage among planted lines by half-A yield (+ lam x DNA prediction: combined field-stage index, off by
    default); outcome = half-B yield of the advanced lines vs pool."""
    a = vA[sel] + (lam * pred[sel] if (pred is not None and lam) else 0.0)
    a = np.where(np.isnan(a), -np.inf, a)
    fin = sel[np.argsort(-a, kind='stable')[:n_final]] if len(sel) > n_final else sel
    return np.nanmean(vB[fin]) - pool_B


def strategies_for(s, truth, N):
    """name -> (score function, family quota kind, per-family z used by tilt)."""
    col, fcol = ('gca', 'F') if truth == 'gca' else ('testcross', 'FT')
    fz = s.groupby('POP')[fcol].first(); fz = (fz - fz.mean()) / fz.std()
    st = {'random': (lambda: rng.random(N), None, None),
          'parent_history': (lambda: s.F_ph.fillna(0).values + 1e-6 * rng.random(N), None, None),
          'markers_within': (lambda: s.D.values, 'even', None)}
    for tau in TAUS:
        st[f'tilt{tau:g}'] = (lambda: s.D.values, ('tilt', tau), fz)
    for k in KAPPAS:
        st[f'kappa{k:+g}'] = (lambda k=k: (s[col] + k * s.sd).values, None, None)
        st[f'kappa{k:+g}_cap'] = (lambda k=k: (s[col] + k * s.sd).values, 'cap', None)
    return st


def main():
    global rng
    rows, det = [], []
    for Y in YEARS:
        sc = pd.read_parquet(f'{OUT}/scores_{Y}.parquet')
        pl = H.load_plots(before=Y + 1); pl = pl[(pl.YEAR == Y) & pl.YLD.notna()]
        for cl in ['C1', 'C2']:
            s = sc[sc.CL == cl]
            p = pl[(pl.CL == cl) & pl.LINE_KEY.isin(set(s.LINE_KEY))].copy()
            s = s[s.LINE_KEY.isin(set(p.LINE_KEY))].reset_index(drop=True)
            s['FT'] = s.F + s['T']
            p['li'] = pd.Series(np.arange(len(s)), index=s.LINE_KEY)[p.LINE_KEY].values
            p['res_gca'] = adjusted(p, tester=True); p['res_testcross'] = adjusted(p, tester=False)
            N = len(s)
            full = {t: p.groupby('li')[f'res_{t}'].mean().reindex(range(N)).values for t in TRUTHS}
            # parent-history family score (traditional baseline), fit on families before Y
            pops = H.load_pops(before=Y, cl=cl)
            hist = pops[pops.YEAR < Y].dropna(subset=['pop_eff_YLD']).reset_index(drop=True); tgt = pops[pops.YEAR == Y].reset_index(drop=True)
            ph = F.parent_hist(hist, tgt, 'pop_eff_YLD', **F.tune('parent_hist', hist, 'pop_eff_YLD', Y))
            s['F_ph'] = s.POP.map(pd.Series(ph.gca.values, index=tgt.POP))
            fam_codes, fam = np.unique(s.POP.values, return_inverse=True); sizes = np.bincount(fam)
            strat = {t: strategies_for(s, t, N) for t in TRUTHS}
            zfam = {t: {n: (v[2].reindex(fam_codes).fillna(0).values if v[2] is not None else None) for n, v in strat[t].items()} for t in TRUTHS}
            pe = p[['POP', 'ENV']].drop_duplicates().reset_index(drop=True)
            pe_index = pd.MultiIndex.from_frame(pe); p_index = pd.MultiIndex.from_frame(p[['POP', 'ENV']])
            n_final = max(int(round(FINAL * N)), 1)
            for rep in range(R):
                h = pd.Series(rng.integers(0, 2, len(pe)), index=pe_index).reindex(p_index).values
                bf = rng.integers(0, len(fam_codes), len(fam_codes))                 # family bootstrap
                idx = np.concatenate([np.where(fam == f)[0] for f in bf]); inst = np.repeat(np.arange(len(bf)), sizes[bf])
                n_fin = max(int(round(FINAL * len(idx))), 1)
                pidx = {'gca': s.gca.values[idx], 'testcross': s.testcross.values[idx]}   # DNA prediction for the field index
                for t in TRUTHS:
                    vA = p[h == 0].groupby('li')[f'res_{t}'].mean().reindex(range(N)).values[idx]
                    vB = p[h == 1].groupby('li')[f'res_{t}'].mean().reindex(range(N)).values[idx]
                    pool_B = np.nanmean(vB)
                    for name, (fn, kind, _) in strat[t].items():
                        scb = fn()[idx]; zf = zfam[t][name]; zb = zf[bf] if zf is not None else None
                        for b in BUDGETS:
                            n_b = max(int(round(b * len(idx))), n_fin)
                            sel = select(scb, inst, n_b, quota(kind, sizes[bf], b, zb))
                            rows.append((t, Y, cl, rep, name, b, season(sel, vA, vB, n_fin, pool_B, pidx[t], FIELD_LAMBDA)))
            for t in TRUTHS:   # deterministic diagnostics (no bootstrap)
                elite = set(np.argsort(-np.nan_to_num(full[t], nan=-np.inf))[:n_final])
                for name, (fn, kind, _) in strat[t].items():
                    scv = fn()
                    for b in BUDGETS:
                        sel = select(scv, fam, max(int(round(b * N)), n_final), quota(kind, sizes, b, zfam[t][name]))
                        det.append(dict(truth=t, year=Y, cl=cl, strategy=name, budget=b,
                                        elite_kept=len(elite & set(sel)) / len(elite), fam_kept=len(np.unique(fam[sel])) / len(fam_codes),
                                        planted_merit=np.nanmean(full[t][sel]) - np.nanmean(full[t])))
            log(f'{Y} {cl}: {N} lines, {len(fam_codes)} families, {len(pe)} family-locations, {R} replicates')

    A = pd.DataFrame(rows, columns=['truth', 'year', 'cl', 'rep', 'strategy', 'budget', 'gain']); D = pd.DataFrame(det)
    A.to_parquet(f'{OUT}/allocation_reps.parquet'); D.to_csv(f'{OUT}/allocation_diag.csv', index=False)

    # ------------------------------------------------------------------ summary: average the 4 cluster-year sets per replicate
    prog = A.groupby(['truth', 'strategy', 'budget', 'rep']).gain.mean().reset_index()
    full_gain = prog[prog.budget == 1.0].groupby('truth').gain.mean()     # all strategies identical at b = 1
    summ = prog.groupby(['truth', 'strategy', 'budget']).gain.agg(mean='mean', sd='std', p10=lambda v: np.quantile(v, 0.10)).reset_index()
    summ['retained'] = summ['mean'] / summ.truth.map(full_gain)
    summ = summ.merge(D.groupby(['truth', 'strategy', 'budget'])[['elite_kept', 'fam_kept', 'planted_merit']].mean().reset_index())
    summ.to_csv(f'{OUT}/allocation_summary.csv', index=False)
    pd.set_option('display.width', 250)
    show = ['random', 'parent_history', 'markers_within', 'tilt0.25', 'tilt0.5', 'tilt1', 'tilt2',
            'kappa-1_cap', 'kappa+0_cap', 'kappa+1_cap', 'kappa-1', 'kappa+0', 'kappa+1']
    for t in TRUTHS:
        print(f'\n######## truth = {t} | full program (plant all, field-select top {FINAL:.0%}): {full_gain[t]:.2f} bu/ac ########')
        for b in BUDGETS[:-1]:
            x = summ[(summ.truth == t) & (summ.budget == b)].set_index('strategy').reindex(show)
            print(f'\n== budget {b:.0%} of plots ==')
            print(x[['mean', 'p10', 'sd', 'retained', 'elite_kept', 'fam_kept', 'planted_merit']].round(3).to_string())

    # ------------------------------------------------------------------ figures (gca truth: the advancement decision)
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    g = summ[summ.truth == 'gca']
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.8))
    for name, lab, ls in [('random', 'random', ':'), ('parent_history', 'parent history (traditional)', '--'),
                          ('markers_within', 'spread: markers within every family', '-'), ('tilt1', 'tilt toward predicted families (tau 1)', '-'),
                          ('kappa+0', 'concentrate on top predicted lines', '-.')]:
        x = g[g.strategy == name].sort_values('budget')
        ax[0].plot(x.budget * 100, x.retained * 100, ls, marker='o', label=lab)
    ax[0].axhline(100, color='grey', lw=.8); ax[0].set_xlabel('plots available (% of candidate lines)')
    ax[0].set_ylabel('realized gain (% of planting everything)'); ax[0].set_title('Gain vs plot budget (2006-07 validation)')
    ax[0].grid(alpha=.3); ax[0].legend(fontsize=8)
    for b, c in zip([0.10, 0.25, 0.50], ['C0', 'C1', 'C2']):
        x = g[(g.budget == b) & g.strategy.isin(['markers_within'] + [f'tilt{t:g}' for t in TAUS] + ['kappa+0_cap', 'kappa+0'])].copy()
        order = ['markers_within'] + [f'tilt{t:g}' for t in TAUS] + ['kappa+0_cap', 'kappa+0']
        x = x.set_index('strategy').loc[order].reset_index()
        ax[1].plot(x['sd'], x['mean'], marker='o', color=c, label=f'{b:.0%} plots')
        for _, r in x.iterrows():
            ax[1].annotate({'markers_within': 'spread', 'kappa+0_cap': 'cap', 'kappa+0': 'concentrate'}.get(r.strategy, r.strategy.replace('tilt', 'tau ')),
                           (r['sd'], r['mean']), fontsize=7, xytext=(3, 3), textcoords='offset points')
    ax[1].set_xlabel('risk: SD of realized gain across replicates (bu/ac)'); ax[1].set_ylabel('mean realized gain (bu/ac)')
    ax[1].set_title('Conservative (spread) -> aggressive (concentrate)'); ax[1].grid(alpha=.3); ax[1].legend(fontsize=8)
    plt.tight_layout(); plt.savefig(f'{FIG}/allocation_tradeoff.png', dpi=130)
    log('wrote allocation_summary.csv, allocation_reps.parquet, figs/allocation_tradeoff.png')


if __name__ == '__main__':
    main()

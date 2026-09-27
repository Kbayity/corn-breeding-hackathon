# phase2/step1d_fill.py
"""Apply the flanking-marker fill to every population, validate by masking, classify generation from raw heterozygosity, re-run the 25-pop probe."""
import os, time, numpy as np, pandas as pd
import common as C, impute as I

GEN_MAP = {'F2': 'F2', 'DH': 'DH', 'BC1': 'BC', 'BC1F2': 'BC1F2'}   # GEN_OBS (pop_generation_final.csv) -> impute.py gen code

ph = C.load_pheno(); t = C.pop_table(ph); mp_df = C.marker_map()   # t.GEN/RECURRENT are GEN_OBS/RECURRENT_final (see common.pop_table)
mp = {'chrom': mp_df.chrom.values, 'cM': mp_df.cM.values}
rng = np.random.default_rng(0)
md = ['\n## 1d Missing genotypes\n',
      'Provider imputed files: NA cells remain (12–14% overall, 32–39% at polymorphic markers). Phase-1 probes filled NA with the '
      'within-population marker mean (never across populations). This task replaces every NA with the conditional expectation given the '
      'nearest called flanking markers of the same individual (Haldane), falling back to the generation prior; monomorphic markers take the parent value.\n']
maskrows = []; genrows = []; stats = []
for cl in C.CLUSTERS:
    P = C.load_parents(cl); panel_sign = np.sign(np.nan_to_num(np.nanmean(P.values, 0))); panel_sign[panel_sign == 0] = 1
    mask_pops = set(rng.choice(t.index[t.CL == cl], 20, replace=False))
    mats, keys = [], []
    for pop in t.index[t.CL == cl]:
        r = t.loc[pop]
        par, prog = C.load_imputed_pop(cl, pop)
        A_id = r.RECURRENT if pd.notna(r.RECURRENT) else r.P1   # RECURRENT is RECURRENT_final (reversed BCs already swapped)
        B_id = r.P2 if A_id == r.P1 else r.P1
        assert A_id in par.index and B_id in par.index, (pop, A_id, B_id, list(par.index))
        parA, fa, pa = I.fill_parent(par.loc[A_id].values.astype(float), mp, panel_sign)
        parB, fb, pb = I.fill_parent(par.loc[B_id].values.astype(float), mp, panel_sign)
        gen = GEN_MAP.get(r.GEN, 'F2')
        V = prog.values.astype(float)
        if pop in mask_pops:
            poly = parA != parB; cells = np.argwhere(~np.isnan(V) & poly[None, :])
            sel = cells[rng.choice(len(cells), min(2000, len(cells)), replace=False)]
            Vm = V.copy(); true = V[sel[:, 0], sel[:, 1]]; Vm[sel[:, 0], sel[:, 1]] = np.nan
            filled = I.fill_population(Vm, parA, parB, gen, mp)
            pred = filled[sel[:, 0], sel[:, 1]]
            popmean = np.nan_to_num(np.nanmean(Vm, 0))[sel[:, 1]]
            maskrows.append(dict(CL=cl, POP=pop, GEN=r.GEN, n=len(sel), mae_flank=np.abs(pred - true).mean(),
                                 mae_popmean=np.abs(popmean - true).mean(), mae_prior=np.abs(0 - true).mean(),
                                 acc_round_flank=(np.round(pred) == true).mean(), acc_round_popmean=(np.round(popmean) == true).mean()))
        t0 = time.time(); filled = I.fill_population(V, parA, parB, gen, mp)
        stats.append(dict(CL=cl, POP=pop, n=len(V), na_before=np.isnan(V).mean(), par_na_flank=fa + fb, par_na_panel=pa + pb, sec=time.time() - t0))
        mats.append(filled); keys += list(prog.index)
    X = np.vstack(mats).astype(np.float32); assert not np.isnan(X).any()
    np.save(os.path.join(C.CACHE, f'filled_{cl}_X.npy'), X); pd.to_pickle(keys, os.path.join(C.CACHE, f'filled_{cl}_keys.pkl'))
    print(cl, 'filled', X.shape)
print('FALLBACK_COUNTS (cells with infeasible flanking calls under the assumed generation model):', I.FALLBACK_COUNTS)
md.append(f'Infeasible-flank fallback cells (impute.FALLBACK_COUNTS, across all fills incl. the mask-check): {I.FALLBACK_COUNTS}.\n')

# generation classification from RAW heterozygosity at polymorphic markers (raw file, ~69 calls per line)
for cl in C.CLUSTERS:
    f = os.path.join(C.DATA, f'Unimputed_{cl}_Genome_Data', f'{cl}_Genome_Data.csv')
    raw = pd.read_csv(f, dtype=str, na_values=['NA'], low_memory=False)
    mk = list(raw.columns[4:]); raw = raw[raw.LINE.notna()]
    P = C.load_parents(cl)
    for pop, g in raw.groupby('shorthand'):
        r = t.loc[pop]; pa, pb = P.loc[r.P1].values, P.loc[r.P2].values
        poly = (pa != pb) & ~np.isnan(pa) & ~np.isnan(pb)
        prog = g[~g.LINE.str.startswith('PID')][mk].apply(pd.to_numeric, errors='coerce').values[:, poly]
        called = ~np.isnan(prog); het = (prog == 0).sum() / max(called.sum(), 1)
        genrows.append(dict(CL=cl, POP=pop, GEN=r.GEN, YEAR=r.YEAR, het_poly=het, n_called=int(called.sum())))
gen = pd.DataFrame(genrows)
gen['expected_het'] = gen.GEN.map({'F2': 0.5, 'BC': 0.5, 'DH': 0.0, 'DH2': 0.0})
gen['GEN_OBS'] = np.where((gen.GEN == 'BC') & (gen.het_poly < 0.375), 'BC1F2?',
                 np.where(gen.GEN.isin(['DH', 'DH2']) & (gen.het_poly > 0.1), 'not-DH?',
                 np.where((gen.GEN == 'F2') & (gen.het_poly < 0.375), 'F2-selfed?', gen.GEN)))
gen.to_csv(os.path.join(C.OUT, 'pop_generation_obs.csv'), index=False)
md.append('Observed heterozygosity at polymorphic markers (raw calls) by declared generation:\n')
md.append(gen.groupby('GEN').het_poly.describe()[['count', 'mean', '25%', '50%', '75%']].round(3).to_markdown() + '\n')
md.append(f'Populations flagged (GEN_OBS): {gen.GEN_OBS.value_counts().to_dict()}. BC populations with het < 0.375 are BC1F2 candidates; the BC1 fill model was still used for them (approximation, flagged).\n')
mk_ = pd.DataFrame(maskrows); mk_.to_csv(os.path.join(C.OUT, 'step1d_maskcheck.csv'), index=False)
md.append('Mask check (2,000 called polymorphic cells hidden per population, 20 populations per cluster):\n')
md.append(mk_.groupby(['CL', 'GEN'])[['mae_flank', 'mae_popmean', 'mae_prior', 'acc_round_flank', 'acc_round_popmean']].mean().round(3).to_markdown() + '\n')
st = pd.DataFrame(stats); md.append(f'Fill statistics: mean NA before {st.na_before.mean():.3f}; parent NA cells filled from flank {st.par_na_flank.sum()}, from panel sign {st.par_na_panel.sum()}; total fill time {st.sec.sum() / 60:.1f} min.\n')

# ---- re-run the 25-population probe with the filled matrix (same populations and folds as phase-1 06_withinpop_gp.py) ----
lm = C.line_means(ph, 'YLD_BE', 'ENV')
h2 = pd.read_csv(os.path.join(C.OUT, 'within_pop_H.csv')).set_index('pop')
Xf, kf = C.geno_matrix('C1', 'filled'); kidx = pd.Series(np.arange(len(kf)), index=kf)
Xi, ki = C.geno_matrix('C1', 'imputed'); kidx_i = pd.Series(np.arange(len(ki)), index=ki)
rng2 = np.random.default_rng(1)
pops = ph[(ph.CL == 'C1') & ph.YEAR.between(2004, 2007)].POP.unique(); pops = rng2.choice(pops, 25, replace=False)
res = []
for pop in pops:
    j = lm[lm.POP == pop]; j = j[j.index.isin(kidx.index)]
    if len(j) < 60:
        continue
    y = j.y.values; folds = rng2.permutation(len(j)) % 5
    for name, (Xm, ki_) in [('filled', (Xf, kidx)), ('popmean_fill', (Xi, kidx_i))]:
        X = np.array(Xm[ki_[j.index].values], float)
        if name == 'popmean_fill':
            X = np.where(np.isnan(X), np.nanmean(X, 0)[None, :], X); X = np.nan_to_num(X)
        X = X[:, X.std(0) > 0]; X = X - X.mean(0); K = X @ X.T / X.shape[1]; lam = (1 - 0.3) / 0.3; pred = np.zeros(len(y))
        for f in range(5):
            tr = folds != f; te = ~tr; mu = y[tr].mean()
            a = np.linalg.solve(K[np.ix_(tr, tr)] + lam * np.eye(tr.sum()), y[tr] - mu); pred[te] = mu + K[np.ix_(te, tr)] @ a
        res.append(dict(pop=pop, fill=name, n=len(y), acc=np.corrcoef(pred, y)[0, 1], H=h2.H.get(pop, np.nan)))
r = pd.DataFrame(res); r.to_csv(os.path.join(C.OUT, 'step1d_probe.csv'), index=False)
piv = r.pivot(index='pop', columns='fill', values='acc')
md.append(f'25-population within-pop GBLUP probe (5-fold CV, corr with line mean): median filled {piv.filled.median():.3f} vs population-mean fill {piv.popmean_fill.median():.3f}; '
          f'mean {piv.filled.mean():.3f} vs {piv.popmean_fill.mean():.3f}; populations where filled >= popmean fill: {(piv.filled >= piv.popmean_fill).sum()} of {len(piv)}.\n')
open(os.path.join(C.OUT, 'checks.md'), 'a').write('\n'.join(md))

def selfcheck():
    for cl in C.CLUSTERS:
        X, k = C.geno_matrix(cl, 'filled'); assert X.shape[1] == 2911 and len(k) == X.shape[0] and not np.isnan(np.asarray(X[:1000])).any()
    assert mk_.mae_flank.mean() < mk_.mae_popmean.mean()
    assert piv.filled.median() > piv.popmean_fill.median() - 0.03
selfcheck()

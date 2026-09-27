# phase2/step1_checks.py
"""Steps 1a, 1b, 1c and 3 of the phase-2 spec. Writes outputs/checks.md (later tasks append)."""
import os, numpy as np, pandas as pd
import common as C

ph = C.load_pheno(); t = C.pop_table(ph)
md = ['# Correctness checks (phase 2)\n']

# ---- 1a: parent rows identical across imputed files ----
rows = []
for cl in C.CLUSTERS:
    seen = {}
    for pop in t.index[t.CL == cl]:
        par, _ = C.load_imputed_pop(cl, pop)
        for pid, row in par.iterrows():
            v = row.values
            if pid in seen:
                ref, refpop = seen[pid]
                both = ~np.isnan(ref) & ~np.isnan(v)
                rows.append(dict(CL=cl, pid=pid, pop_a=refpop, pop_b=pop, compared=int(both.sum()),
                                 mismatch=int((ref[both] != v[both]).sum()),
                                 na_only_a=int((np.isnan(v) & ~np.isnan(ref)).sum()),
                                 na_only_b=int((np.isnan(ref) & ~np.isnan(v)).sum())))
            else:
                seen[pid] = (v, pop)
a = pd.DataFrame(rows)
md.append('## 1a Allele coding consistency of parents across imputed files\n')
md.append(f'Parent-row pairs compared: {len(a)}; pairs with any mismatch at jointly-called markers: {(a.mismatch > 0).sum()}; '
          f'total mismatching cells: {a.mismatch.sum()} of {a.compared.sum()} compared. '
          f'Cells called in one file but NA in the other: {a.na_only_a.sum() + a.na_only_b.sum()}.\n')
if (a.mismatch > 0).any():
    md.append(a[a.mismatch > 0].head(30).to_markdown(index=False) + '\n')
for cl in C.CLUSTERS:
    P = C.load_parents(cl); mism = 0; comp = 0
    for pop in t.index[t.CL == cl][:60]:
        par, _ = C.load_imputed_pop(cl, pop)
        for pid, row in par.iterrows():
            if pid in P.index:
                r = P.loc[pid].values; v = row.values; both = ~np.isnan(r) & ~np.isnan(v)
                comp += both.sum(); mism += (r[both] != v[both]).sum()
    md.append(f'{cl}: imputed-file parent rows vs raw-file parent rows (first 60 populations): {mism} mismatches of {comp} compared cells.\n')

# ---- 1b: testers ----
tp = ph.groupby('POP').TESTER.nunique(); tpl = ph.groupby(['POP', 'LOC']).TESTER.nunique()
md.append('## 1b Testers\n')
md.append(f'Distinct testers per population: {tp.value_counts().sort_index().to_dict()} (TESTER="NA" counts as one level). '
          f'Populations with TESTER = NA: {(t.TESTER == "NA").sum()}. Distinct testers per population×location: {tpl.value_counts().sort_index().to_dict()}.\n')
exc = tp[tp > 1]
md.append(('Exceptions: ' + ', '.join(exc.index) + '\n') if len(exc) else 'One tester per population confirmed for all 999 populations.\n')

# ---- 1c: reconciliations ----
md.append('## 1c Reconciliations\n')
cr = ph[['POP', 'P1', 'P2']].drop_duplicates('POP')
allp = pd.concat([cr.P1, cr.P2]); n_unique = allp.nunique()
geno = {cl: set(C.load_parents(cl).index) for cl in C.CLUSTERS}
per_cl = {cl: set(pd.concat([cr[cr.POP.str.startswith(cl)].P1, cr[cr.POP.str.startswith(cl)].P2])) for cl in C.CLUSTERS}
md.append(f'Unique parent IDs after stripping the `*2` suffix: {n_unique} (C1 {len(per_cl["C1"])}, C2 {len(per_cl["C2"])}, shared {len(per_cl["C1"] & per_cl["C2"])}). '
          f'Genotyped parents: C1 {len(geno["C1"])}, C2 {len(geno["C2"])}. Phenotype parents lacking a genotype: C1 {len(per_cl["C1"] - geno["C1"])}, C2 {len(per_cl["C2"] - geno["C2"])}. '
          f'The briefing figure of 586 counted `A*2` and `A` as different parents.\n')
d08 = ph[ph.YEAR == 2008]
md.append(f'2008 design rows: {len(d08)} plots, {d08.LINE_ID.nunique()} lines, {d08.POP.nunique()} populations, {d08.LOC.nunique()} locations. '
          f'Plots per line in 2008: mean {len(d08) / d08.LINE_ID.nunique():.2f}, median {d08.groupby("LINE_ID").size().median():.0f}. '
          f'Locations per population in 2008: median {d08.groupby("POP").LOC.nunique().median():.0f} vs all years {ph.groupby("POP").LOC.nunique().median():.0f}. '
          f'(Trait values for 2008 are NaN and were not read.)\n')
byyr = ph.groupby('YEAR').agg(plots=('LINE_ID', 'size'), lines=('LINE_ID', 'nunique'))
byyr['plots_per_line'] = byyr.plots / byyr.lines
byyr['locs_per_pop_median'] = ph.groupby(['YEAR', 'POP']).LOC.nunique().groupby('YEAR').median()
md.append(byyr.round(2).to_markdown() + '\n')
for cl in C.CLUSTERS:
    _, keys = C.geno_matrix(cl, 'imputed'); ks = set(keys)
    lines = ph.loc[ph.CL == cl].drop_duplicates('LINE_ID')
    lines = lines.assign(g=lines.LINE_ID.isin(ks))
    md.append(f'{cl} phenotype-to-genotype link rate: {lines.g.mean():.4f} ({lines.g.sum()} of {len(lines)} lines); genotyped lines without phenotype: {len(ks - set(lines.LINE_ID))}.\n')
    md.append(lines.groupby('YEAR').g.agg(['mean', 'sum', 'size']).round(3).to_markdown() + '\n')
    zero = lines.groupby('POP').g.mean(); md.append(f'{cl} populations with zero linked lines: {list(zero[zero == 0].index)}\n')

# ---- 3: clean variance components using multi-population SETs ----
md.append('## 3 Variance components using only SETs with 2+ populations\n')
y = ph.dropna(subset=['YLD_BE'])
pops_per_set = y.groupby('SET').POP.nunique(); multi = set(pops_per_set[pops_per_set >= 2].index)
ym = y[y.SET.isin(multi)]
cell = ym.groupby(['TRIAL', 'POP']).YLD_BE.agg(['mean', 'size']).reset_index()
cell = cell[cell['size'] >= 20]
cell['dev'] = cell['mean'] - cell.groupby('TRIAL')['mean'].transform('mean')
h2 = C.pop_h2(ph, 'YLD_BE')
noise = (ym.groupby(['TRIAL', 'POP']).YLD_BE.var().mean()) / cell['size'].mean()
trials = cell.groupby('TRIAL').filter(lambda g: len(g) >= 2)
v_between = trials.groupby('TRIAL').dev.var().mean() - noise
pops = trials.POP.unique()
v_within = h2.loc[h2.index.isin(pops), 'vL'].median()
# -- A: covariance-between-locations estimator, isolates the population main effect --
trial_info = ym[['TRIAL', 'SET', 'LOC']].drop_duplicates('TRIAL')
cellset = cell.merge(trial_info, on='TRIAL', how='left')
covs = []; sets_used = set(); pops_main = set()
for set_id, g in cellset.groupby('SET'):
    piv = g.pivot_table(index='POP', columns='LOC', values='dev')
    locs = list(piv.columns)
    for i in range(len(locs)):
        for j in range(i + 1, len(locs)):
            pair = piv[[locs[i], locs[j]]].dropna()
            if len(pair) >= 2:
                covs.append(np.cov(pair[locs[i]], pair[locs[j]], ddof=1)[0, 1])
                sets_used.add(set_id); pops_main |= set(pair.index)
n_pairs = len(covs); n_sets = len(sets_used)
var_pop_main = float(np.mean(covs))
v_within_main = h2.loc[h2.index.isin(pops_main), 'vL'].median()
ratio_main = var_pop_main / v_within_main

res = [dict(estimate='covariance between locations, multi-pop SETs (pop main only)',
            n_trials=np.nan, n_sets=n_sets, n_pairs=n_pairs, n_pops=len(pops_main),
            var_between_pop=var_pop_main, var_within_pop_genetic_median=v_within_main, ratio=ratio_main)]
res.append(dict(estimate='within-trial, multi-pop SETs (pop main + pop×location)',
                n_trials=trials.TRIAL.nunique(), n_sets=np.nan, n_pairs=np.nan, n_pops=len(pops),
                var_between_pop=v_between, var_within_pop_genetic_median=v_within, ratio=v_between / v_within))

# -- B: "all SETs" estimate, restricted to location-years with 2+ populations --
env_pop_counts = y.groupby('ENV').POP.nunique(); qual_envs = set(env_pop_counts[env_pop_counts >= 2].index)
d = y[y.ENV.isin(qual_envs)]
env_mean = d.groupby('ENV').YLD_BE.mean()
cell_all = d.groupby(['POP', 'ENV']).YLD_BE.agg(['mean', 'size']).reset_index()
cell_all['dev'] = cell_all['mean'] - cell_all['ENV'].map(env_mean)
pm2 = cell_all.groupby('POP').agg(dev=('dev', 'mean'), n_cells=('dev', 'size'), n_plots=('size', 'sum'))
pm2 = pm2[pm2.n_cells >= 2]
noise_all = (d.groupby(['POP', 'ENV']).YLD_BE.var().mean()) / d.groupby(['POP', 'ENV']).size().mean()
v_between_all = pm2.dev.var() - noise_all / pm2.n_cells.mean()
res.append(dict(estimate='ENV-adjusted, location-years with 2+ pops (confounded with experiment)',
                n_trials=d.TRIAL.nunique(), n_sets=np.nan, n_pairs=np.nan, n_pops=len(pm2),
                var_between_pop=v_between_all, var_within_pop_genetic_median=h2.vL.median(), ratio=v_between_all / h2.vL.median()))

r = pd.DataFrame(res); r.to_csv(os.path.join(C.OUT, 'step3_variance.csv'), index=False)
md.append(r.round(2).to_markdown(index=False) + '\n')
md.append(f'Number of SETs with 2+ populations: {len(multi)}; plots in them: {len(ym)} of {len(y)}. '
          f'Covariance-between-locations pairs used: {n_pairs} across {n_sets} SETs.\n')
close6 = abs(ratio_main - 6) < 2
md.append(f'The "covariance between locations" row is the clean population main-effect variance, free of '
          f'population×location interaction and cell noise; it is the row to read for population-mean vs. '
          f'within-population comparisons. Its ratio of {ratio_main:.2f} is '
          f'{"consistent with" if close6 else "notably different from"} phase-1\'s approximate 6x figure '
          f'(BRIEFING.md: between-pop variance ≈166 vs. within-pop genetic variance ≈27).\n')
open(os.path.join(C.OUT, 'checks.md'), 'w').write('\n'.join(md))

def selfcheck():
    assert len(exc) < 5
    assert n_unique < 586
    assert len(multi) >= 100
    assert n_pairs >= 100 and var_pop_main > 0
    assert os.path.getsize(os.path.join(C.OUT, 'checks.md')) > 2000
selfcheck()

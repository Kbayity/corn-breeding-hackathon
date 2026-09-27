# phase2/step2_generation.py
"""Empirical check of generation-aware expectations: BC mean weights (0.75/0.25) and within-family variance ratios (BC ~0.5x F2, DH ~2x F2)."""
import os, numpy as np, pandas as pd
from scipy import sparse
from scipy.sparse.linalg import lsqr
import common as C
from step1e_parents import parent_groups

ph = C.load_pheno(); t = C.pop_table(ph); pm = C.pop_means(ph, 'YLD_BE'); h2 = C.pop_h2(ph, 'YLD_BE')
md = ['# Step 2: generation-aware expectations (2000–2007 populations)\n']
d = h2.join(t[['GEN', 'CL']]); rng = np.random.default_rng(0)
rows = []
f2 = d.loc[d.GEN == 'F2', 'vL'].values
for gen in ['F2', 'BC', 'DH', 'DH2']:
    v = d.loc[d.GEN == gen, 'vL'].values
    ratios = [np.median(rng.choice(v, len(v))) / np.median(rng.choice(f2, len(f2))) for _ in range(1000)]
    rows.append(dict(GEN=gen, n_pops=len(v), median_vL=np.median(v), ratio_to_F2=np.median(v) / np.median(f2),
                     ci_lo=np.percentile(ratios, 2.5), ci_hi=np.percentile(ratios, 97.5), expected_ratio={'F2': 1, 'BC': 0.5, 'DH': 2, 'DH2': 2}[gen]))
r = pd.DataFrame(rows); md.append('## Within-family genetic variance of yield by generation\n'); md.append(r.round(3).to_markdown(index=False) + '\n')
rows = []
for cl in C.CLUSTERS:
    gp = parent_groups(cl); tc = t[(t.CL == cl) & (t.YEAR < 2008)].copy(); tc['G1'] = tc.P1.map(gp); tc['G2'] = tc.P2.map(gp)
    tc = tc.join(pm.dev).dropna(subset=['dev'])
    tr = tc[tc.GEN != 'BC']; groups = sorted(set(tr.G1) | set(tr.G2)); gi = {g: i for i, g in enumerate(groups)}
    R = np.arange(len(tr))
    X = sparse.csr_matrix((np.r_[np.full(len(tr), 0.5), np.full(len(tr), 0.5)], (np.r_[R, R], [gi[g] for g in tr.G1] + [gi[g] for g in tr.G2])), shape=(len(tr), len(groups)))
    lam = 2.0; A = sparse.vstack([X, sparse.diags(np.full(len(groups), np.sqrt(lam)))]); b = np.r_[tr.dev.values - tr.dev.mean(), np.zeros(len(groups))]
    gca = pd.Series(lsqr(A, b)[0], index=groups)
    bc = tc[(tc.GEN == 'BC') & tc.RECURRENT.notna()].copy()
    bc['G_rec'] = np.where(bc.RECURRENT == bc.P1, bc.G1, bc.G2); bc['G_don'] = np.where(bc.RECURRENT == bc.P1, bc.G2, bc.G1)
    bc = bc[bc.G_rec.isin(gca.index) & bc.G_don.isin(gca.index)]
    if len(bc) >= 10:
        Xb = np.c_[np.ones(len(bc)), gca[bc.G_rec].values, gca[bc.G_don].values]; yb = bc.dev.values
        beta = np.linalg.lstsq(Xb, yb, rcond=None)[0]
        boots = np.array([np.linalg.lstsq(Xb[i], yb[i], rcond=None)[0] for i in (rng.integers(0, len(bc), len(bc)) for _ in range(1000))])
        rows.append(dict(CL=cl, n_BC=len(bc), coef_recurrent=beta[1], rec_lo=np.percentile(boots[:, 1], 2.5), rec_hi=np.percentile(boots[:, 1], 97.5),
                         coef_donor=beta[2], don_lo=np.percentile(boots[:, 2], 2.5), don_hi=np.percentile(boots[:, 2], 97.5), expected='0.75 vs 0.25 (ratio 3:1)'))
r2 = pd.DataFrame(rows); md.append('## BC population mean as a function of parent-group GCA estimated from F2/DH populations\n'); md.append(r2.round(3).to_markdown(index=False) + '\n')
md.append('Coefficients are attenuated by GCA estimation error; the diagnostic is the recurrent:donor ratio, expected 3:1.\n')
open(os.path.join(C.OUT, 'step2_generation.md'), 'w').write('\n'.join(md))

def selfcheck():
    assert set(r.GEN) == {'F2', 'BC', 'DH', 'DH2'} and r.n_pops.sum() > 800
    assert len(r2) == 2
selfcheck()

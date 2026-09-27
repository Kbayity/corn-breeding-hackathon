# phase2/step10_generation.py
"""Classify each population's true generation from A-dosage class shares in the imputed genotype file
(a data-driven check on the declared GENERATION_NAME), and detect reversed backcrosses (donor and recurrent
parent swapped). Writes outputs/pop_generation_final.csv, consumed by common.pop_table."""
import os
import numpy as np, pandas as pd
import common as C

# expected (A_hom, het, B_hom) share vectors; A = declared recurrent for BC else P1 (see common.pop_table)
EXPECTED = {'F2': (0.25, 0.5, 0.25), 'BC1': (0.5, 0.5, 0.0), 'BC1F2': (0.625, 0.25, 0.125), 'DH': (0.5, 0.0, 0.5)}


def dosage_shares(cl, pop, A_id, B_id):
    """A-dosage class shares (A_hom, het, B_hom) at polymorphic, called cells of the imputed provider file.
    A-dosage d = 1 + g*pA (g = progeny file value, pA = parent A's file value); classes: d==2 A_hom, d==1 het, d==0 B_hom."""
    par, prog = C.load_imputed_pop(cl, pop)
    pA = par.loc[A_id].values.astype(float); pB = par.loc[B_id].values.astype(float)
    poly = (pA != pB) & ~np.isnan(pA) & ~np.isnan(pB)
    pA = pA[poly]
    V = prog.values[:, poly]
    called = ~np.isnan(V)
    n = int(called.sum())
    if n == 0:
        return np.nan, np.nan, np.nan, 0
    d = 1.0 + V * pA[None, :]
    A_hom = float(((d == 2) & called).sum() / n)
    het = float(((d == 1) & called).sum() / n)
    B_hom = float(((d == 0) & called).sum() / n)
    return A_hom, het, B_hom, n


_MIRROR = {'BC1_mirror': ('BC1', (0.0, 0.5, 0.5)), 'BC1F2_mirror': ('BC1F2', (0.125, 0.25, 0.625))}


def classify(A_hom, het, B_hom):
    """Nearest expected share vector by Euclidean distance. BC1/BC1F2 are asymmetric in (A_hom, B_hom), so their
    mirror (A and B swapped) is also a candidate: a reversed backcross -- where the declared-recurrent parent A
    is genotypically the donor -- still lands on its true class this way, rather than nearest F2 by default."""
    v = np.array([A_hom, het, B_hom])
    cand = dict(EXPECTED, **{k: m[1] for k, m in _MIRROR.items()})
    best = min(cand, key=lambda k: float(np.sum((v - np.array(cand[k])) ** 2)))
    return _MIRROR[best][0] if best in _MIRROR else best


def resolve_recurrent(gen_obs, A_hom, B_hom, A_id, B_id):
    """A reversed backcross has the donor, not the recurrent, showing the higher homozygosity share."""
    reversed_ = gen_obs in ('BC1', 'BC1F2') and B_hom > A_hom
    return (B_id if reversed_ else A_id), reversed_


def run():
    # Sourced from GEN_declared/RECURRENT_declared (the original cross-string data), never from a GEN_OBS/
    # RECURRENT_final left over by an earlier run of this script, so this stays idempotent.
    ph = C.load_pheno(); t = C.pop_table(ph)
    rows = []
    for pop, r in t.iterrows():
        A_id = r.RECURRENT_declared if (r.GEN_declared == 'BC' and pd.notna(r.RECURRENT_declared)) else r.P1
        B_id = r.P2 if A_id == r.P1 else r.P1
        try:
            A_hom, het, B_hom, n = dosage_shares(r.CL, pop, A_id, B_id)
        except Exception:
            A_hom = het = B_hom = np.nan; n = 0
        if n == 0:
            gen_obs = r.GEN_declared if r.GEN_declared in EXPECTED else 'F2'
            recurrent_final, reversed_ = A_id, False
        else:
            gen_obs = classify(A_hom, het, B_hom)
            recurrent_final, reversed_ = resolve_recurrent(gen_obs, A_hom, B_hom, A_id, B_id)
        w_rec = 0.75 if gen_obs in ('BC1', 'BC1F2') else 0.5
        W1, W2 = (w_rec, 1 - w_rec) if recurrent_final == r.P1 else (1 - w_rec, w_rec)
        rows.append(dict(POP=pop, GEN_declared=r.GEN_declared, GEN_OBS=gen_obs, A_hom=A_hom, het=het, B_hom=B_hom,
                         RECURRENT_final=recurrent_final, W1=W1, W2=W2, flag='reversed' if reversed_ else ''))
    out = pd.DataFrame(rows).set_index('POP')
    out.to_csv(os.path.join(C.OUT, 'pop_generation_final.csv'))
    return out, t


def write_md(out, t):
    md = ['\n## 10 Generation classification from A-dosage class shares\n',
          'GEN_OBS classifies each population by nearest Euclidean distance among the expected (A_hom, het, B_hom) '
          f'share vectors {EXPECTED}, computed from the imputed provider file (polymorphic, called cells only; '
          'A = declared recurrent for BC else P1). A reversed backcross (B_hom > A_hom under GEN_OBS in {BC1, BC1F2}) '
          'swaps the recurrent parent in RECURRENT_final.\n']
    conf = pd.crosstab(out.GEN_declared, out.GEN_OBS)
    md.append('Confusion table (rows: declared GEN, columns: GEN_OBS):\n\n' + conf.to_markdown() + '\n')
    rev = out[out.flag == 'reversed']
    md.append(f'Reversed backcross populations ({len(rev)}): {list(rev.index)}\n')
    pop2008 = set(t.index[t.YEAR == 2008])
    changed2008 = out[(out.index.isin(pop2008)) & (out.GEN_OBS != out.GEN_declared)]
    md.append(f'2008 populations with GEN_OBS != GEN_declared ({len(changed2008)}): {list(changed2008.index)}\n')
    open(os.path.join(C.OUT, 'step10_generation.md'), 'w').write('\n'.join(md))


def selfcheck():
    assert os.path.exists(os.path.join(C.OUT, 'pop_generation_final.csv'))
    o = pd.read_csv(os.path.join(C.OUT, 'pop_generation_final.csv'))
    assert set(o.GEN_OBS) <= set(EXPECTED)
    assert np.allclose(o.W1 + o.W2, 1)


if __name__ == '__main__':
    out, t = run()
    write_md(out, t)
    selfcheck()
    print('wrote', len(out), 'populations;', (out.flag == 'reversed').sum(), 'reversed')

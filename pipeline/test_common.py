# phase2/test_common.py
import numpy as np, pandas as pd
import common as C

def test_norm_num():
    assert C.norm_num('00000000163') == '163'
    assert C.norm_num('000000325#1') == '325#1'
    assert C.norm_num('10.1') == '10.1'
    assert C.norm_num('191') == '191'

def test_pheno_quarantine_and_ids():
    ph = C.load_pheno()
    assert len(ph) == 1072276
    assert ph.loc[ph.YEAR == 2008, C.ALL_TRAITS].notna().sum().sum() == 0
    assert ph.loc[ph.YEAR < 2008, 'YLD_BE'].notna().sum() > 900000
    assert ph.LINE_ID.nunique() == 154033  # 154700 raw (POP,LINE) pairs minus 667 C1 zero-pad dupes norm_num correctly merges
    assert ph.groupby('POP').YEAR.nunique().max() == 1
    assert ph.groupby('POP').TESTER.nunique().max() == 1
    assert (ph.LINE_ID.str.endswith('.0') & (ph.CL == 'C2')).sum() == 0

def test_pop_table_weights():
    # requires outputs/pop_generation_final.csv (step10_generation.py) to already exist: pop_table overrides
    # GEN/RECURRENT/W1/W2 from it, keeping the originally-declared generation in GEN_declared.
    ph = C.load_pheno(); t = C.pop_table(ph)
    assert len(t) == 999
    assert np.allclose(t.W1 + t.W2, 1)
    assert 'GEN_declared' in t.columns
    bc = t[t.GEN.isin(['BC1', 'BC1F2'])]
    assert len(bc) > 0
    assert set(bc.W1.round(2)) <= {0.75, 0.25}
    assert (t.loc[~t.GEN.isin(['BC1', 'BC1F2']), 'W1'] == 0.5).all()

def test_line_and_pop_means():
    ph = C.load_pheno()
    lm = C.line_means(ph, 'YLD_BE')
    assert lm.YEAR.max() == 2007
    assert abs(lm.y.mean()) < 0.5
    pm = C.pop_means(ph, 'YLD_BE')
    # 157 pops quarantined (YEAR==2008) + 2 pops (C2.147, C2.31) with zero non-null YLD_BE in any year
    assert pm.YEAR.max() == 2007 and len(pm) == 840

def test_geno_link():
    par, prog = C.load_imputed_pop('C1', 'C1.1')
    assert par.shape == (2, 2911) and prog.shape[1] == 2911
    ph = C.load_pheno()
    ids = set(ph.loc[ph.POP == 'C1.1', 'LINE_ID'])
    assert len(ids & set(prog.index)) / len(ids) > 0.99
    m = C.marker_map(); assert len(m) == 2911 and m.chrom.nunique() == 10

def test_boot_corr():
    r = C.boot_corr(np.arange(50.0), np.arange(50.0) + np.random.default_rng(1).normal(size=50))
    assert 0.9 < r['pearson'] < 1 and r['p_lo'] <= r['pearson'] <= r['p_hi'] and r['n'] == 50

def test_boot_corr_constant():
    pred = np.full(30, 3.0)
    obs = np.random.default_rng(2).normal(size=30)
    r = C.boot_corr(pred, obs)
    assert r['n'] == 30
    assert np.isnan(r['pearson']) and np.isnan(r['spearman'])
    assert np.isnan(r['p_lo']) and np.isnan(r['p_hi']) and np.isnan(r['s_lo']) and np.isnan(r['s_hi'])

if __name__ == '__main__':
    for f in [test_norm_num, test_pheno_quarantine_and_ids, test_pop_table_weights, test_line_and_pop_means, test_geno_link, test_boot_corr, test_boot_corr_constant]:
        f(); print('ok', f.__name__)

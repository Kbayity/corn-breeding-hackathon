# phase2/test_impute.py
import numpy as np
import impute as I

def test_haldane():
    assert abs(I.haldane(0) - 0) < 1e-12 and abs(I.haldane(1e9) - 0.5) < 1e-9
    assert abs(I.haldane(10) - 0.5 * (1 - np.exp(-0.2))) < 1e-12

def test_expected_dosage_limits():
    for gen in ['F2', 'DH', 'BC', 'DH2']:
        for gL in ([0, 2] if gen in ('DH', 'DH2') else ([1, 2] if gen == 'BC' else [0, 1, 2])):
            e = I.expected_dosage(np.array([gL]), np.array([gL]), np.array([1e-6]), np.array([1e-6]), gen)
            assert abs(e[0] - gL) < 1e-3, (gen, gL, e)
    e = I.expected_dosage(np.array([-1]), np.array([-1]), np.array([0.3]), np.array([0.3]), 'F2'); assert abs(e[0] - 1) < 1e-9
    e = I.expected_dosage(np.array([-1]), np.array([-1]), np.array([0.3]), np.array([0.3]), 'BC'); assert abs(e[0] - 1.5) < 1e-9
    e = I.expected_dosage(np.array([-1]), np.array([-1]), np.array([0.3]), np.array([0.3]), 'DH'); assert abs(e[0] - 1) < 1e-9
    e = I.expected_dosage(np.array([2]), np.array([-1]), np.array([0.1]), np.array([0.5]), 'F2'); assert abs(e[0] - 1.8) < 1e-9
    e = I.expected_dosage(np.array([1]), np.array([1]), np.array([0.1]), np.array([0.1]), 'F2'); assert abs(e[0] - 1) < 1e-9
    e = I.expected_dosage(np.array([2]), np.array([0]), np.array([0.1]), np.array([0.1]), 'F2'); assert abs(e[0] - 1) < 1e-9
    e = I.expected_dosage(np.array([2]), np.array([-1]), np.array([0.1]), np.array([0.5]), 'DH2'); assert abs(e[0] - 1.72) < 1e-9

def test_bc1f2_uses_f2_enumeration():
    gL, gR, rL, rR = np.array([2., 1., 0.]), np.array([0., 1., -1.]), np.array([0.1, 0.2, 0.3]), np.array([0.1, 0.2, 0.5])
    e_bc1f2 = I.expected_dosage(gL, gR, rL, rR, 'BC1F2')
    e_f2 = I.expected_dosage(gL, gR, rL, rR, 'F2')
    assert np.allclose(e_bc1f2, e_f2)

def test_expected_dosage_infeasible_flank_fallback():
    # gL=1 (het) is impossible for DH (dosage in {0,2}); falls back to dropping the left flank -> one-sided right result.
    e = I.expected_dosage(np.array([1.]), np.array([2.]), np.array([0.1]), np.array([0.1]), 'DH')
    assert np.isfinite(e[0]) and abs(e[0] - 2 * (1 - 0.1)) < 1e-9
    # both flanks infeasible for DH -> falls back all the way to the generation prior.
    e = I.expected_dosage(np.array([1.]), np.array([1.]), np.array([0.1]), np.array([0.1]), 'DH')
    assert np.isfinite(e[0]) and abs(e[0] - 1.0) < 1e-9

def test_fill_population_small():
    mp = {'chrom': np.array([1, 1, 1, 2, 2]), 'cM': np.array([0., 10., 20., 0., 50.])}
    parA = np.array([1, 1, 1, 1, -1.]); parB = np.array([-1, -1, 1, -1, -1.])   # markers 3 and 5 monomorphic
    prog = np.array([[1, np.nan, 1, np.nan, np.nan],
                     [-1, np.nan, np.nan, -1, np.nan]])
    out = I.fill_population(prog.copy(), parA, parB, 'F2', mp)
    assert not np.isnan(out).any()
    assert out[0, 1] > 0.8 and abs(out[0, 3]) < 1e-9 and out[0, 4] == -1 and out[0, 2] == 1
    assert out[1, 1] < -0.8 and out[1, 3] == -1
    assert np.array_equal(out[0, [0, 2]], [1, 1])

if __name__ == '__main__':
    for f in [test_haldane, test_expected_dosage_limits, test_bc1f2_uses_f2_enumeration,
              test_expected_dosage_infeasible_flank_fallback, test_fill_population_small]:
        f(); print('ok', f.__name__)

# phase2/test_generation.py
import step10_generation as G


def test_classify_synthetic_share_vectors():
    assert G.classify(0.25, 0.5, 0.25) == 'F2'
    assert G.classify(0.5, 0.5, 0.0) == 'BC1'
    assert G.classify(0.625, 0.25, 0.125) == 'BC1F2'
    assert G.classify(0.5, 0.0, 0.5) == 'DH'
    # noisy but still nearest to the right class
    assert G.classify(0.28, 0.47, 0.25) == 'F2'
    assert G.classify(0.55, 0.45, 0.0) == 'BC1'
    assert G.classify(0.6, 0.28, 0.12) == 'BC1F2'
    assert G.classify(0.47, 0.03, 0.5) == 'DH'


def test_classify_mirrored_backcross_still_classifies_as_backcross():
    # a reversed backcross (declared recurrent A is genotypically the donor) must not default to F2
    assert G.classify(0.0, 0.5, 0.5) == 'BC1'
    assert G.classify(0.125, 0.25, 0.625) == 'BC1F2'


def test_reversed_backcross_swaps_recurrent():
    rec, rev = G.resolve_recurrent('BC1', A_hom=0.1, B_hom=0.6, A_id='PA', B_id='PB')
    assert rec == 'PB' and rev is True
    rec, rev = G.resolve_recurrent('BC1F2', A_hom=0.15, B_hom=0.55, A_id='PA', B_id='PB')
    assert rec == 'PB' and rev is True
    rec, rev = G.resolve_recurrent('BC1', A_hom=0.6, B_hom=0.1, A_id='PA', B_id='PB')
    assert rec == 'PA' and rev is False
    # reversal logic only applies to BC1/BC1F2, never F2/DH
    rec, rev = G.resolve_recurrent('F2', A_hom=0.1, B_hom=0.6, A_id='PA', B_id='PB')
    assert rec == 'PA' and rev is False


if __name__ == '__main__':
    for f in [test_classify_synthetic_share_vectors, test_classify_mirrored_backcross_still_classifies_as_backcross,
              test_reversed_backcross_swaps_recurrent]:
        f(); print('ok', f.__name__)

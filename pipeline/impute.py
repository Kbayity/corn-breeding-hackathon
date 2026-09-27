# phase2/impute.py
"""Conditional-expectation fill of missing biparental progeny genotypes from flanking markers (Haldane map)."""
import itertools, numpy as np

def haldane(cm):
    return 0.5 * (1.0 - np.exp(-2.0 * np.asarray(cm, float) / 100.0))

def _gamete_configs():
    return np.array(list(itertools.product([0, 1], repeat=3)), dtype=float)   # (8,3): l, m, r alleles (1 = A)

def _trans(same, r):
    """P(next allele | previous) for a (N,) vector r and a (K,) boolean 'same' -> (N,K)."""
    return np.where(same[None, :], 1.0 - r[:, None], r[:, None])

FALLBACK_COUNTS = {'drop_left': 0, 'drop_right': 0, 'prior': 0}   # cells whose flanking calls were infeasible under the generation model

def _dosage_core(gL, gR, rL, rR, gen):
    """Vectorized weighted enumeration. gen in {'F2','DH','BC'} only (DH2 already folded into DH by the caller,
    with rL/rR pre-adjusted). Returns (num, den); den == 0 marks a row whose flanking calls are impossible
    under the generation model (e.g. a het call flanking a DH/BC line)."""
    hasL = gL >= 0; hasR = gR >= 0
    G = _gamete_configs()
    if gen == 'F2':
        cfg = np.array([np.concatenate([a, b]) for a in G for b in G])   # (64,6): l1,m1,r1,l2,m2,r2
        w = 0.25 * np.ones((len(gL), len(cfg)))
        for (li, mi, ri) in [(0, 1, 2), (3, 4, 5)]:
            tl = _trans(cfg[:, li] == cfg[:, mi], rL); tr = _trans(cfg[:, ri] == cfg[:, mi], rR)
            w *= np.where(hasL[:, None], tl, 0.5) * np.where(hasR[:, None], tr, 0.5)
        dl = cfg[:, 0] + cfg[:, 3]; dr = cfg[:, 2] + cfg[:, 5]; dm = cfg[:, 1] + cfg[:, 4]
    elif gen == 'DH':
        cfg = G; w = 0.5 * np.ones((len(gL), 8))
        tl = _trans(cfg[:, 0] == cfg[:, 1], rL); tr = _trans(cfg[:, 2] == cfg[:, 1], rR)
        w *= np.where(hasL[:, None], tl, 0.5) * np.where(hasR[:, None], tr, 0.5)
        dl = 2 * cfg[:, 0]; dr = 2 * cfg[:, 2]; dm = 2 * cfg[:, 1]
    elif gen == 'BC':
        cfg = G; w = 0.5 * np.ones((len(gL), 8))
        tl = _trans(cfg[:, 0] == cfg[:, 1], rL); tr = _trans(cfg[:, 2] == cfg[:, 1], rR)
        w *= np.where(hasL[:, None], tl, 0.5) * np.where(hasR[:, None], tr, 0.5)
        dl = cfg[:, 0] + 1; dr = cfg[:, 2] + 1; dm = cfg[:, 1] + 1
    else:
        raise ValueError(gen)
    mask = np.ones_like(w, dtype=bool)
    mask &= np.where(hasL[:, None], dl[None, :] == gL[:, None], True)
    mask &= np.where(hasR[:, None], dr[None, :] == gR[:, None], True)
    wm = w * mask
    return wm @ dm, wm.sum(1)

def expected_dosage(gL, gR, rL, rR, gen):
    """E[dosage of A allele at target | flanking dosages gL, gR (-1 = no flank), recombination fractions rL, rR].
    gen in {'F2','DH','DH2','BC','BC1F2'} (BC: A is the recurrent parent). All inputs 1-D arrays of equal length.
    A flanking dosage inconsistent with the generation model (e.g. a heterozygous call flanking a DH line, or a
    donor-homozygous call flanking a BC line) leaves a row's config mask empty (denominator 0). Such rows fall
    back, in order: (a) drop the left flank, (b) rows still empty: drop the right flank instead (restoring the
    original left flank), (c) rows still empty: drop both (the generation prior). This never returns NaN.
    Fallback counts are tallied in FALLBACK_COUNTS.
    'BC1F2' (a backcross selfed once) has no dedicated transition model: all three dosage classes are feasible,
    same as F2, so it reuses the F2 enumeration as an approximation (documented; not exact for BC1F2's skewed
    class shares, only for which flanking calls are feasible)."""
    gL = np.asarray(gL, float); gR = np.asarray(gR, float); rL = np.asarray(rL, float); rR = np.asarray(rR, float)
    if gen == 'DH2':
        rL = 1.5 * rL - rL ** 2; rR = 1.5 * rR - rR ** 2; gen = 'DH'
    if gen == 'BC1F2':
        gen = 'F2'
    num, den = _dosage_core(gL, gR, rL, rR, gen)
    out = np.divide(num, den, out=np.full_like(den, np.nan), where=den > 0)
    bad = np.where(den == 0)[0]
    if len(bad):
        num_a, den_a = _dosage_core(np.full(len(bad), -1.0), gR[bad], rL[bad], rR[bad], gen)
        out[bad] = np.divide(num_a, den_a, out=np.full_like(den_a, np.nan), where=den_a > 0)
        ok_a = den_a > 0
        FALLBACK_COUNTS['drop_left'] += int(ok_a.sum())   # resolved by dropping the left flank only
        bad2 = bad[~ok_a]
        if len(bad2):
            num_b, den_b = _dosage_core(gL[bad2], np.full(len(bad2), -1.0), rL[bad2], rR[bad2], gen)
            out[bad2] = np.divide(num_b, den_b, out=np.full_like(den_b, np.nan), where=den_b > 0)
            ok_b = den_b > 0
            FALLBACK_COUNTS['drop_right'] += int(ok_b.sum())   # resolved by dropping the right flank only
            bad3 = bad2[~ok_b]
            if len(bad3):
                FALLBACK_COUNTS['prior'] += len(bad3)   # resolved only by the generation prior (both flanks dropped)
                num_c, den_c = _dosage_core(np.full(len(bad3), -1.0), np.full(len(bad3), -1.0), rL[bad3], rR[bad3], gen)
                out[bad3] = num_c / den_c   # den_c always > 0: no constraints -> full config mass
    return out

def _nearest_called(called):
    """called: (R,M) bool over markers in map order for one chromosome. Returns left/right index arrays (R,M), -1 where none."""
    R, M = called.shape
    idx = np.where(called, np.arange(M)[None, :], -1)
    left = np.maximum.accumulate(idx, axis=1)
    idxr = np.where(called, np.arange(M)[None, :], M)
    right = np.minimum.accumulate(idxr[:, ::-1], axis=1)[:, ::-1]
    right = np.where(right == M, -1, right)
    return left, right

def fill_parent(par, mp, panel_mean_sign):
    """Fill NA in an inbred parent row from its nearest called marker on the chromosome, else panel sign. Returns (row, n_flank, n_panel)."""
    par = par.copy(); n_flank = n_panel = 0
    for ch in np.unique(mp['chrom']):
        ix = np.where(mp['chrom'] == ch)[0]; ix = ix[np.argsort(mp['cM'][ix])]
        v = par[ix]; called = ~np.isnan(v)
        if called.sum() == 0:
            par[ix] = panel_mean_sign[ix]; n_panel += len(ix); continue
        pos = mp['cM'][ix]; cp = pos[called]; cv = v[called]
        for j in np.where(~called)[0]:
            k = np.argmin(np.abs(cp - pos[j])); par[ix[j]] = cv[k]; n_flank += 1
    return par, n_flank, n_panel

def fill_population(prog, parA, parB, gen, mp, chunk=200000):
    """prog: (n, 2911) float file-coded progeny with NaN; parA/parB: (2911,) file-coded parents without NaN.
    gen: 'F2'|'DH'|'DH2'|'BC' (A = recurrent for BC). mp: dict chrom (2911,), cM (2911,). Returns filled (n,2911) float32 in file coding."""
    prog = np.asarray(prog, float); out = prog.copy()
    poly = parA != parB
    mono = ~poly
    out[:, mono] = np.where(np.isnan(prog[:, mono]), parA[mono][None, :], prog[:, mono])
    for ch in np.unique(mp['chrom']):
        ix = np.where((mp['chrom'] == ch) & poly)[0]; ix = ix[np.argsort(mp['cM'][ix])]
        if len(ix) == 0:
            continue
        pos = mp['cM'][ix]; pA = parA[ix]
        d = 1.0 + prog[:, ix] * pA[None, :]                 # A-dosage, NaN where missing
        called = ~np.isnan(d)
        left, right = _nearest_called(called)
        rr, cc = np.where(~called)
        for s in range(0, len(rr), chunk):
            r_ = rr[s:s + chunk]; c_ = cc[s:s + chunk]
            L = left[r_, c_]; Rr = right[r_, c_]
            gL = np.where(L >= 0, d[r_, np.clip(L, 0, None)], -1.0)
            gR = np.where(Rr >= 0, d[r_, np.clip(Rr, 0, None)], -1.0)
            rL = haldane(np.where(L >= 0, pos[c_] - pos[np.clip(L, 0, None)], 0.0))
            rR = haldane(np.where(Rr >= 0, pos[np.clip(Rr, 0, None)] - pos[c_], 0.0))
            e = expected_dosage(gL, gR, rL, rR, gen)
            out[r_, ix[c_]] = (e - 1.0) * pA[c_]
    return out.astype(np.float32)

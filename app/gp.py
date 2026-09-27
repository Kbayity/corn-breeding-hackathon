# Marker models shared by 20_gp_forward.py and 40_score.py.
#   Ridge                 rrBLUP via normal equations (X'X built once, reused across lambdas)
#   fit_within_model      rrBLUP on within-family deviations, lambda by inner forward split
#   FamilySimulator       simulate progeny of a planned cross from parent genotypes + genetic map,
#                         to predict the family's genetic spread (sigma_G) before planting
import numpy as np, pandas as pd
import hackdata as H, evalkit as E

LAMS = [0.5, 2, 10, 50]          # multiples of p (number of markers)


class Ridge:
    def __init__(self, X, y, w=None):
        self.mu_x = X.mean(0, dtype=np.float64).astype(np.float32)
        Xc = X - self.mu_x
        w = np.ones(len(y)) if w is None else w / w.mean()
        self.ybar = np.average(y, weights=w)
        Xw = Xc * np.sqrt(w)[:, None].astype(np.float32)
        self.XtX = (Xw.T.astype(np.float64) @ Xw.astype(np.float64))
        self.Xty = Xc.T.astype(np.float64) @ (w * (y - self.ybar))
        self.p = X.shape[1]

    def coef(self, lam_mult):
        A = self.XtX.copy(); A[np.diag_indices_from(A)] += lam_mult * self.p
        return np.linalg.solve(A, self.Xty)

    def predict(self, X, b):
        return self.ybar + (X - self.mu_x).astype(np.float64) @ b


def fit_within_model(tr, Xtr, Y, trait='YLD'):
    """rrBLUP on y_w (within-family deviation). tr: training lines aligned with Xtr, all YEAR < Y.
    Returns (model, beta, lam, inner_within_r, slope) with lambda chosen on an inner forward split;
    slope = regression of observed y_w on the family-centered prediction in the inner year (scale calibration)."""
    y = tr[f'y_w_{trait}'].values; ok = ~np.isnan(y)
    inner = (tr.YEAR < Y - 1).values & ok; val = (tr.YEAR == Y - 1).values & ok
    mi = Ridge(Xtr[inner], y[inner]); sc, pvs = {}, {}
    for lm in LAMS:
        pv = mi.predict(Xtr[val], mi.coef(lm)); pvs[lm] = pv
        sc[lm] = E.summarize_within(E.within_family(tr[val].assign(pred=pv), truth=f'y_w_{trait}'))['r_median']
    lam = max(sc, key=sc.get)
    v = tr[val].assign(pred=pvs[lam]); v['pc'] = v.pred - v.groupby('POP').pred.transform('mean')
    slope = float(np.polyfit(v.pc, v[f'y_w_{trait}'], 1)[0])
    m = Ridge(Xtr[ok], y[ok]); return m, m.coef(lam), lam, sc[lam], slope


class FamilySimulator:
    """Progeny genotypes of a cross under Haldane recombination along the cM map.
    Coding matches the imputed files: homozygous -1 / +1, heterozygous 0.
      F2      : (g1 + g2) / 2, both gametes from the F1
      BC      : (g1 + recurrent) / 2
      DH, DH2 : g1 (doubled gamete)"""
    def __init__(self, seed=0):
        mm = H.marker_map()
        self.order = np.lexsort((mm.cM.values, mm.chrom.values))          # sorted by chrom, then cM
        ch = mm.chrom.values[self.order]; cm = mm.cM.values[self.order]
        d = np.diff(cm); new_chrom = ch[1:] != ch[:-1]
        self.r = np.where(new_chrom, 0.5, 0.5 * (1 - np.exp(-2 * np.clip(d, 0, None) / 100)))  # free recombination between chromosomes
        self.rng = np.random.default_rng(seed)

    def gametes(self, a, b, n):
        """n gametes from an F1 of inbreds a, b (vectors in map order)."""
        sw = self.rng.random((n, len(self.r))) < self.r
        origin = np.concatenate([self.rng.integers(0, 2, (n, 1)), sw.astype(np.int8)], 1).cumsum(1) % 2
        return np.where(origin == 0, a, b)

    def progeny(self, a, b, gen, rp=None, n=200):
        a = a[self.order]; b = b[self.order]
        g1 = self.gametes(a, b, n)
        if gen == 'BC':
            r = (a if rp == 'a' else b); out = (g1 + r) / 2
        elif gen in ('DH', 'DH2'):
            out = g1
        else:
            out = (g1 + self.gametes(a, b, n)) / 2
        res = np.empty_like(out); res[:, self.order] = out                 # back to file column order
        return res

    def family_sigma(self, pops, PG, beta, n=200):
        """Predicted within-family genetic SD (and mean) of X @ beta for each planned family."""
        rows = []
        for r in pops.itertuples():
            if r.P1 not in PG.index or r.P2 not in PG.index:
                rows.append((r.POP, np.nan, np.nan)); continue
            a = np.rint(PG.loc[r.P1].values); b = np.rint(PG.loc[r.P2].values)
            rp = None
            if isinstance(r.RP, str): rp = 'a' if r.RP == r.P1 else 'b'
            g = self.progeny(a, b, r.GEN, rp, n) @ beta
            rows.append((r.POP, g.std(), g.mean()))
        return pd.DataFrame(rows, columns=['POP', 'sigmaG_pred', 'mean_pred']).set_index('POP')

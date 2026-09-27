# Shared evaluation metrics for forward-year validation (BRIEFING section H).
# Every function takes a frame with columns POP, pred (model score), and the truth column(s).
import numpy as np, pandas as pd
from scipy.stats import spearmanr

MIN_LINES = 30  # families smaller than this are skipped for within-family correlation


def _r(a, b):
    return float(np.corrcoef(a, b)[0, 1]) if len(a) > 2 and np.std(a) > 0 and np.std(b) > 0 else np.nan


def _rho(a, b):
    return float(spearmanr(a, b)[0]) if len(a) > 2 and np.std(a) > 0 and np.std(b) > 0 else np.nan


def within_family(d, truth='y_w', pred='pred', frac=0.10):
    """Per-family accuracy and selection gain when the top `frac` of each family is advanced.
    gain: mean truth of selected lines (0 = random selection within family, since truth is centered);
    gain_max: same for perfect selection on the observed truth; eff = gain / gain_max."""
    rows = []
    for pop, g in d.dropna(subset=[truth, pred]).groupby('POP'):
        if len(g) < MIN_LINES: continue
        k = max(int(round(frac * len(g))), 1)
        sel = g.nlargest(k, pred)[truth].mean(); best = g.nlargest(k, truth)[truth].mean()
        rows.append(dict(POP=pop, n=len(g), r=_r(g[pred], g[truth]), rho=_rho(g[pred], g[truth]),
                         gain=sel - g[truth].mean(), gain_max=best - g[truth].mean(),
                         overlap=len(set(g.nlargest(k, pred).index) & set(g.nlargest(k, truth).index)) / k))
    return pd.DataFrame(rows)


def population_level(d, truth='pop_eff', pred='pred'):
    """Correlation of predicted vs observed family effects (one row per family)."""
    m = d.groupby('POP').agg(pred=(pred, 'mean'), truth=(truth, 'first')).dropna()
    return dict(n_pops=len(m), r=_r(m.pred, m.truth), rho=_rho(m.pred, m.truth))


def overall(d, truth='y_tot', pred='pred', frac=0.10):
    """Ranking all lines of the year together (what a plot budget actually cuts)."""
    g = d.dropna(subset=[truth, pred]); k = max(int(frac * len(g)), 1)
    top_p, top_t = set(g.nlargest(k, pred).index), set(g.nlargest(k, truth).index)
    return dict(n=len(g), r=_r(g[pred], g[truth]), rho=_rho(g[pred], g[truth]),
                overlap=len(top_p & top_t) / k, overlap_random=frac,
                gain=g.nlargest(k, pred)[truth].mean() - g[truth].mean(),
                gain_max=g.nlargest(k, truth)[truth].mean() - g[truth].mean())


def summarize_within(w):
    return dict(n_pops=len(w), r_median=w.r.median(), r_mean=w.r.mean(), rho_median=w.rho.median(),
                overlap=w.overlap.mean(), gain=w.gain.mean(), gain_max=w.gain_max.mean(),
                eff=w.gain.mean() / w.gain_max.mean())

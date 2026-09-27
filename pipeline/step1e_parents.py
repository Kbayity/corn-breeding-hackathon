# phase2/step1e_parents.py
"""Group near-identical parents by IBS similarity; list 2008 near-repeat crosses."""
import os, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
import common as C

def ibs_matrix(P):
    V = P.values.astype(float); n = len(V); S = np.eye(n)
    for i in range(n):
        both = ~np.isnan(V[i])[None, :] & ~np.isnan(V)
        S[i] = np.where(both, 1.0 - np.abs(V[i][None, :] - V) / 2.0, 0.0).sum(1) / both.sum(1)
    return pd.DataFrame(S, index=P.index, columns=P.index)

def choose_threshold(S):
    """Midpoint of the largest empty gap (>= 0.01 wide) in the off-diagonal IBS tail above 0.90; else 0.95."""
    v = np.sort(S.values[np.triu_indices(len(S), 1)]); hi = v[v >= 0.90]
    if len(hi) < 2:
        return 0.95, 'default (no pairs above 0.90)'
    gaps = np.diff(hi); k = int(np.argmax(gaps))
    if gaps[k] >= 0.01:
        return float((hi[k] + hi[k + 1]) / 2), f'midpoint of largest gap ({hi[k]:.3f}–{hi[k + 1]:.3f}) in the IBS tail'
    return 0.95, 'default 0.95 (no gap >= 0.01 above 0.90)'

def components(S, thr):
    n = len(S); lab = -np.ones(n, int); cur = 0; A = S.values >= thr
    for i in range(n):
        if lab[i] >= 0:
            continue
        stack = [i]; lab[i] = cur
        while stack:
            j = stack.pop()
            for k in np.where(A[j] & (lab < 0))[0]:
                lab[k] = cur; stack.append(k)
        cur += 1
    return lab

def parent_groups(cl):
    g = pd.read_csv(os.path.join(C.OUT, f'parent_groups_{cl}.csv'), dtype=str)
    return g.set_index('pid')['group']

if __name__ == '__main__':
    ph = C.load_pheno(); t = C.pop_table(ph); md = ['\n## 1e Near-identical parents and near-repeat crosses\n']
    for cl in C.CLUSTERS:
        P = C.load_parents(cl); S = ibs_matrix(P); thr, why = choose_threshold(S)
        lab = components(S, thr)
        g = pd.DataFrame({'pid': P.index, 'group': [f'G{cl}_{k}' for k in lab]}); g['group_size'] = g.groupby('group').pid.transform('size')
        g.to_csv(os.path.join(C.OUT, f'parent_groups_{cl}.csv'), index=False)
        off = S.values[np.triu_indices(len(S), 1)]
        plt.figure(figsize=(6, 3.5)); plt.hist(off, bins=100); plt.axvline(thr, color='r'); plt.yscale('log')
        plt.title(f'{cl} parent pairwise IBS (threshold {thr:.3f})'); plt.tight_layout(); plt.savefig(os.path.join(C.OUT, f'parent_ibs_hist_{cl}.png'), dpi=100); plt.close()
        md.append(f'{cl}: {len(P)} parents, threshold IBS >= {thr:.3f} ({why}); groups {g.group.nunique()}; parents in multi-member groups {(g.group_size > 1).sum()}; largest group {g.group_size.max()}. '
                  f'IBS off-diagonal quantiles 50/90/99/99.9%: {np.quantile(off, [.5, .9, .99, .999]).round(3).tolist()}.\n')
    rows = []
    for cl in C.CLUSTERS:
        gp = parent_groups(cl); tc = t[t.CL == cl].copy(); tc['G1'] = tc.P1.map(gp); tc['G2'] = tc.P2.map(gp)
        tc['pair'] = [tuple(sorted(x)) for x in zip(tc.G1, tc.G2)]
        hist = tc[tc.YEAR < 2008]
        hist_pairs = hist.groupby('pair').agg(n_hist_pops=('n_lines', 'size'), n_hist_lines=('n_lines', 'sum'),
                                              hist_years=('YEAR', lambda s: ','.join(map(str, sorted(s.unique())))))
        hist_groups = set(hist.G1) | set(hist.G2)
        for pop, r in tc[tc.YEAR == 2008].iterrows():
            seen = int(r.G1 in hist_groups) + int(r.G2 in hist_groups)
            nr = r.pair in hist_pairs.index
            rows.append(dict(CL=cl, POP=pop, GEN=r.GEN, P1=r.P1, P2=r.P2, G1=r.G1, G2=r.G2, parents_seen=seen, near_repeat=nr,
                             n_hist_pops=int(hist_pairs.loc[[r.pair], 'n_hist_pops'].iloc[0]) if nr else 0,
                             n_hist_lines=int(hist_pairs.loc[[r.pair], 'n_hist_lines'].iloc[0]) if nr else 0,
                             hist_years=hist_pairs.loc[[r.pair], 'hist_years'].iloc[0] if nr else ''))
    nr = pd.DataFrame(rows); nr.to_csv(os.path.join(C.OUT, 'near_repeat_2008.csv'), index=False)
    md.append(f'2008 populations: {len(nr)}; near-repeat crosses (both parent groups crossed before 2008): {nr.near_repeat.sum()} '
              f'(C1 {nr[nr.CL == "C1"].near_repeat.sum()}, C2 {nr[nr.CL == "C2"].near_repeat.sum()}); parents_seen distribution: {nr.parents_seen.value_counts().sort_index().to_dict()}.\n')
    md.append(nr[nr.near_repeat].sort_values('n_hist_lines', ascending=False)[['CL', 'POP', 'GEN', 'G1', 'G2', 'n_hist_pops', 'n_hist_lines', 'hist_years']].to_markdown(index=False) + '\n')
    open(os.path.join(C.OUT, 'checks.md'), 'a').write('\n'.join(md))

    def selfcheck():
        for cl in C.CLUSTERS:
            gp = parent_groups(cl); assert gp.index.nunique() == len(gp) and len(gp) in (258, 260)
        assert len(nr) == 157 and set(nr.parents_seen) <= {0, 1, 2}
    selfcheck()

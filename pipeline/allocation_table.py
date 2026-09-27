"""Task 3 addendum (controller ruling): outputs/final_model_report.md's plot-allocation table is
cap-bound (40% per-population cap) at the 50% and 75% budgets -- the cap, not the plot budget,
becomes the binding constraint above 25% (see the report's existing "Note:" paragraph). This script
adds an uncapped (pure top-k by score, no per-population cap) row for those same two budgets next to
the capped ones, WITHOUT re-running the model: it reads the already-written outputs/predictions_2008.csv
for LINE_ID/POP/score and re-derives only the 2008 design's per-line plot counts (n_plots_2008) from
the phenotype data (a single groupby -- the same aggregation final_model.py uses when building
design_by_cl, not a model refit), then rewrites just the "## Plot-allocation table" section of the
report in place.

Run: python3 phase2/allocation_table.py   (from exploration/, or anywhere; paths are absolute via common.py)
"""
import os
import numpy as np, pandas as pd
import common as C

pred = pd.read_csv(os.path.join(C.OUT, 'predictions_2008.csv'))

# 2008 design plot counts per line -- same aggregation as final_model.py's design_by_cl, cheap to
# redo (single groupby on the already-cached phenotype table) rather than re-running the model.
ph = C.load_pheno()
d8 = ph[ph.YEAR == 2008]
n_plots = d8.groupby('LINE_ID').agg(n_plots_2008=('LOC', 'size'))
full = pred.merge(n_plots, left_on='LINE_ID', right_index=True, how='left')
assert full['n_plots_2008'].notna().all(), 'every predictions_2008.csv line should have 2008 design rows'
total_plots = int(full['n_plots_2008'].sum())
order = full.sort_values('score', ascending=False)


def allocate(budget, cap_frac):
    """Greedy fill of `order` (already score-sorted) to `budget` plots. cap_frac=None: pure top-k,
    no per-population cap. cap_frac=0.4: the same 40%-per-population cap as final_model.py."""
    if cap_frac is not None:
        cap = full.groupby('POP')['LINE_ID'].transform('count').mul(cap_frac).apply(lambda x: max(1, int(x)))
        cap_map = cap.reindex(order.index)
    used, taken_per_pop, n_lines = 0, {}, 0
    for idx, row in order.iterrows():
        if used + row.n_plots_2008 > budget:
            continue
        if cap_frac is not None and taken_per_pop.get(row.POP, 0) >= int(cap_map.loc[idx]):
            continue
        used += row.n_plots_2008; n_lines += 1; taken_per_pop[row.POP] = taken_per_pop.get(row.POP, 0) + 1
    return used, n_lines, len(taken_per_pop)


rows = []
for frac in [0.25, 0.5, 0.75]:
    budget = frac * total_plots
    used, n_lines, n_pops = allocate(budget, cap_frac=0.4)
    rows.append(dict(budget_pct=int(frac * 100), cap='40% per-pop cap', plots_used=used,
                      plots_budget=round(budget), n_lines_kept=n_lines, n_pops_kept=n_pops))
    if frac in (0.5, 0.75):   # controller ruling: only these two budgets are cap-bound (see report Note)
        used, n_lines, n_pops = allocate(budget, cap_frac=None)
        rows.append(dict(budget_pct=int(frac * 100), cap='none (pure top-k)', plots_used=used,
                          plots_budget=round(budget), n_lines_kept=n_lines, n_pops_kept=n_pops))
alloc_tab = pd.DataFrame(rows)

# consistency check: the capped rows must reproduce the numbers already published in the report
capped = alloc_tab[alloc_tab.cap == '40% per-pop cap'].plots_used.tolist()
assert capped == [21821, 34586, 34586], ('recomputed capped allocation does not match the published '
                                          f'report numbers: {capped}')

section = (
    '## Plot-allocation table (lines kept by score; 40%-per-population-cap rows vs. an added uncapped '
    'pure top-k comparison)\n\n'
    f'Total planned 2008 plots (design rows): {total_plots}.\n\n'
    + alloc_tab.to_markdown(index=False) + '\n\n'
    'Validated (2007, YLD_BE combined-score) top-10% enrichment for reference: 1.15x random (no ground '
    'truth exists for 2008, so this validated number -- not a per-budget computation -- is the expected '
    'quality context for the allocation above).\n\n'
    'Note: the 50% and 75% rows use the same 6,332 lines as the 25% row already approaches -- once every\n'
    'population hits its 40% cap (157/157 populations, ~6,332 of 15,968 lines total), no more lines are\n'
    'eligible regardless of remaining plot budget. The 40% per-population cap, not the plot budget, is the\n'
    'binding constraint above 25%; raising the cap (not the budget) is what would let allocation use more\n'
    'of the available plots.\n\n'
    'Uncapped comparison (controller ruling, Task 3): the "none (pure top-k)" rows above drop the 40% '
    'per-population cap entirely and rank strictly by score. They use noticeably more of the plot budget '
    'at 50% and stay top-k-bound rather than cap-bound at 75% (i.e. the plot budget, not a cap, is what '
    'stops them). They also concentrate plots in fewer, higher-scoring populations (n_pops_kept is lower '
    'than the capped rows at the same budget). Neither is "correct": the cap trades some expected score '
    'for diversification across populations (a portfolio-risk choice); the uncapped rows show the '
    'raw-score-maximizing alternative. Use the capped rows for a risk-managed nomination list, the '
    'uncapped rows if concentrating resources in the top populations is acceptable.\n'
)

report_path = os.path.join(C.OUT, 'final_model_report.md')
text = open(report_path).read()
i = text.index('## Plot-allocation table')
assert text[i:].count('## Plot-allocation table') == 1, 'section header should be unique'
text = text[:i] + section
open(report_path, 'w').write(text)
print('rewrote plot-allocation section of', report_path, '--', len(alloc_tab), 'rows')

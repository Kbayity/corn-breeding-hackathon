# phase2/step8_assemble.py
"""Assemble one table per step into outputs/RESULTS_phase2a.md; the Recommendation section is left for the controller."""
import os, re, pandas as pd
import common as C
O = C.OUT
def section(title, body):
    return f'## {title}\n\n{body}\n'

def strata_table(df, count_col, corr_cols, cols_order, thresh=5):
    """Markdown of df[cols_order] with corr_cols blanked to 'n<5' where count_col < thresh."""
    d = df[cols_order].round(3)
    mask = (df[count_col] < thresh).values
    for c in corr_cols:
        d[c] = d[c].astype(object)
        d.loc[mask, c] = 'n<5'
    return d.to_markdown(index=False)

PLACEHOLDER = '(controller fills in)\n'
recommendation = PLACEHOLDER
_rp = os.path.join(O, 'RESULTS_phase2a.md')
if os.path.exists(_rp):
    _old = open(_rp).read()
    _m = re.search(r'## Recommendation\n\n(.*)\Z', _old, re.S)
    if _m and _m.group(1).strip() != PLACEHOLDER.strip():
        recommendation = _m.group(1)
        if not recommendation.endswith('\n'):
            recommendation += '\n'

parts = ['# Phase 2a results (checkpoint)\n',
         'All numbers come from YEAR < 2008 phenotypes. 2008 trait values were never read. Per-step details: DELIVERABLES.md, checks.md, step2_generation.md, step4_popmean.md, step5_withinpop.md, step6_maturity.md, step7_envspecific.md.\n']
deliv = open(os.path.join(O, 'DELIVERABLES.md')).read()
m = re.search(r'## 3\. What is NOT stated.*?(?=\n## 4)', deliv, re.S)
parts.append(section('Step 0 — deliverables and scoring', m.group(0) if m else deliv[:3000]))
checks = open(os.path.join(O, 'checks.md')).read()
def grab(h):
    m = re.search(rf'## {h}.*?(?=\n## |\Z)', checks, re.S); return m.group(0) if m else f'(section {h} missing)'
parts.append(section('Step 1 — correctness checks', '\n\n'.join(grab(h) for h in ['1a', '1b', '1c', '1d', '1e'])))
parts.append(section('Step 2 — generation-aware expectations', open(os.path.join(O, 'step2_generation.md')).read()))
parts.append(section('Step 3 — clean variance components', pd.read_csv(os.path.join(O, 'step3_variance.csv')).round(2).to_markdown(index=False)))
s4 = pd.read_csv(os.path.join(O, 'step4_metrics.csv'))
s4a = s4[s4.stratum == 'all'].pivot_table(index=['CL', 'test_year'], columns='model', values=['pearson', 'spearman']).round(3)
s4strata_md = strata_table(s4[s4.stratum != 'all'], 'n', ['pearson', 'p_lo', 'p_hi', 'spearman'],
                           ['test_year', 'CL', 'model', 'stratum', 'n', 'pearson', 'p_lo', 'p_hi', 'spearman'])
parts.append(section('Step 4 — population-mean head-to-head', s4a.to_markdown() + '\n\nStrata (per fold):\n\n' + s4strata_md))
s5 = pd.read_csv(os.path.join(O, 'step5_metrics.csv'))
s5a = s5[s5.stratum == 'all'].pivot_table(index=['CL', 'test_year'], columns='model', values=['rMP_median', 'rMG_median', 'top10_mean']).round(3)
s5strata_md = strata_table(s5[s5.stratum != 'all'], 'n_pops', ['rMP_median', 'rMP_lo', 'rMP_hi', 'top10_mean'],
                           ['CL', 'test_year', 'model', 'stratum', 'n_pops', 'rMP_median', 'rMP_lo', 'rMP_hi', 'top10_mean'])
parts.append(section('Step 5 — within-population head-to-head', s5a.to_markdown() + '\n\nStrata:\n\n' + s5strata_md))
parts.append(section('Step 6 — maturity and secondary traits', open(os.path.join(O, 'step6_maturity.md')).read()))
parts.append(section('Step 7 — broad vs environment-specific', open(os.path.join(O, 'step7_envspecific.md')).read().split('\n|')[0]))
parts.append(section('Step 8 — combined score across lines', open(os.path.join(O, 'step9_combined.md')).read()))
parts.append('## Recommendation\n\n' + recommendation)
open(os.path.join(O, 'RESULTS_phase2a.md'), 'w').write('\n'.join(parts))

def selfcheck():
    txt = open(os.path.join(O, 'RESULTS_phase2a.md')).read()
    assert all(f'## Step {i}' in txt for i in range(9)) and '## Recommendation' in txt
selfcheck()

# Validation results (forward-year, 2008 untouched)

All numbers are yield (YLD). Test sets are the new families of 2006 and 2007 in each cluster (C1 and C2), each predicted from earlier years only: 4 cluster-year sets, about 200 families and about 28k lines in total. Reproduce with `./run_all.sh`, or run `20_gp_forward.py` and `30_popmean_h2h.py` directly. Tables are in `cache/results/` and logs in `cache/logs/`.

## Step 2 — marker model for lines (`20_gp_forward.py`)

rrBLUP on 2,911 imputed SNPs, trained on every earlier line of the same cluster. λ is picked by an inner forward split.

| Target the model learns | Within-family r (median) | Family r | All-lines r |
|---|---|---|---|
| `y_w`: within-family deviation | **0.22** (0.19–0.26) | 0.23 | 0.22 |
| `y_tot`: family + deviation, reliability-weighted | 0.13 | 0.45 | 0.39 |
| Two-part: family from `y_tot` + deviation from `y_w` | **0.22** | 0.45 | **0.41** |

- Within-family ranking works the same whether 0, 1 or 2 parents were seen before, so the model transfers to new families.
- For a 10% selection within each family, the gain is about 3 bu/ac over random. A perfect pick on noisy single plots would get about 14.

## Step 3 — predicting family means (`30_popmean_h2h.py`)

**Raw testcross family effect.** This is what the field observes, tester included.

| Method | r (mean of 4) | Top-20% families: gain (bu/ac) |
|---|---|---|
| random | 0.07 | 1.3 |
| parent history (shrunk mean of past families sharing a parent) | 0.38 | 8.1 |
| tester history only | 0.52 | 11.3 |
| pedigree GCA ridge (parents + tester) | 0.57 | 11.0 |
| **parent-genomic ridge** (contribution-weighted parent SNPs + tester) | **0.67** | **11.9** (max 17.1) |
| line markers (step 2, family mean) | 0.45 | 7.0 |
| ensemble (z-average of pedigree, parent-genomic, line markers) | 0.63 | 10.4 |

Parent-genomic minus parent history: +0.28 r, 95% CI [+0.18, +0.40] (paired bootstrap over families).

**Line-side (GCA) accuracy.** Families are compared only within the same tester and year (138 families, 17 groups), which removes the tester's share of the hybrid.

| Method | r |
|---|---|
| parent history | 0.21 |
| pedigree GCA | 0.27 |
| parent-genomic | 0.26 |
| ensemble | 0.27 |
| line markers | 0.20 |

No method is significantly better than parent history here: every CI crosses 0, for example parent-genomic +0.05 [−0.13, +0.22].

## What this means for the product

1. **The tester is the largest single driver of a family's testcross mean.** Tester history alone gives r = 0.52. A tool that ranks raw predicted testcross yield across families will partly be ranking *testers*. For advancement decisions, strip out the tester term, which the pedigree and parent-genomic models estimate explicitly, and rank lines on predicted GCA. Report the predicted testcross yield with the tester included separately, because that is the scenario's literal "predict performance".
2. **Choosing families on their own merit is only modestly predictable** (r ≈ 0.25) and not clearly better than parent track record. This is the main source of uncertainty, and the recommendation should hedge it. This is the conservative vs aggressive trade-off: spread plots across families when family predictions are unsure, or concentrate them when parents are well characterized.
3. **Ranking within a family is where markers reliably add value** (r ≈ 0.22 in every set). The defensible core is to pick the best lines inside each family with markers.
4. **Caveats:**
   - The test sets are small, and a single set's r has an SE of about 0.14 (random reached 0.25 in one set).
   - Family effects still include SET field effects.
   - The truth is single-plot phenotypes, so every accuracy here is lower than accuracy against true genetic value, by roughly a factor of √H for lines.

## Step 4 — final line scores (`40_score.py`)

For each candidate line, using only information available in January:

| Column | Meaning |
|---|---|
| `F` | family GCA: line-side part of the pedigree and parent-genomic models, tester removed |
| `T` | tester part |
| `D` | within-family marker deviation |
| `gca` = F + D | ranks lines for advancement |
| `testcross` = F + T + D | predicted hybrid yield |
| `sd` | prediction SD: family error by #parents seen, plus within-family error |
| `sigmaG_pred` | predicted within-family genetic SD, from simulated progeny of the planned cross |
| `tier` | high / medium / low, from relatedness to tested material |

Calibration against the observed 2006 and 2007 seasons:

| | 2006 | 2007 |
|---|---|---|
| Family testcross r | 0.76 | 0.53 |
| Observed-vs-predicted slope (1 = right scale) | 1.43 | 0.54 |
| Nominal 80% interval coverage | 0.76 | 0.66 |
| Within-family slope | 1.03 | 1.09 |
| Predicted σG: median (observed median) | 4.98 (5.62) | 4.89 (5.44) |
| Predicted σG vs observed, r | 0.22 | 0.26 |

- **Scale calibration.** The slope correction is estimated on the 3 previous years, replayed forward. The error SD uses leave-one-year-out slopes, so it includes calibration instability. 2007 is less predictable than its history, so read the intervals as roughly 70% intervals.
- **σG.** The simulated progeny spread is rescaled to the historical median. Its family-to-family signal is weak, so it only mildly affects the uncertainty.

## Step 5 — plot allocation: conservative vs aggressive (`50_allocation.py`)

**Setup.** Each simulated season has three stages:
1. **January:** the strategy plants a budget b of the candidates.
2. **Field:** the program advances the top 5% of all candidates, chosen among the planted lines on yield in half the locations.
3. **Scoring:** the advanced lines are scored on the *other* half of the locations.

There are 100 replicates, each with a random location split plus a family bootstrap, averaged over the 4 cluster-year sets. "Full program" means planting everything and selecting on yield alone.

**GCA truth** (tester-adjusted; this is the advancement decision). Full program = 3.85 bu/ac.

| Strategy | 10% plots: gain (P10) | Retained | 25% plots: gain (P10) | Retained |
|---|---|---|---|---|
| random | 2.02 (1.51) | 53% | 3.00 (2.40) | 78% |
| parent history (traditional) | 1.07 (−1.52) | 28% | 2.56 (1.12) | 67% |
| **spread**: every family gets its share, best lines inside it by markers | **4.88 (4.28)** | **127%** | 4.98 (4.11) | 129% |
| tilt τ=0.5 toward predicted-good families | 4.84 (4.14) | 126% | 4.98 (4.22) | 129% |
| tilt τ=2 | 4.57 (3.62) | 119% | 4.53 (3.48) | 118% |
| concentrate: top predicted lines, no family limit | 2.54 (0.15) | 66% | 3.61 (2.19) | 94% |

**Testcross truth** (raw hybrid yield, tester included). Full program = 6.16 bu/ac. At 10% of plots:
- spread: 98% retained
- **tilt τ=0.5: 111% (P10 6.04)**
- tilt τ=1: 115%
- concentrate: 102% (P10 4.10)

## Recommendation (for the pitch)

1. **Spread, then tilt slightly.** Keep every family in the program, tilt plots mildly toward families predicted better (τ ≈ 0.5), and pick lines within each family by markers. This is at or near the top under both truths, with the lowest risk. With **10% of the plots it delivers about 110–125% of the gain of testing every line**, because marker preselection adds information that phenotypes from a few locations don't have.
2. **The real conservative-vs-aggressive dial is concentration, not κ.** Concentrating plots on the top predicted families ("aggressive") loses gain *and* adds risk: P10 falls to about 0 at a 10% budget, and it keeps only 15–35% of families. Traditional parent-history selection concentrates too, and does worse than random at small budgets. Uncertainty weighting (κ from −2 to +2) barely changes anything once plots are spread.
3. **The defensible default is conservative = spread (τ = 0).** Aggressive = τ ≥ 1 or concentration, which is justified only if the goal is testcross yield with the current testers rather than line merit.
4. **Caveat: most individual elite lines are missed.** At 10% of plots only about 21% of the true top-5% lines get planted. The gain comes from raising the average quality of what is planted, not from finding every star. The 2008 answer key has not been used; the final scoring run is `40_score.py 2008`, followed by a one-time evaluation.

## Digital twin, Phase 1 — genotype layer + benchmark C (`60_imputation_bench.py`, `hmm.py`)

**A. Masking benchmark.** 10% of real observed progeny calls at parent-polymorphic markers were hidden (1.04 M calls in 999 families) and then recovered by each method.

| Method | Overall | F2 | BC | DH |
|---|---|---|---|---|
| family mean of the other lines | 51.9% | 52.1% | 54.3% | 6.8% |
| nearest flanking call | 57.7% | 56.8% | 61.0% | 48.0% |
| **parent-aware HMM** (ε = 0.01; ε from 0.003 to 0.03 gives the same result) | **75.7%** | 73.9% | 81.2% | 76.0% |

The provided imputed files can't be scored this way, because they were built with the hidden calls visible.

**D. Downstream effect.** Forward-year within-family rrBLUP (median within-family r):

| | C1 2006 | C1 2007 | C2 2006 | C2 2007 | Mean |
|---|---|---|---|---|---|
| provided imputation + family-mean fill | 0.203 | 0.258 | 0.230 | 0.186 | 0.219 |
| **HMM dosages** | 0.252 | 0.284 | 0.260 | 0.240 | **0.259** |

That's +18%, and it improves in all 4 sets. Use it via `hackdata.load_geno(cl, keys, source='hmm')`.

**C. Twin realism.** Each real family was simulated with the twin's recombination model, given the real missing-data pattern and genotyping error, then passed through the identical HMM pipeline.

| Check | Real vs twin | Verdict |
|---|---|---|
| Genotype ratios: F2 het / homA | 0.496 / 0.258 vs 0.490 / 0.255 | pass |
| Genotype ratios: BC het / homA | 0.490 / 0.480 vs 0.486 / 0.488 | pass |
| Crossovers per line: F2 | 20.8 vs 19.3 (−7%) | pass |
| Crossovers per line: BC | 10.8 vs 9.9 (−9%) | pass |
| Crossovers per line: DH | 13.7 vs 10.4 (−24%) | **fail** (DH is about 3% of families; real DH look like they had more than one meiosis) |
| Crossovers, per-family correlation real vs twin | 0.81 | pass |
| LD decay: mean r² by map distance, 0–5 cM … 80+ cM | 0.776 / 0.631 / 0.473 / 0.255 / 0.074 / 0.015 vs 0.774 / 0.646 / 0.491 / 0.278 / 0.100 / 0.020 | pass (max difference 0.026) |
| HMM masking accuracy: F2 / BC | 0.729 / 0.806 vs 0.757 / 0.831 | marginal: the twin is about 2.5 points too clean |
| DH residual heterozygosity | 3.4% vs 0% | minor miss |

**Verdict:** the twin's genotype layer is realistic for F2 and BC families (about 97% of the data). It is slightly too clean, because real data has extra error sources the twin doesn't model. DH families are only approximately right.

**QC finding worth a slide.** 30 of 999 families (3%) have around 46% of their calls contradicting *both* recorded parents at markers where the two parents agree. That's about what you'd get by chance, which points to a wrong pedigree record, i.e. a mislabelled parent. Flagging these automatically is a cheap product feature.

## Research packages run natively (`80_export_native.py`, `native/*.R`, `81_score_native.py`)

The same forward-year splits (HMM genotypes) were exported to Arrow and float32 files. Each package fitted its models in its own language, with its own defaults or internal tuning (conda env `hack-r`, packages built from the `research_tests/` clones; see `envs/README.md`). Python then scored every model with the same `evalkit` metrics. Test-set truths were never exported.

**A. Within-family line ranking.** Median within-family r, mean of 4 sets:

| Model | r | Fit time per set |
|---|---|---|
| bigstatsr `big_spLinReg` (family-grouped internal CV; chose α = 0.01, i.e. near-ridge, in 3 of 4 sets) | 0.261 | 131 s |
| **Python rrBLUP (ours)** | **0.259** | ~10 s |
| Python Gaussian kernel (Nyström) | 0.256 | ~60 s |
| bWGR `emRR` (EM ridge) | 0.253 | 33 s |
| bWGR `emBC` | 0.249 | 51 s |
| VIGoR EBL | 0.238 | 147 s |
| bWGR `emEN` | 0.238 | 44 s |
| bWGR `emBB` | 0.233 | 56 s |
| bWGR `emBL` | 0.223 | 29 s |
| VIGoR BayesB | 0.195 | 230 s |

The more a model assumes a few large-effect genes, the worse it predicts: yield here is polygenic. bWGR's ridge reproduces ours within 0.006, an independent check on our implementation.

**B. Family means.** BGLR RKHS with kernels from nlkernel `transform_snps` and SKM `kernelize`, using nlkernel's default hyperparameter grids tuned on the inner year, plus a tester kernel. GBLUP is VanRaden G on the parents, C·G·Cᵀ.

| Model | Testcross r | Within-tester r |
|---|---|---|
| **Python linear kernel ridge** | **0.669** | 0.242 |
| Python Bessel | 0.668 | 0.295 |
| native PCA | 0.637 | 0.252 |
| native polynomial | 0.619 | 0.249 |
| native arc-cosine (SKM) | 0.617 | 0.199 |
| native GBLUP | 0.617 | 0.246 |
| native Laplacian | 0.603 | 0.242 |
| native Gaussian | 0.597 | 0.247 |
| native Bessel | 0.560 | 0.185 |

The native kernels trail by 0.03–0.11. Likely causes:
- **Grid edge.** nlkernel's σ grid is too coarse for this data scale: Gaussian σ = 0.001, the edge of the grid, was chosen in 4 of 4 sets.
- **Too few families.** BGLR estimates variance components from only about 350 families.

## Parent-haplotype (segment GCA) model (`65_haplotype_features.py`, `66_haplotype_gp.py`)

**What it is.** Each line's inheritance share from each parent, per 5/10/20 cM bin, from HMM ancestry. Sanity check of the mean share from P2: F2 0.49–0.50, BC 0.25, DH 0.49. Parent × segment effects are pooled across every family that uses that parent. It uses a within-family ridge with separate penalties, tuned on the inner year.

| Model | C1 2006 | C1 2007 | C2 2006 | C2 2007 | Mean |
|---|---|---|---|---|---|
| rrBLUP (reference) | 0.252 | 0.284 | 0.260 | 0.240 | 0.259 |
| marker-only, within-family centred (same solver) | 0.245 | 0.283 | 0.284 | 0.213 | 0.256 |
| haplotype-only | 0.172 | 0.187 | 0.209 | 0.145 | 0.178 |
| markers + haplotypes | 0.254 | 0.284 | 0.282 | 0.210 | 0.257 |

**Paired bootstrap** over families:
- combined − marker-only: −0.005 [−0.023, +0.013].
- haplotype-only − marker-only: −0.075 [−0.101, −0.046].
- Families with both parents seen: combined 0.288 vs 0.277, only 66 families, not significant.
- Tuning mostly chose the coarsest bins (20 cM) and the strongest penalty, i.e. it switched the haplotype block down.

**Why it doesn't help.** Within a family, a marker dosage already *is* the parental-origin signal. The marker model pools an allele's effect across every parent carrying it. The haplotype model pools only across families of the same parent, so it has less data per effect and ends up noisier.

**Verdict.** Linear rrBLUP on HMM genotypes stays the production model. Within-family centring of markers is not a reliable gain: +0.024 in C2 2006, −0.027 in C2 2007.

## Pipeline switched to HMM genotypes (default in `hackdata.load_geno` since 2026-09-26)

Results before the switch are kept in `cache/results/pre_hmm/`. Steps 2–5 were rerun (mean of 4 sets):

| | Provided imputation | HMM |
|---|---|---|
| Step 2 within-family r | 0.219 | **0.259** |
| Step 2 all-lines r, two-part model | 0.406 | **0.420** |
| Step 2 top-10% gain, bu/ac | 7.3 | **8.9** |
| Step 3 family r, parent-genomic (uses parent genotypes only) | 0.665 | 0.665 |
| Step 5, 10% plots, "spread", gain retained (GCA truth) | 127% | **141%** |
| Step 5, 10% plots, tilt τ=0.5 (GCA / testcross truth) | 126% / 111% | **138% / 118%** |

The ">100% retained" figures still include the half-location handicap of the field-selection baseline. The digital twin gives the unhandicapped number.

## Digital twin, Phase 2 — benchmark B: predicting crosses from parents (`61_cross_bench.py`)

197 families from 2006–07, scored with the January scores only.

| Prediction → observed | r |
|---|---|
| family mean → family mean | **0.656** (0 parents seen: 0.714, n = 26) |
| σG → observed within-family genetic SD | 0.205 (right level: median 5.1 vs 5.5; too narrow: SD 1.3 vs 1.9) |
| usefulness (mean + i·σG·r_g) → realized top-10% value | 0.647, vs 0.655 for the mean alone: **no gain** (−0.008 [−0.018, +0.001]) |

**Verdict.** Family means extrapolate well to new crosses. Family-specific spread does not, so cross planning ranks crosses by predicted mean and shows σG only as a low-confidence indicator. In the twin, family spread comes from simulated segregation of the true effects, not from this predictor.

## Digital twin, Phase 3 — field layer, calibration and validation (`native/reml_varcomp.jl`, `62`/`63`/`68`)

**REML variance components** (MixedModels.jl, plots 2004–05, about 180k per cluster, fitted in 31–48 min), variance and (SD):

| Cluster | Location-year | Family × location | Tester | SET | Family | Line | Residual |
|---|---|---|---|---|---|---|---|
| C1 | 605 | **140** (11.8) | 34 | 29 | 10 (3.2) | 38 (6.1) | 272 (16.5) |
| C2 | 687 | **189** (13.7) | 29 | 22 | 27 (5.2) | 28 (5.3) | 275 (16.6) |

The trial component is estimated at 0: nearly every SET holds one family, so trial ≡ family × location. Family performance is dominated by family × location interaction, which is why family merit is hard to predict. The split between family (POP) and SET is not well identified.

**Calibration on 2004–05** chose φ = 0.2 (genetic share of the line component) and γ = 1 (SET variance treated as genetic), using a pre-registered distance on within-family r and family r:

| | Within r | Family r | Tester-controlled r |
|---|---|---|---|
| real 2004–05 | 0.198 | 0.438 | 0.316 |
| twin (φ 0.2, γ 1) | 0.178 | 0.285 | 0.181 |

**Validation on 2006–07:**

| | Within r | Family r | Tester-controlled r | σG r | Median H |
|---|---|---|---|---|---|
| real | 0.259 | 0.654 | 0.282 | 0.223 | 0.48 |
| twin φ 0.2 (chosen) | 0.171 | 0.522 | 0.279 | 0.184 | 0.43 |
| twin φ 0.4 | 0.268 | 0.546 | 0.343 | 0.394 | 0.42 |

The twin matches family-level behaviour and data scales. Its within-family accuracy is only right at φ ≈ 0.4, and it did not reproduce the rise in real accuracy from 2004–05 to 2006–07.

**True-merit grading** (twin only; full-location field stage). At 10% of plots, every DNA-based strategy gives **1.7–2.6× the true genetic gain of planting everything** and selecting on field yield. This holds in every twin world tried (φ 0.2–0.4, γ 0–1). In all of these worlds, concentrating on the top predicted lines ranks first.

**Protocol check.** Inside the twin, the observed-yield half-location protocol used by `50_allocation.py` compresses all strategies to 0.81–0.88, which hides the 2× true advantage. Observed yield also rewards persistent non-heritable line effects, so the "plant everything" baseline looks better than it really is.

## Augmentation test — does the twin help? (`67_augmentation_test.py`) — **No**

Everything is trained on years < Y and scored on **real** 2006–07.

| | A0 real only | A1 + twin data, w 0.25 / 1 | A2 + model-seeded data, w 0.25 / 1 |
|---|---|---|---|
| within-family r | **0.259** | 0.250 / 0.220 | 0.260 / 0.239 |
| family testcross r | **0.665** | 0.545 | 0.573 |
| tester-controlled family r | **0.258** | 0.152 | 0.206 |
| allocation, spread / tilt 0.5 at 10% of plots | 1.41 / 1.38 | 1.35 / 1.32 (w 0.25) | 1.41 / 1.41 (w 0.25) |

**A3: strategy chosen per budget** from the twin (true merit) vs from the real 2004–05 replay, then graded on real 2006–07 (bu/ac):

| Budget | Real-2004–05 choice → gain | Twin choice → gain | Best possible |
|---|---|---|---|
| 10% | tilt τ=1 → **5.17** | concentrate → 3.10 | 5.41 |
| 25% | tilt τ=2 → **4.96** | concentrate → 3.85 | 5.40 |
| 50% | tilt τ=2 → **4.46** | tilt τ=1 → 4.44 | 4.99 |
| 75% | tilt τ=2 → **4.34** | capped → 4.06 | 4.42 |

**Verdict.**
- **Adding simulated yields hurts predictions**, and more weight hurts more. Model-seeded data is at best neutral.
- **Twin-guided strategy choice is worse** than choosing from earlier real seasons.
- **So the twin is not used to train models or to pick strategies.** Its defensible uses are:
  - showing that DNA preselection beats phenotype-only selection on true merit (robust in every world);
  - diagnosing evaluation protocols;
  - "what-if" illustration, clearly labelled.

**Recommended decision rule.** Choose the allocation strategy on the most recent real seasons, replayed forward. For 2008, use the 2004–07 replay. On 2006–07 this rule came within 5–10% of the best possible choice at every budget, and it picked a moderate tilt (τ 1–2), not either extreme.

## Twin Phase 4 — exploratory scenarios (illustration only; the twin failed the decision test above)

**Sensitivity and genotyping density.** 2006–07 within-family r in twin worlds:

| World | Within-family r |
|---|---|
| chosen world (φ 0.2) | 0.171 |
| + 70 markers per line (≈ 2× density) | 0.188 |
| + 210 markers per line (≈ 4× density) | 0.197 |
| causal genes on the chip | 0.202 |
| φ 0.9 | 0.424 |

Denser genotyping has diminishing returns: about +15% for 4× the markers.

**2008 bands.** 8 simulated 2008 seasons on the real 2008 crosses and plot design, true gain in bu/ac, mean and [P10, P90]:

| Strategy | 10% of plots | 25% of plots |
|---|---|---|
| tilt τ = 2 | 4.29 [3.62, 5.26] | 4.07 [3.42, 5.13] |
| tilt τ = 1 | 4.13 [3.59, 4.98] | 3.96 [3.37, 4.92] |
| spread | 3.11 [2.85, 3.29] | 3.09 [2.69, 3.51] |
| parent history | 2.15 [0.96, 3.58] | 2.83 [1.81, 4.34] |
| plant everything | 2.25 [1.77, 2.89] | — |
| random | 0.83 | 1.54 |

**Full REML fit on all plots ≤ 2005** (C1 3.1 h, C2 1.8 h) vs the 2004–05 fit:

| | C1 2004–05 | C1 ≤ 2005 | C2 2004–05 | C2 ≤ 2005 |
|---|---|---|---|---|
| family (POP) | 10.4 | **40.1** | 27.4 | 26.6 |
| experiment (SETY) | 28.7 | **0.0** | 22.3 | 19.2 |
| **POP + SETY** | **39.1** | **40.1** | **49.7** | **45.8** |
| family × location / trial | 140 / 0 | 59 / 80 | 189 / 0 | 159 / 0 |
| line | 37.6 | 32.5 | 28.2 | 26.2 |
| residual | 272 | 263 | 275 | 258 |

- **The POP/SETY split is not identified**, because nearly every SET holds one family: with more years, C1 moves the whole family-level variance from SETY to POP, while the sum is stable. The trial vs family × location split behaves the same way.
- The full fit supports the twin's calibrated γ = 1 (SETY variance treated as genetic family merit).
- The line and residual components are stable across both fits.

## Budget ablation — what share of plots is best? (`69_budget_ablation.py`, figure `cache/results/figs/budget_ablation.png`)

**Setup.** The real forward replay on 2004–07: 8 cluster-year sets, 100 replicates each, GCA truth, field stage advancing the top 5%. Planting everything gives **4.46 bu/ac**.

Realized gain, bu/ac:

| Budget | tilt τ=0.5 | tilt τ=1 | tilt τ=2 | family-capped | spread | parent history | random |
|---|---|---|---|---|---|---|---|
| 5% | 3.86 | 4.02 | 4.03 | 4.08 | 3.61 | 0.44 | −0.02 |
| 7.5% | 5.03 | 5.03 | 5.02 | 5.07 | 4.86 | 1.61 | 1.71 |
| 10% | 5.36 | 5.39 | 5.36 | 5.36 | 5.25 | 2.11 | 2.36 |
| 15% | **5.60** | 5.58 | 5.53 | 5.46 | 5.59 | 2.69 | 2.93 |
| 20% | **5.63** | 5.58 | 5.53 | 5.53 | 5.62 | 3.07 | 3.26 |
| 25% | 5.58 | 5.48 | 5.46 | 5.43 | 5.61 | 3.39 | 3.47 |
| 50% | 5.17 | 5.10 | 5.14 | 4.88 | 5.30 | 4.18 | 4.08 |
| 100% | 4.46 | 4.46 | 4.46 | 4.46 | 4.46 | 4.46 | 4.46 |

**Shape of the curve.**
- **Steep rise from 5% to 10%.** At 5%, the field stage has no choice left: it plants exactly the lines it advances.
- **Plateau from 15% to 25%**, with the maximum at 15–20%.
- **Slow decline above 25%.** With more lines planted, noisy field phenotypes increasingly override the DNA pre-screen.

**Picks.**
- Pre-registered pick (smallest budget tied with the maximum, 0.25 bu/ac tolerance): **10%**.
- Maximum gain: **15–20%**.
- Gain per plot: best at 5–7.5%.

**Exploratory twin (true merit).** The peak is at 7.5–10% in both twin worlds, with the same shape.

**Recommendation.** Use **15% of plots with tilt τ = 0.5–1**. That gives 5.60 bu/ac, within 0.03 of the maximum, saves 85% of plots, and beats planting everything by +26%.
- If plots are very scarce, use **10%**: −0.25 bu/ac (−5%), and it saves 90% of plots.
- Planting more than 25% costs plots *and* gain.

**Implication.** The gain falls above 25% only because the field stage ranks on phenotype alone. A field-stage index combining phenotype and DNA prediction would remove the penalty for extra plots. That's a clear next improvement.

## FINAL — 2008, evaluated once (`90_final_2008.py`, `final_2008/`)

**Decision (sealed 2026-09-26 10:59, SHA-256 in `final_2008/SEAL.json`, before any 2008 outcome was read).**
- Budget: 15% of candidate lines per cluster.
- Strategy: tilt τ = 0.5, pre-registered as the best at 15% in the 2004–07 replay.
- Result: advance **2,395 of 15,968 lines** from 154 of 157 families.
- Every line carries a reason: family rank on predicted GCA, sibling rank by DNA, parents seen, confidence tier. Of the advanced lines, 25–34% are high-confidence and 12–14% low-confidence.

**Prediction accuracy on 2008.**

| | C1 | C2 | Validation expectation |
|---|---|---|---|
| family testcross r | 0.609 | 0.697 | ~0.65 |
| within-family r | 0.161 | 0.195 | ~0.26 (2004–05: 0.20) |
| tester-controlled family r | 0.085 | 0.320 | ~0.28 |
| 80% interval coverage | 0.70 | 0.80 | ~0.70 |

**Decision outcome.**
- **The sealed list:** the advanced lines out-yielded the average candidate by +2.38 (C1) and +2.34 (C2) bu/ac on observed 2008 yield (tester- and location-adjusted, all locations).
- **2008 season replay** at 15% of plots (same protocol as validation):

| Strategy | Gain, bu/ac [P10, P90] | vs planting everything (4.74) |
|---|---|---|
| **tilt τ = 0.5 (sealed choice)** | **5.42 [4.79, 5.92]** | **1.14×** |
| spread | 5.37 | 1.13× |
| family-capped | 5.14 | 1.09× |
| concentrate | 4.21 | 0.89× |
| parent history (traditional) | 3.75 | 0.79× |
| random | 3.27 | 0.69× |

**Verdict.** The pre-registered strategy was the best option on the real 2008 season.
- It uses 15% of the plots, saving 85%, and delivers 14% more gain than testing every line.
- Traditional parent-history selection at the same budget would have lost 21% versus planting everything.
- Within-family accuracy was lower in 2008 than in 2006–07, so the margin (+14%) is smaller than the 2004–07 expectation (+26%). It is still clearly positive and best-in-class.

## External data beyond the dataset (organizers allowed it) — `native/external/fetch_*.R`, `external_features.py`, `71_env_external.py`

**Sources**, fetched natively in R with the clients in `additionial_data/` (env `hack-r`, `envs/r_data_clients.lock`). Only the trial-site coordinates were sent.

| Source | Coverage |
|---|---|
| NASA POWER daily weather 2000–08 | 414 / 414 sites with coordinates (18 sites have none) |
| NRCS SSURGO soil, 0–100 cm | 402 sites with a map unit, 393 with water-holding capacity |
| USDA NASS county corn-grain yields 1995–2008 | 49,507 county-years; 401 / 414 sites with county history (county lookup via the US Census geocoder) |

**Features.**
- Weather, by approximate crop stage (May–Jun, Jul, Aug–mid-Sep): GDD, rain, Hargreaves water deficit, solar radiation, Tmax/Tmin, VPD, heat degree-days > 32 °C, days > 35 °C.
- Soil: AWC, OM, clay, sand, Ksat, bulk density, pH, drainage class.
- NASS: county 5-year mean yield and 10-year trend, both from years *before* the season; same-season county yield is used in the hindcast only.
- **Forecast mode** uses climatology from earlier years + soil + NASS history, all available in January. **Hindcast** uses the actual season, which is post-planting information.

**A. Location-year yield level** (forward-year 2006–07, per cluster, mean of 4 sets):

| Model | r | RMSE | Coverage |
|---|---|---|---|
| location history (baseline) | 0.258 | 32.3 | 100% |
| provided monthly features + history | 0.224 | 34.8 | 91% |
| external weather + soil, forecast + history | 0.259 | 32.1 | 99.8% |
| external weather + soil, hindcast + history | 0.232 | 33.2 | 99.8% |
| **external forecast + NASS county history** | **0.338** | **29.8** | 99.8% |
| external hindcast + NASS (incl. same-season county yield) | 0.371 | 29.4 | 99.8% |

**B. Location-specific family ranking** (family × location model on family DNA × covariates, added to the broad ranking; within-location r vs broad 0.34):

| Covariates | Gain | Locations improved |
|---|---|---|
| provided | −0.004 | 55% |
| external hindcast | −0.021 | 41% |
| external forecast | −0.055 | 39% |
| external forecast + NASS | +0.015 (per set +0.09, +0.09, −0.04, −0.08) | 42% |

**Verdict.**
1. The external data is accessible and **better than the provided environment file**: 99.8% vs 91% coverage and higher accuracy.
2. **USDA NASS county yield history is the one source that clearly improves a January forecast** of location productivity: r 0.26 → 0.34, RMSE −8%. It is useful for site planning (e.g. the 36 new 2008 locations) and for the environment-specific framing.
3. **None of it improves line or family ranking.** Location-specific rankings do not reliably beat the broad-acre ranking. The advancement decision (broad-acre, DNA + pedigree) is unchanged, and the sealed 2008 result stands.
4. Actual-season weather adds little over climatology, and alone it overfits (r 0.07). Weather is not the lever for this problem.

## Combined field-stage index (`72_field_index.py`) — no gain

**What was tested.** At the field stage, rank planted lines by observed yield + λ × DNA prediction (gca) instead of observed yield alone. λ was tuned on the 2004–05 replay and validated on 2006–07.

**Tuning on 2004–05 chose λ = 0**, i.e. the current yield-only field stage. The gain of tilt τ=0.5, averaged over the 10–25% budgets:

| λ | 0 | 0.5 | 1 | 2 | 4 | 8 |
|---|---|---|---|---|---|---|
| gain, bu/ac | **5.86** | 5.85 | 5.84 | 5.78 | 5.57 | 5.10 |

**Validation on 2006–07.** λ = 0 is best at every budget from 7.5% to 75%, and gain falls steadily as λ grows. At 15%: 5.29 (λ 0) → 4.17 (λ 8).

**Only "plant everything" benefits.** Over 2004–07 it improves from 4.46 to 4.68 (λ 1–2, +5%). The 15% plan still beats this improved baseline by about 20% (5.60 vs 4.68).

**2008 post-hoc.** λ chosen on 2004–07 is also 0, so the result is identical to the sealed one (5.42 at 15%).

**Interpretation.** The plan already uses the DNA prediction when choosing what to plant. Re-using it at the field stage double-counts it and dilutes the only new information the field adds (the phenotype). The decline above 25% of plots is not caused by a yield-only field stage; it comes from the family-structured pre-selection itself. **The value is in *when* DNA is used (before planting), not only whether it is used.** `FIELD_INDEX_LAMBDA` stays at 0 (the default).

## Pushing accuracy further — three levers tested, then the ceiling measured

All levers were chosen on 2004–07 replays. 2008 was scored once, reported as post-hoc v2; the sealed v1 is unchanged.

| Lever | Validation 2006–07 | 2008 line r (v1 = 0.564) |
|---|---|---|
| free linear stack of 7 components (`73_stacking.py`) | line r 0.536 vs v1 0.561 (unstable, sign-flipping weights) | — |
| constrained family-level stack, NNLS (`76_stack_v2.py`) | 0.530 vs 0.561 | 0.565 |
| + climatology G × E (real January forecast) | 0.530 | 0.565 |
| + **actual 2008 weather G × E, assuming a perfect seasonal forecast** (`75_weather_gxe_component.py`) | 0.531 | **0.567** (weather weight 0.16 in C1, 0 in C2) |
| relatedness-weighted DNA training, parent-specific models blended (`74_related_training.py`) | within-family r +0.003 [−0.014, +0.016] | — |

The validation winner remains **v1**. Even perfect weather knowledge adds +0.003 line r on 2008.

**Accuracy ceiling.** The split-half reliability of the observed line values (half of each family's locations vs the other half, Spearman–Brown corrected to all locations) caps the correlation any predictor can reach:

| Season | C1 max r | C2 max r | Our r | Share of the ceiling |
|---|---|---|---|---|
| 2006 | 0.703 | 0.693 | | |
| 2007 | 0.647 | 0.633 | | |
| **2008** | **0.647** | **0.636** | 0.562 / 0.566 | **87% / 89%** |

**Consequences.**
- The sealed forecast is at about **88% of the maximum achievable accuracy**; the remaining headroom is about 0.07–0.08 r. It is limited by single-plot noise and large family × location interaction, not by the model.
- A 2008 line-level r well above about 0.65 cannot come from genuine prediction. It indicates noise-fitting or leakage of the answer key.

## Simulator, S1–S2: crop model + genomic G × E (`cropmodel.py`, `78_cropmodel_tests.py`, `79_maturity_gxe.py`)

**Crop model.** A daily maize model: thermal-time phenology for 115 RM, Beer's-law light capture, radiation-use efficiency 3.8 g/MJ, a 1 m soil-water bucket from SSURGO water-holding capacity, and a harvest index reduced by water and heat stress around silking.
- Driven by NASA POWER weather and made **irrigation-aware with USDA NASS county irrigated-corn share** (Census 1997/2002/2007; 44 trial sites are more than 50% irrigated).
- Simulated yield averages 202 bu/ac (observed about 195).
- No parameter was fitted to trial data.

Within-year correlation of the simulated yield with observed location-year means (2000–07, n = 1,188):

| Region | Rain-fed model | Irrigation-aware model |
|---|---|---|
| all | 0.135 | **0.331** |
| West (NE/KS/SD) | −0.005 | **0.321** |
| Corn Belt (IA, IL, …) | 0.24–0.29 | same |

**A. Site yield level**, forward 2006–07:

| Model | r | RMSE |
|---|---|---|
| location history | 0.258 | 32.3 |
| NASS + climatology (earlier best) | 0.338 | 29.8 |
| **crop model (January forecast: site mean over earlier seasons) + NASS** | **0.420** | **29.0** |
| crop model (perfect weather forecast) + NASS | 0.427 | 28.9 |

**B. Which family where**, crop-model covariates with a kernel G × E: gain −0.015 to −0.10. No improvement.

**Maturity × season G × E.**
- Family maturity (harvest grain moisture) predicted from the parents' DNA: **r 0.80–0.90**.
- One interaction per site covariate (season length, days to silk, latitude). It predicts family × location deviations with r 0.22–0.30, and its coefficients are consistent in sign in all 4 sets (later families lose at northern, short-season sites).
- Within-location ranking gain: +0.004 (forecast) / +0.017 (perfect weather), mixed across sets.

**Verdict.**
- The crop model is the first environmental model that clearly predicts **site productivity** (+63% over location history, January-legit).
- "Which line where" remains dominated by broad adaptation. The only consistent G × E is maturity × season length, and it is small but explainable.

## Simulator, S3 — "what to plant where", beyond 2008 (`simulator.py`, outputs in `cache/results/simulator/`)

**Scale.** 157 candidate families (2008) × 414 sites × **44 weather scenarios (NASA POWER 1981–2024)**, run in about 1 minute.

**Layers.**
- Crop model, irrigation-aware → site yield model (crop-model covariates + NASS county history, trained on real 2000–07 location-years).
- Family value F + T and line deviation D (January 2008 scores).
- Family maturity from the parents' DNA.
- Maturity × season G × E, fitted on 2000–07: coefficients for season length, days to silk and latitude are C1 [0.44, −0.86, −0.88] and C2 [0.11, −0.79, −0.58].

**Findings.**
- **Rankings.** Family rankings agree between states at Spearman **0.97 (C1) / 0.98 (C2)**, and the top-5 families by expected yield match the top-5 by bad-year P10 in almost every state. The elite families are broadly adapted.
- **Regional differences are mainly maturity.** Later families drop at northern, short-season sites; for example, C1.381 enters the top 5 in IA/IL and C1.427 in AR/GA/FL.
- **Site risk.**
  - Most variable sites (SD across weather years): MISD, IADO, MNPN, MNMY (SD 23–27 bu/ac).
  - Most reliable sites (highest P10): TXDA, TXDU, and the irrigated NEHD/NEFU (P10 210–221).

**Trust levels.**

| Part | Validation |
|---|---|
| line/family value | line r 0.56, family r 0.65 (2008) |
| maturity from DNA | r 0.80–0.90 |
| site yield level | r 0.42 (+63% over location history) |
| maturity G × E | consistent sign, small |
| location-specific family ranking | **no reliable gain**, so it is not claimed |

## More public environmental layers (`native/external/fetch_geo_layers.py`, env `hack-geo`; `82_geo_layers_test.py`)

**Fetched** (only site coordinates / county FIPS were sent):

| Layer | Coverage |
|---|---|
| gridMET daily 4 km 2000–08 (`pygridmet`) | 402 sites |
| USGS 3DEP elevation, slope, relief (`py3dep`) + NHDPlus stream distance, order, first-order count (`pynhd`) | 414 sites |
| U.S. Drought Monitor weekly county D0–D4 (REST API) | 283 counties |
| NOAA Storm Events hail / wind / flood / tornado by county-season (bulk CSV) | 2,520 county-years with events |
| MODIS 13Q1 250 m NDVI (Planetary Computer STAC) | in progress; ≥ 45% of location-years |

**Site yield level**, forward 2006–07, mean of 4 sets; base = crop model on NASA POWER + NASS:

| Configuration | Forecast r | Perfect r |
|---|---|---|
| base | **0.420** | **0.427** |
| crop model driven by gridMET instead of POWER | 0.403 | 0.405 |
| + terrain | 0.421 | 0.422 |
| + NDVI | 0.419 | 0.429 |
| + Drought Monitor | 0.409 | 0.423 |
| + NOAA storms | 0.415 | 0.411 |
| + all | 0.391 | 0.408 |

**Family ranking within location** (best covariate set): gain −0.026 (per set −0.05, −0.07, −0.09, +0.11).

**Verdict.**
- No layer improves beyond noise (±0.01), and all layers together overfit.
- The finer gridMET weather is worse than NASA POWER here, likely because site coordinates are rounded to about 1 km and 4 km rainfall is patchier at the cell level.
- **Not testable with this dataset:** the seed-production items (field layouts, male:female ratios, tassel / off-type detection, weed history) need private production-field records.

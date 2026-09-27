# Final write-up: what the hackathon asks for, what we found, and exactly how the model works

This document has three parts:
- **Part 1** explains, in simple terms, every insight the organizers expect in the submission, with our 2008 answer to each.
- **Part 2** is the technical model: every data point we use, how it is processed, and where it ends up in the output.
- **Part 3** traces each output back to its inputs.

Sources for the expectations:
- the track brief (`PRECISION_AGRICULTURE_HACKATHON_2026_TRACK1.pdf`);
- the Data Overview slides;
- the Hybrid Breeding course slides;
- the organizers' email ("go beyond the dataset").

Numbers come from forward-in-time validation: train on earlier seasons, predict the next one.
- 2008 was predicted from 2000–2007 data only.
- The decision was sealed with a SHA-256 hash before 2008 was opened, and 2008 was evaluated once.
- Numbers marked **post-hoc** were computed afterwards for the presentation (`92_posthoc_2008_extras.py`). Nothing was tuned on them.

C1 and C2 are the two gene pools (heterotic clusters); results are given as C1 / C2.

---

# Part 1 — The expected insights, in simple terms, with our 2008 answers

## A. The decision itself

### 1. Which lines to advance, and why
**What they want.** A specific list of 2008 lines to plant, with a reason a breeder can check for each one.

**Our answer.** **2,395 of 15,968 lines** (15% of the plots), coming from 154 of the 157 families. Every line has:
- a predicted value and an uncertainty;
- a confidence tier;
- a written reason, for example: "family ranked 6/71 on predicted GCA; #1 of 40 siblings by DNA; one parent tested before; confidence medium".

**Files:** `final_2008/advancement_list.csv`, with the full detail in `cache/results/report_2008/lines.csv`.

### 2. How to spend the reduced plots (resource allocation)
**What they want.** Not only who is best, but how to use a limited number of plots.

**Our answer.** Plant **15% of the lines**:
- **Families:** keep nearly every family, and give each family plots in proportion to its size, tilted toward families predicted to be good (tilt τ = 0.5). Inside each family, take the siblings with the best DNA scores.
- **Locations:** test every planted line at every location its family goes to.
- **Harvest:** advance the top 5% of lines on field yield.

**How the numbers were chosen.** A sweep over plot budgets on the real 2004–07 seasons showed gain peaks at 15–20% of plots.

**Lines vs locations.** Fewer lines at more locations beats more lines at fewer locations, at every budget. At equal cost it gives about **1.8×** the gain of testing every line at one location.

### 3. Usable in January 2008
**What they want.** A recommendation that could really have been made before planting.

**Our answer.**
- The pipeline's loaders only return data from before the forecast year, and 2008 results sit in a separate answer-key file.
- The decision was sealed with a SHA-256 hash of the scores before 2008 was opened.

## B. The predictions (the three challenge prompts)

### 4. Broad-acre performance (Challenge 1): the one that drives our recommendation
**What they want.** Predict how each line does on average across all environments, plus a measure of stability.

**2008 results:**

| Measure | C1 / C2 |
|---|---|
| Line accuracy (r) | **0.56 / 0.57** |
| Family accuracy (r) | **0.61 / 0.70** |
| True top-10% lines caught by our top 10% | **34%** (38% / 30%); random picking would catch 10% |

**Best achievable.** Half of the 2008 field data agrees with the other half only at r ≈ 0.64. So we reached **87–89% of what the noisy 2008 data allows**.

**Stability ⚠.** For every family we simulate performance at every site across 44 historical weather years (1981–2024), which gives an expected yield, a bad-year yield (P10) and a good-year yield (P90).
- **Post-hoc 2008:** this predicted stability did **not** match how much families actually varied across 2008 locations (r −0.01 to 0.35, near zero).
- **So:** present it as a scenario and risk tool, not as a validated stability measure.

### 5. Environment-specific performance (Challenge 2)
**What they want.** Location-specific forecasts and recommendations.

**Site yield forecast.** Each trial location's yield level is predicted from a crop model and county yield history.

| Forecast made | 2008 r (post-hoc) | 2003–07 average r |
|---|---|---|
| January | 0.25 | 0.35 |
| End of August | 0.35 | 0.45 |

On 2003–07 it beat plain location history (r 0.21) in 5 of 5 years.

**Family × location.** The simulator gives each family's expected yield and P10 at every site, and its best states.

**Why lines are still chosen broad-acre.** Location-specific line ranking (G×E models) was tested in every forward year and always lost to or tied the broad ranking (−0.03 to −0.10). Family rankings agree across states (Spearman 0.97–0.98). Environment-specific output is therefore used for site choice and risk, not for picking lines.

### 6. Multi-trait trade-offs (Challenge 3)
**What they want.** Balance yield against moisture (drying cost), test weight and lodging.

**What we predict.** Each family's harvest moisture and test weight are predicted from the parents' DNA.

| Trait | Post-hoc 2008 r (C1 / C2) |
|---|---|
| Moisture | **0.90 / 0.94** |
| Test weight | 0.57 / 0.59 |

**The trade-off in 2008 ⚠.** Compared with the average candidate, the lines we planted were:
- **+5.7 bu/ac** higher yielding;
- **+1.6 to 1.9 moisture points** wetter at harvest;
- −0.4 lb/bu in test weight.

Selecting on yield alone pulls in later-maturing lines, which is a real drying-cost trade-off.

**Tools provided:**
- a yield-vs-moisture Pareto flag per family;
- a simple index: family value minus a chosen number of bu/ac per point of moisture.

**Not done:** a full economic index with market prices and a lodging penalty.

### 7. Genomic prediction (a theme)
**What they want.** Use the DNA markers.

**Our answer.** DNA is central:
- **Families:** predicted from the parents' 2,911-marker genotypes.
- **Siblings:** ranked by a ridge regression on markers (rrBLUP).
- **Imputation:** a parent-aware HMM imputation recovers **76%** of hidden marker calls, against 58% and 52% for simpler methods. That raised within-family accuracy by 18%.

### 8. Genotype × environment interaction (a theme)
**What they want.** Show you understand that lines can rank differently in different places.

**Our answer.** We tested it directly:
- kernel G×E models;
- maturity × season-length interactions;
- weather-driven interactions, even assuming a perfect weather forecast.

None improved line ranking in forward tests. G×E exists, but with this data it can't be predicted well enough to change the decision.

### 9. Data integration, "multi-omics" (a theme)
**What they want.** One workflow from raw data to decision, combining phenotypes, genomics and environment.

**Our answer.** One pipeline from the raw CSV and zip files to the advancement list. It combines:
- field phenotypes, pedigree and DNA from the hackathon data;
- weather, soil and county statistics from public data;
- satellite imagery, tested separately.

## C. Validation and trust

### 10. Baselines
**What they want.** Compare with standard methods: phenotypic BLUP and environmental means.

**2008 comparison:**

| Measure | Ours | Traditional (parents' field record, phenotypic BLUP style) | Random 15% | Plant everything |
|---|---|---|---|---|
| Line r | **0.56 / 0.57** | 0.51 / 0.46 | — | — |
| Genetic gain of advanced lines (bu/ac) | **5.42** | 3.75 | 3.27 | 4.74 |

**Environmental means:** location history alone predicts site yield at r 0.21 (2003–07); the crop model + county history gives 0.35.

### 11. Validation suited to breeding
**What they want.** Test the way the model is used.

**Our answer:**
- Always **forward in time**: train on seasons before Y, predict new families in Y.
- A family's lines are never split between training and testing.
- The two gene pools are modelled separately.
- Every method was re-tested on each season 2003–2007, not only on one year.

### 12. Uncertainty
**What they want.** Confidence intervals for the predictions.

**Our answer.** Every line gets a standard deviation (median 11.5 bu/ac) and an 80% interval. Every family gets a probability of beating the average.

**Honest 2008 check ⚠:**

| Interval | Target coverage | 2008 coverage (C1 / C2) |
|---|---|---|
| Family 80% intervals | 80% | 70% / 80% |
| Line 80% intervals (post-hoc) | 80% | **68% / 73%** |

The line intervals are **too narrow**; the high-confidence tier in C1 covered only 54%. Widening them is a next step.

### 13. Missing data
**What they want.** How gaps are handled.

**Our answer:**
- **Genotypes:** progeny were measured at only 49–123 of 2,911 markers. The HMM rebuilds the rest from the two parents; this is the single most useful processing step.
- **Outliers:** plots more than 5 robust standard deviations from their family-trial median are removed. That is very few: 4 yield plots, 236 moisture plots and 65 test-weight plots, all under 0.03%.
- **Missing parents:** a parent with no field history is still predicted from its DNA.
- **New locations:** a location never used before is still forecast from weather, soil and county data.
- **Coverage:** all 2008 candidates were genotyped.

### 14. Failure modes
**What they want.** When does the model break?

**Our answer:**
- **Too little history.** In seasons with few known parents (2002–04), line r was only about 0.2.
  - One season ahead is reliable.
  - Two seasons ahead gives r 0.39, and three gives 0.20 (2005–07 average).
  - Retrain every season.
- **Novelty flag.** The confidence tier marks new parents and testers. **Post-hoc 2008 ⚠:** the tiers did not predict where errors were larger. Families with no parent seen before had *smaller* errors (6–7 bu/ac, on only 10–14 families) than those with one or two parents seen (8–11).
- **New environments.** In 2008, locations never used before were forecast no worse (r 0.32–0.43) than known ones (0.20–0.23), on small numbers.
- **Population shift.** Families unlike any tested before are the main risk. The DNA model softens it, because relatives' DNA carries information even when the parents themselves were never tested.

### 15. Accuracy, ranking and uncertainty in the results
Covered in points 4, 10 and 12.

## D. Commercial value

### 16. Intended users
- **Breeding program managers:** choose the budget and the risk level.
- **Population development teams:** plan next season's crosses from the ranked cross shortlist.
- **Field-testing coordinators:** allocate plots and locations.

### 17. Conservative vs aggressive selection
All at 15% of plots, 2008 season replay:

| Setting | Gain (bu/ac) | Bad-year P10 | vs plant everything |
|---|---|---|---|
| Conservative: even spread over families | 5.37 | 4.80 | 1.13× |
| **Recommended middle: tilt τ = 0.5** | **5.42** | 4.79 | **1.14×** |
| Aggressive: top predicted lines only | 4.21 | 3.31 | 0.89× |

Going aggressive loses 22% of the gain and has the worst bad-year outcome.

### 18. Cost and efficiency
- **74,361 of 87,286 plots saved** (85%).
- **7.7× the genetic gain per plot.**
- About **$11M** of plots at the course's ~$150 per plot per location. That cost is an assumption, not program data.

### 19. Computing needs
- A full season from raw files: **17.4 minutes** on a workstation.
- Judge mode: **9 seconds**.
- Linear models only, with no GPU or deep learning, so it runs on a laptop.

### 20. Scalability
- Each season is one more scoring run.
- The multi-year tool backtests any season and ranks future crosses.
- Two runnable packages and a local app are provided.

### The course's key question: "How good does the model need to be to skip the preliminary trial?"
**Answer: don't skip it, shrink it.**
- **DNA alone** (no field trial) delivered only **0.30×** the gain of planting everything in 2008, and 0.54× in the 2004–07 replay.
- **DNA to cut 85% of the lines, then field-test the rest** delivered **1.14×** in 2008 and 1.26× in the replay.

## E. Honesty about limits

### 21. Limitations
- **Sibling ranking is weak:** within-family r is 0.16–0.26, because siblings differ little and are measured on few plots.
- **Intervals and stability are overconfident** (points 4 and 12).
- **Moisture trade-off:** yield selection drifts toward later maturity (point 6).
- **2008 is the only true out-of-sample test.** Families are placed at locations non-randomly, and about 40% of 2008 locations hold a single family.
- **No economic index:** the multi-trait economic index is not finished.
- **Satellites don't help pick lines.** They help only as a mid-season site monitor.

### 22. Historical data may not represent the future
Accuracy decays when the newest data is older (point 14). The 2027 cross ranking is relative only; no genetic or climate trend after 2008 is modelled.

## F. Submission requirements

- **README (23):** `README_2008_PREDICTION.md` covers the seven deliverables. `SOLUTION_SUMMARY.md` is a summary, and `RESULTS.md` holds every experiment.
- **Judge mode (24):** `python judge_mode.py --budget 0.25` runs end to end on a 19 MB sample in about 10 seconds. The full pipeline is in `maize_advancement_package.zip`, and the app is in `maize_advisor_app.zip`.
- **Deliverables and slides (25):** everything above maps onto the seven deliverables. **The slide deck in the template is not made yet.**

---

# Part 2 — The technical model: every data point, how it is processed, where it goes

## The pipeline at a glance

```
RAW FILES ──► 00_prepare ──► 02b_geno_cluster ──► 10_build_dataset (stage 1) ──► 60 HMM imputation
                                                          │                              │
                                                          ▼                              ▼
                                              family table, line table        line genotypes (2,911 SNPs)
                                                          │                              │
                          ┌───────────────────────────────┼──────────────────────────────┘
                          ▼                               ▼
                 FAMILY MODELS (famodels.py)     WITHIN-FAMILY MODEL (gp.py)
                 pedigree ridge + parent-DNA     rrBLUP on markers -> D
                 ridge -> F (family), T (tester)
                          └───────────────┬───────────────┘
                                          ▼
                              LINE SCORE (40_score.py): testcross = F + T + D, GCA = F + D, SD, tier
                                          ▼
                              ALLOCATION (50/90): 15% of plots, tilt 0.5, advance top 5% at harvest
                                          ▼
                              OUTPUTS: advancement list, reasons, report, app

PUBLIC DATA ──► crop model (cropmodel.py) + county history ──► site yield forecast, simulator (stability, where)
```

## 2.1 Hackathon data points

### Plot records (`C1/C2_Phenotype_Data_V2.csv`, 1.07 million plots)
Each row is one plot: one line, crossed to one tester, grown at one location in one trial set in one year.

| Data point | How it is processed | Where it is used |
|---|---|---|
| **YLD** (yield, bu/ac): the main target | 1. **Outlier removal:** within each family × trial, plots more than 5 robust SDs from the median (median absolute deviation × 1.4826) are set to missing.<br>2. **Line deviation `y_w`:** each plot's yield minus its family's mean in the same trial (set × location × year), averaged over the line's trials. This is the clean within-family signal, because location and set effects cancel inside a trial.<br>3. **Family effect `pop_eff`:** family × location cell means are fitted by sparse least squares as location + cluster + family, with a tiny ridge so everything is identifiable. Families are compared through the locations they share, which is not the same as raw means. Effects are centred within cluster-year.<br>4. **Line total `y_tot`** = family effect + line deviation.<br>5. **Variance components per family** (one-way ANOVA across trials): line variance vL and error variance vE, which give heritability and reliability. | Training targets for every model; the truth for validation |
| **MST** (harvest moisture) | Same stage-1 steps | Family moisture prediction (Challenge 3), maturity × season G×E, multi-trait tests |
| **TWT** (test weight) | Same stage-1 steps | Family test weight prediction; multi-trait tests |
| **PHT / EHT** (plant and ear height), **RTLP / STLP** (root and stalk lodging) | Line deviations within half of each family's locations | Pre-harvest experiment only: DNA + height gives within-family r 0.184 vs 0.167 for DNA alone. Not used in the January decision. |
| **ERM** | Found to be derived from harvest moisture (median within-location r 0.92) | Not used |
| **YEAR** | Defines every training/testing split | All models are trained on seasons < Y |
| **LOC, SET → ENV and TRIAL** | ENV = location × year; TRIAL = set × location × year | ENV absorbs location effects in the family fit; TRIAL defines the within-trial line deviation |
| **LAT / LON** | Location coordinates, 1–2 decimals (±0.5–5 km) | Crop-model weather lookup, soil lookup, county matching, satellite windows |
| **LINE ID** | Normalized to `LINE_KEY` = family + line number without leading zeros. It keeps suffixes like `.1` / `#1` and drops the C2 float `.0`. | Matches 100% of phenotyped lines to genotypes; 154,033 unique lines. It fixed 667 lines that had been counted twice. |

### Pedigree and design (inside the phenotype files)

| Data point | How it is processed | Where it is used |
|---|---|---|
| **P1, P2** (parents) | Each parent's genetic share: F2 and doubled-haploid families 0.5 / 0.5; backcross families 0.75 for the recurrent parent and 0.25 for the donor | Pedigree family model (which parent was in which earlier family, and how those families did); parent-DNA profile; "parents seen before" count; the reason text |
| **RP** (recurrent parent) | Sets the 0.75 / 0.25 shares | As above |
| **GEN** (F2, BC, DH) | Sets the shares and how simulated progeny segregate | Family model; progeny simulator (predicted within-family spread, future crosses) |
| **TESTER** (the opposite-pool inbred each line is crossed to) | One-hot indicator in both family models, fitted jointly with the family part and then split off | The tester part **T** is reported but kept out of the ranking value (GCA), because the tester is not part of the line. "Tester seen before" feeds the confidence tier. |

### Genotypes

| Data point | How it is processed | Where it is used |
|---|---|---|
| **Parent genotypes:** 518 parents × 2,911 SNPs, coded −1 / 0 / +1 | Read from the parent rows of each family file; per-marker mean fill for rare gaps | **Parent-DNA family model:** each family is the share-weighted average of its parents' genotypes, and ridge regression learns marker effects for family value. Parents with no field history still get a value. Also the HMM imputation and the progeny simulator. |
| **Progeny genotypes:** 49–123 SNPs per line (unimputed) | **Parent-aware HMM** (`hmm.py`): along each chromosome, in genetic-map order, each line's hidden state is which parent a segment came from. Transitions come from the map distance (Haldane recombination), with a genotyping-error rate of 1%. The 2,911-marker genotype is then filled from the parents. | **Within-family model:** rrBLUP ridge regression of line deviations on the 2,911 imputed markers. The penalty is chosen on the previous season by median within-family r. **D** = calibrated slope × (the line's marker prediction minus its family's average). |
| **Provided imputed files** | Benchmarked against the HMM | Replaced: HMM 0.259 within-family r vs 0.219 |
| **Marker map** (chromosome, cM) | Order and distances along each chromosome | HMM transitions; progeny simulator; per-chromosome explanation of D |

### Environmental features (`environmental_features.csv`, provided)
Monthly weather and soil per location-year. Tested as a site-yield input and did worse than location history (−0.05 r), so it is **not used**. It is replaced by the public crop-model inputs below.

## 2.2 Public data points ("go beyond the dataset")

| Data point | How it is processed | Where it is used |
|---|---|---|
| **NASA POWER daily weather** (Tmax/Tmin, rain, solar radiation; 2000–08 and 1981–2024) | **Crop model** (`cropmodel.py`), one season per site:<br>1. Planting date from latitude.<br>2. Growing degree-days (base 10 °C, cap 30 °C): silking at 780, maturity at 1,500.<br>3. Leaf area and light capture (Beer's law, k = 0.65), biomass from radiation-use efficiency 3.8 g/MJ.<br>4. A 1 m soil-water bucket.<br>5. Kernel set cut by water stress and heat (> 35 °C) around silking; harvest index 0.5.<br>This produces simulated yield, water stress at flowering and in grain fill, heat days, season radiation and days to silk.<br>**January:** the site's average over earlier seasons. **In-season:** actual weather to the date, then typical weather for the rest. | **Site yield forecast** (ridge regression on the crop-model outputs + county history, trained on earlier location-years); the **simulator** (44 weather years → expected / P10 / P90 per family × site); the maturity × season G×E test |
| **SSURGO soil** (available water capacity) | Averaged over the root zone at each site | Size of the crop model's water bucket |
| **USDA NASS county corn yields** | 5-year mean and linear trend for the site's county, from years < Y | The strongest site-yield input (e.g. "county 5-year yield +15.8" in explanations) |
| **USDA NASS irrigated share** | County irrigated fraction | Blends the irrigated (no water stress) and rain-fed crop-model yields |
| gridMET, US Drought Monitor, NOAA storms, 3DEP terrain, NHDPlus streams | Site features in January and to date | Tested; neutral or slightly harmful, so **not used** |
| MODIS / Landsat / Sentinel-2 / NAIP / Sentinel-1 radar / thermal | Per-scene field or site statistics (NDVI, EVI, red-edge, backscatter, canopy temperature) | Satellite experiments 1–7: a mid-season site and field yield monitor (field r 0.29 → 0.59 by end of August when the field outline is known). **Not used for choosing lines.** |
| Genomes to Fields (G2F) 2014–23 | Planting and flowering dates; field corners; plot layout | Confirmed the crop model's phenology settings (no gain from recalibrating); test bed for field-level satellite forecasts |

## 2.3 Model steps in detail

1. **Family value F and tester part T** (`famodels.py`, averaged inside `40_score.family_block`):
   - **Pedigree model:** ridge regression of family effects on a parent-share matrix plus tester indicators, fitted on all earlier families.
   - **Parent-DNA model:** ridge regression on share-weighted parent marker profiles plus tester indicators.
   - **Tuning:** each model's penalties are chosen by fitting on seasons < Y−1 and scoring season Y−1.
   - **F and T:** the two models' family and tester parts are averaged.
   - **Calibration:** a slope from replaying the three previous seasons forward rescales F and T to the observed scale.
   - **Uncertainty SD_F:** the spread of replay errors, grouped by how many parents were seen before, with fewer seen never shown as more certain.
2. **Within-family deviation D** (`gp.py`): rrBLUP on the imputed markers, trained on every earlier line's within-family deviation. D is rescaled by a slope measured in the previous season.
3. **Uncertainty SD_D:** from the predicted within-family genetic spread of each cross. 200 progeny are simulated from the parents with recombination along the map, and the spread is scaled to match earlier families' observed spread.
4. **Line score:**
   - GCA = F + D, the ranking value.
   - Testcross = F + T + D.
   - SD = √(SD_F² + SD_D²), and the 80% interval is ±1.28 SD.
   - Tier: high if both parents and the tester were seen before, medium if one parent was seen, low otherwise.
5. **Allocation:**
   - Each family's plot quota = its size × 15% × w, with w = clip(1 + τ·z, 0, 3) rescaled so the total is 15%.
   - z is the family's standardized predicted value, and τ = 0.5.
   - Inside each family the lines with the highest D fill the quota.
   - At harvest the top 5% of all candidates on field yield advance.
6. **Evaluation (the replay):**
   - Each family's locations are split at random into a field half and a grading half.
   - The field stage selects on the field half, and the result is graded on the other half (tester-adjusted). This is repeated 100 times with a family bootstrap.
   - This avoids "picking and grading on the same noisy plots".
7. **Explanations** (`predict_report.py`). Because both family models are linear, each family's value splits exactly into:
   - a base;
   - parent 1's track record and parent 1's DNA;
   - parent 2's track record and parent 2's DNA.
   D splits exactly by chromosome. The script checks that the parts add up (error below 1e-6).
8. **Site forecast:**
   - Ridge regression on standardized crop-model outputs plus county yield history, trained on earlier location-years per gene pool.
   - The in-season version swaps in weather to date.
   - Each forecast is split into per-feature contributions.
9. **Simulator (stability, where):** the site forecast for each of 44 weather years, plus each family's value and a small maturity × season-length term. This gives expected / P10 / P90 per family per site and the best states.
10. **Future crosses** (`forecast.py future`): the family models score planned parent pairs, and the progeny simulator gives each cross's spread and best-5% line value. Validated on 2008 with crosses known and progeny simulated: family r 0.61 / 0.70.

---

# Part 3 — How each output traces back to its inputs

| Output (column or number) | Built from | Processing |
|---|---|---|
| **F (family value)** | Earlier families' effects (yield plots → stage 1), pedigree, parent genotypes | Two ridge regressions, averaged and calibrated |
| **F split: P1 / P2 track record and DNA** | Same as F | Exact linear split per parent |
| **T (tester part)** | Tester identity and earlier families with that tester | Tester indicator coefficients |
| **D (own DNA vs siblings)** | Earlier lines' within-family deviations, imputed line genotypes | rrBLUP ridge, minus the family average, times the slope |
| **D split by chromosome** | Same as D | Marker effects grouped by chromosome |
| **GCA, testcross** | F, T, D | GCA = F + D; testcross = F + T + D |
| **SD, 80% interval** | Replay errors by parents seen; simulated progeny spread | √(SD_F² + SD_D²), ±1.28 SD |
| **Tier** | Parents and tester seen in earlier seasons | Rule: high / medium / low |
| **Advance or plant flag** | GCA, F, D, family sizes, budget, τ | Tilted family quotas, best D within each family |
| **Reason text** | Family rank, sibling rank, parents seen, tier | Template sentence |
| **Predicted moisture and test weight** | Earlier families' moisture and test weight, parent genotypes | Parent-DNA ridge on each trait |
| **Pareto flag, index** | Predicted F and moisture | Non-dominated on (high yield, low moisture); index = F − weight × moisture |
| **Stability (expected, P10, P90, best states)** | 44 years of NASA POWER weather, soil, county history, F + T, predicted moisture | Crop model per weather year → site forecast + family value |
| **Site forecast (January to August)** | NASA POWER weather (climatology, then weather to date), SSURGO soil, NASS county yields and irrigation | Crop model → ridge regression |
| **Site drivers** | Same | Per-feature contribution = coefficient × standardized value |
| **Earliest best-prediction date** | Validation timeline (horizon test, in-season and pre-harvest experiments) | Family: at cross planning. Unplanted line: January. Planted line: late August (+ plant height), then harvest. Site: Aug 31. |
| **Expected gain and P10 per strategy** | Real replays of 2004–07 and the 2008 evaluation | Field half / grading half replay, 100 replicates |
| **Next-cross shortlist** | Everything through 2008, parent genotypes | Family models + progeny simulator; each parent used at most 3 times |

**Reproduce it:**
- **Run instructions:** see `README_2008_PREDICTION.md` and the packages `maize_advancement_package.zip` (full pipeline, 17 min from raw data) and `maize_advisor_app.zip` (the app).
- **Per-line explanations:** `python predict_report.py --year 2008`.
- **Post-hoc presentation numbers:** `python 92_posthoc_2008_extras.py`.

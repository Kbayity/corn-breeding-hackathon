# Corn Breeding Hackathon 2026 — Track 1

**Genomic Prediction for Maize Line Advancement Under Resource Constraints**

---

## Problem Statement

In January 2008, the maize breeding program faces a critical advancement decision under severe resource constraints. The 115 Relative Maturity Pipeline contains approximately 180,000 candidate lines organized across 998 biparental populations, with historical evaluation data spanning 2001 to 2007 comprising 515,000 phenotypic records. This is the initial screening stage of commercial maize breeding — the first gate where lines are evaluated for general combining ability before entering multi-location testing. In a typical season, roughly 15% of candidates — approximately 27,000 lines — would advance to the next stage based on field performance. The breeding team has the genomic data, the environmental characterization, and the phenotypic history needed to make informed advancement decisions. The infrastructure exists. The data exists. The decision-making framework is established.

But in January 2008, budget cuts reduced available field plots by 50%, and the breeding program manager must decide by Monday morning which lines to plant. Testing all 180,000 candidates is no longer possible — and testing the wrong 27,000 means wasting scarce field resources on suboptimal material while superior lines are delayed by a full breeding cycle. The biological complexity compounds the difficulty: general combining ability (GCA) — the additive genetic merit that predicts hybrid performance — is predictable from genomic data, but specific combining ability (SCA) arises from dominance and epistasis and remains a 100-year-old unsolved problem in quantitative genetics (Sprague & Tatum, 1942). Recent genomic prediction studies confirm that GCA prediction accuracies reach 0.49 to 0.55 when both inbred lines and testers are included in the model, while SCA prediction remains negative — worse than random. This means the breeder's target — GCA — is tractable, but only if the data are used correctly.

The stakeholder impact extends well beyond the breeding program manager. Purdue University research shows that product performance drives 80% of large-scale farmers' seed purchase decisions — far above price (13%) or supplier relationships (7%) (Castro, 2023). Farmers depend on a continued pipeline of improved hybrids, and the economics of getting selection right are substantial. A University of Nebraska-Lincoln study found that poor hybrid selection reduced profit by $173,580 per 1,000 acres, compared to just $3,750 for an average choice (Stockton, 2024) — a 46× difference between average and poor selection. The breeding company depends on efficient field testing and timely advancement to maintain competitive position; genetic gain compounds year over year, with modern corn hybrids gaining an average of 1.8 bu/A per year since 1930 (Butzen & Smith, Pioneer). When farmers like their crop's performance, more than 60% return to that brand and 56% recommend it (Purdue, 2023). At the system level, sustained genetic improvement in maize — the most widely grown crop in the United States — contributes directly to food security and agricultural productivity. A poor advancement decision at this initial screening stage affects the breeding cycle for an entire year, consuming scarce plots on suboptimal candidates while delaying superior lines from entering the testing pipeline.

Therefore we must rank candidate lines genomically before allocating field resources, using historical phenotype, genomic, and environmental data to predict which lines are most likely to perform well in 2008. The prediction task focuses on estimating additive genetic merit to support advancement decisions under severe resource constraints. This approach has direct commercial significance: field evaluation remains the most expensive component of variety development, and published benchmarks for public maize yield trials provide reference points. The University of Georgia charges approximately $1,000 per entry for eight grain tests, Kansas State University charges $150 per entry per location, and Ohio State grower trials charge $100 per hybrid for five entries. At the screening stage, commercial programs typically plant unreplicated plots at one to two locations before investing in replicated multi-location testing. The conventional approach — testing all candidates before selection — would require enormous field capacity that budget constraints have made unavailable. A prediction-enabled approach inverts this sequence: rank candidates genomically first, then allocate field resources only to the most promising material. Genomic selection offers the opportunity to predict GCA and hybrid performance from molecular marker information, enabling the total breeding cost to be reduced dramatically by phenotyping fewer multiple-location trials. The system must provide four outputs: a prediction of which lines are promising, a ranking of which lines should advance, a quantification of uncertainty for every recommendation, and a commercial interpretation that translates model output into actionable breeding decisions.

**Why This Matters Beyond 2008.** The 2008 budget crisis is a symptom of a much larger systemic issue. Climate volatility is making yield stability harder to maintain: a 2025 study in *Earth's Future* found that temperature and precipitation variability explain 28–33% of changes in major crop yield stability at the global scale (Zhu et al., 2025), and a 2024 study in *Frontiers in Agronomy* projects Iowa corn yield declines of 1.4–1.7% per year until mid-century if current trends continue (Zai et al., 2024). Breeding timelines compound the stakes: developing a new corn variety takes 7.5 years from cross to determination, and up to 10–15 years from initial cross to market introduction (USDA ERS). Every year of delay is a year of lost market position. And genotype-by-environment interaction — the fact that the same line performs differently across environments — remains the core biological challenge: a 2026 Springer chapter on genomic selection notes that G×E has persistently hindered the development of stable, high-performing cultivars, and that integrating genomic data with environmental covariates is one of the most promising strategies to address it (Alemu et al., 2026). This is precisely the approach our solution takes. As Corteva's own analysis puts it: "Genetics drive performance. Traits protect the genetics" (Corteva, 2025). Our job is to make sure the right genetics get selected — not just for 2008, but for every breeding cycle that follows.

---

## Deliverables Required

### 1. Problem Statement
*(Breeding decision context, stakeholder impact, commercial significance — see above)*

### 2. Solution Overview

One pipeline, raw hackathon files to advancement decision:

```
RAW FILES ──► outlier removal + within-family deviation + family effect (stage 1)
                            │                              │
                            ▼                              ▼
                   family/line tables            HMM-imputed line genotypes (2,911 SNPs)
                            │                              │
        ┌───────────────────┼──────────────────────────────┘
        ▼                   ▼
 FAMILY MODELS      WITHIN-FAMILY MODEL
 pedigree ridge +   rrBLUP on markers → D
 parent-DNA ridge → F, T
        └─────────┬─────────┘
                   ▼
      LINE SCORE: testcross = F+T+D, GCA = F+D, SD, confidence tier
                   ▼
      ALLOCATION: 15% of plots, tilt τ=0.5, advance top 5% at harvest
                   ▼
      OUTPUT: advancement list + written reason per line

PUBLIC DATA (NASA POWER weather, SSURGO soil, USDA NASS county yields)
      ──► site-yield forecast + simulator (site choice, risk — not line ranking)
```

Two runnable packages implement this: `pipeline/` (raw data → decision, ~17 min; judge mode ~2 min on a bundled sample) and `app/` (a Streamlit advisor app that ships with precomputed, forward-validated predictions and needs no raw data to run). `web/` is a standalone pitch website built on the real sealed 2008 decision — see [Run Instructions](#5-run-instructions).

### 3. Technical Approach

- **Family value (F):** two ridge regressions — a pedigree model (family effects on a parent-share matrix + tester indicators) and a parent-DNA model (share-weighted parent marker profiles + tester indicators) — each tuned on seasons < Y−1 and scored on Y−1, averaged and rescaled by a replay-calibrated slope.
- **Within-family deviation (D):** rrBLUP ridge regression on 2,911 markers per line. Progeny are genotyped at only 49–123 of those markers; a parent-aware HMM (Haldane recombination along the genetic map, 1% genotyping-error rate) imputes the rest, recovering 76% of hidden calls vs. 58%/52% for simpler methods — the single most useful processing step, raising within-family accuracy 18%.
- **Uncertainty:** SD from replay error grouped by how many parents were seen before, combined with simulated-progeny spread (200 simulated progeny per cross); 80% interval = ±1.28 SD. Confidence tier (high/medium/low) from whether both/one/no parents and the tester were seen before.
- **Allocation:** each family's plot quota = family size × 15% × a tilt weight (`clip(1 + τ·z, 0, 3)`, τ=0.5, z = standardized predicted family value), rescaled so the total is 15%; inside each family the best-DNA siblings fill the quota.
- **Validation, strictly forward in time:** train on seasons < Y, predict new families in Y only; a family's lines are never split between train and test; the two gene pools (C1/C2) are modeled separately; every method re-tested on each season 2003–2007. The reported gain replays each family's locations split into a field half (used to select) and a grading half (used to score), 100 bootstrap replicates — so nothing is picked and graded on the same plots.
- **Baselines beaten:** traditional parents'-field-record selection (line r 0.51/0.46 vs. ours 0.56/0.57; genetic gain 3.75 vs. our 5.42 bu/ac), environmental means, random selection, and planting everything.

### 4. Results

*(Full detail in `docs/RESULTS.md` and `docs/FINAL_WRITEUP.md`; headline numbers below are the sealed evaluation.)*

| Measure | Value |
|---|---|
| Lines advanced | 2,395 of 15,968 (15% of plots), from 154 of 157 families |
| Plots used / saved | 12,925 used, 74,361 saved (85%) |
| Line accuracy (r), C1 / C2 | 0.562 / 0.566 |
| Family accuracy (r), C1 / C2 | 0.609 / 0.697 |
| Genetic gain, our plan vs. planting everything | 5.42 vs. 4.74 bu/ac (**+14%**) |
| Genetic gain vs. traditional parent-record selection | 5.42 vs. 3.75 bu/ac (**+45%**) |
| Genetic gain per plot vs. planting everything | **7.7×** |
| Plot cost saved (at $150/plot, assumed) | **~$11M** |
| Share of the data's own noise ceiling reached | 87% (C1) / 89% (C2) |
| True top-10% lines caught by our top 10% (random = 10%) | 38% (C1) |

Reproducibility: the app, `predict_report.py`, and the packaged pipeline each reproduce the sealed 2,395-line list exactly. The decision was locked with a SHA-256 hash before the 2008 results were opened, and 2008 was evaluated once.

### 5. Run Instructions

**Judge mode** — full pipeline on a bundled sample (well under 2 minutes):
```bash
cd pipeline
MAIZE_DATA="sample_data/Simplified Hackathon Dataset V3" MAIZE_CACHE=cache_judge \
  MAIZE_OUT=outputs_judge python3 judge_mode.py
# writes outputs_judge/judge_mode_output.csv
```

**Full pipeline** (raw data → decision, ~17.4 min): same scripts in `pipeline/`, run against the complete hackathon dataset (not bundled here for size — see the organizers' data drop).

**Demo app** (no raw data needed — ships with precomputed, forward-validated predictions):
```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd app && streamlit run app.py   # open http://localhost:8501
```

**Pitch website** (real sealed-decision data, interactive):
```bash
cd web
npm install
npm run dev   # open http://localhost:3000
```
Live: see the deployed link in `web/README.md` if present, or ask the team.

### 6. Commercial Recommendations

Plant the 2,395 lines in `app/final_2008/advancement_list.csv` — 15% of plots, tilt τ=0.5 strategy, frozen from the 2004–07 replay before 2008 was opened. Test every planted line at every location its family goes to (extra locations beat extra lines, ~1.8× the gain at equal cost); at harvest, advance the top 5% on field yield; plan next crosses from the shortlist in `pipeline`'s forecast output.

**Key insight:** don't skip the field trial, shrink it. DNA alone (no field test) delivers only 0.30× the gain of planting everything; using DNA to cut to 15% of lines, then field-testing those, delivers 1.14×.

**Intended users:** breeding program managers (budget/risk level), population development teams (next-cross shortlist), field-testing coordinators (plot/location allocation).

### 7. Constraints and Limitations

- **Sibling ranking is weak** (within-family r 0.16–0.20): siblings differ little and are measured on few plots. The family-level call carries the decision.
- **Intervals run overconfident:** 2008 line 80% intervals covered only 68–73%, not 80%; C1's high-confidence tier covered just 54% (C2 was 76%).
- **Yield selection drifts wetter:** planted lines are +1.6–1.9 moisture points wetter at harvest (later maturity) — a real drying-cost trade-off with no finished economic index yet.
- **2008 is the only true out-of-sample test:** one held-out season, and ~40% of its locations hold a single family — thin ground for some of these numbers.
- **Satellite imagery** helps as a mid-season site/field monitor, not for choosing which lines to plant.

## Data → Decision Framing

Raw plots, genotypes and pedigree → outlier removal, within-family deviation and family-effect fitting (stage 1) → HMM-imputed line genotypes (2,911 SNPs from 49–123 measured) → family models (pedigree ridge + parent-DNA ridge) and within-family rrBLUP → line score (GCA = F+D, testcross = F+T+D, SD, confidence tier) → tilted budget allocation (15% of plots, τ=0.5) → advancement list with a checkable, written reason per line. Separately, public weather/soil/county data drive a site-yield forecast and simulator used for location choice and risk framing — validated independently, and never used to re-rank which lines to plant (location-specific ranking was tested every forward year and never beat the broad ranking).

## Repository Structure

```
├── pipeline/    Full raw-data → decision pipeline (judge_mode.py, final_model.py, score_2008.py, ...)
│                Run judge mode against the bundled pipeline/sample_data/.
├── app/         Streamlit advisor app — Farmer / Advanced / Analytics panels, precomputed predictions,
│                no raw hackathon data required. final_2008/advancement_list.csv is the sealed decision.
├── web/         Next.js pitch website (splash, Farmer/Geneticist/Data-scientist/Story views),
│                built on the same real sealed 2008 data.
└── docs/        FINAL_WRITEUP.md (full technical write-up), RESULTS.md (every 2008 number, sealed
                 and post-hoc), INVENTORY.md.
```

## References

1. Sprague, G.F. & Tatum, L.A. (1942). General vs. specific combining ability in single crosses of corn. *Journal of the American Society of Agronomy*, 34(10), 923–932.
2. Castro, L.T.E. (2023). Farmers' Purchasing Behavior and Implications for Suppliers' Go-to-Market Strategies. *Purdue Center for Food and Agricultural Business*.
3. Stockton, M. (2024). Maximizing Profitability by Choosing the Right Corn Hybrid. *UNL Center for Agricultural Profitability*.
4. Butzen, S. & Smith, S. Corn Yield Gains Due to Genetic and Management Improvements. *Pioneer*.
5. Corteva Agriscience (2025). "Investing in Genetics."
6. Zhu et al. (2025). Climate Extremes and Crop Yield Stability in the U.S. Midwest. *Earth's Future*.
7. Zai, F.H., McSharry, P.E., & Hamers, H. (2024). Impact of climate change and genetic development on Iowa corn yield. *Frontiers in Agronomy*, 6:1339410.
8. USDA Economic Research Service. *Agricultural Resources and Environmental Indicators* (EIB-16).
9. Keno, T. et al. (2026). Inter-plot competition in hybrid maize multi-environment yield trials can reduce rate of genetic gain. *Theoretical and Applied Genetics*, 139(7), 174.
10. Alemu, A. et al. (2026). Genomic Selection Role to Mitigate G × E Interaction in Plant Breeding. In *Genotype x Environment Interactions and its Implications for Plant Breeding* (pp. 343–364). Springer Singapore.

---

## License

MIT License. See `LICENSE` for details.

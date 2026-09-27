# Inventory: data, research packages and models

Everything collected or built so far, with what each provides or uses and each model's best validated performance. Details and caveats are in `RESULTS.md`.

- **Validation notation:** "fwd 2006–07" means trained on years before Y and tested on Y = 2006 and 2007, per cluster (C1, C2), as a mean of 4 sets.
- **2008:** the one-time evaluation of the sealed forecast.

---

## 1. Provided datasets (`Simplified Hackathon Dataset V3/`)

| Dataset | Size | Data points |
|---|---|---|
| `C1_Phenotype_Data_V2.csv`, `C2_Phenotype_Data_V2.csv` | 536,936 + 535,340 plots; 2000–2008; 499 + 500 families; 154,033 unique lines | **Traits:** yield YLD_BE (4% missing), grain moisture MST (3%), test weight TWT (12%), relative maturity ERM (40%), stalk/root lodging (34–55%), plant/ear height (71–78%). **Design:** location, year, experiment (SET), line, family, parents (CROSS), generation (F2 / BC1 / DH / DH2), tester, lat/lon |
| `environmental_features.csv` | 1,184 location-years (85% of phenotyped) | Monthly Apr–Oct precipitation, mean temperature, dew-point counts (DP01, DP10), heating/cooling degree days; SoilGrids coarse fragments, clay, silt, sand, nitrogen, pH, SOC at 6 depths |
| `Unimputed_C1/C2_Genome_Data.zip` | 79,394 + 78,635 rows × 2,911 SNPs | Parents fully genotyped (98.8% called); progeny about 69 called SNPs each; genetic map (10 chromosomes, 1,825 cM) |
| `ImputedC1/C2Populations.zip` | 499 + 500 files | Progeny imputed to the 2,911 parental SNPs (12–14% still missing) |
| Docs | — | Data dictionary, data overview, scenario, track brief, data guide, breeding course slides, slide template |

## 2. External data (`additionial_data/` clients; fetched into `cache/external/`)

| Source (client) | Coverage | Data points |
|---|---|---|
| **NASA POWER** (`nasapower`, R) | 414 sites × daily 2000–2008 **and** 1981–2024 | T2M, T2M_MAX, T2M_MIN, precipitation, solar radiation, RH, dew point, wind |
| **NRCS SSURGO** (`soilDB`, R) | 402 sites with a map unit, 393 with AWC | 0–100 cm weighted available water capacity, organic matter, clay, sand, Ksat, bulk density, pH; dominant drainage class |
| **USDA NASS Quick Stats** (`rnassqs`, R; key in `~/.config/hackathon/nass_key`) | 49,507 county-years 1995–2008; 401 sites | County corn-grain yield (bu/ac) |
| **USDA NASS Census of Agriculture** (`rnassqs`) | 402 sites (44 are >50% irrigated) | County irrigated share of corn-for-grain area (1997, 2002, 2007) |
| **US Census geocoder** (HTTP) | 414 sites | Site → state/county FIPS |
| **gridMET** (`pygridmet`, Python, env `hack-geo`) | 402 sites × daily 2000–2008 (4 km) | Tmax, Tmin, precipitation, solar radiation, RH max/min, wind |
| **USGS 3DEP** (`py3dep`) | 414 sites | Elevation; slope and relief in a ~1 km box (30 m DEM) |
| **USGS NHDPlus** (`pynhd`) | 414 sites | Distance to nearest stream, max stream order, count of first-order streams within ~4 km |
| **U.S. Drought Monitor** (public REST API) | 283 counties × weekly 2000–2008 | % of county area in D0–D4 |
| **NOAA Storm Events** (bulk CSV) | 2,520 county-years with events (Apr–Oct 2000–2008) | Hail count and max size, thunderstorm/high wind, flood/flash flood/heavy rain, tornado |
| **MODIS 13Q1 NDVI** (`pystac-client` + Planetary Computer) | ~750 of 1,372 trial location-years so far (download in progress) | 16-day 250 m NDVI, monthly means May–Sep and seasonal peak in a ~2 km box |
| **PRISM** (`prism`, R) | client installed, endpoint verified | US gridded climate (not used) |
| **PHG v2** (Kotlin) | — | Pan-genome haplotype graph; needs physical-coordinate genotypes and reference assemblies (not usable with our marker IDs) |

## 2b. Derived data artifacts

| Artifact | Location | Content |
|---|---|---|
| Clean modelling tables | `cache/model/` (3.5 GB) | plots, stage-1 lines and families, candidates, environments, provided-imputation and **HMM** genotype matrices (`geno_hmm_*.npy`), haplotype inheritance shares (`hap_*.npz`), sealed 2008 holdout files |
| Line scores | `cache/results/scores_2004 … 2008.parquet/.csv` | GCA, testcross, F, T, D, SD, tier per candidate line (January information for each season) |
| Sealed 2008 decision | `Let's Win/final_2008/` | config, SHA-256 seal, advancement list (2,395 lines with reasons), all candidates, one-time evaluation, post-hoc extensions |
| Crop-model outputs | `cache/external/cropmodel_2000_2008.parquet` | per location-year: potential and water-limited yield, irrigation-aware simulated yield, stage water/heat stress, days to silk / maturity |
| Weather libraries | `cache/external/nasapower/` (2000–08), `nasapower_1981_2024/` (44 scenario years), `gridmet/` | daily weather per site |
| Site layers | `cache/external/{soil_ssurgo, terrain, loc_county, county_yield, county_irrigation, usdm_county_weekly, storms_county_year, ndvi_env, trial_envs, locations}.csv` | one row per site / county / location-year |
| Simulator outputs | `cache/results/simulator/` | site × scenario yields, family × site distributions (mean / P10 / P90), region recommendations, family best regions |
| Digital-twin worlds | `cache_twin/<name>/` (57 GB, 30+ worlds) | simulated genotypes, true merit, plots and pipeline outputs, same layout as the real cache |
| Native-benchmark splits and predictions | `cache/native/<CL>_<Y>/` | Arrow / float32 exports and R/Julia predictions (predA, predB) |
| Result tables and figures | `cache/results/*.csv`, `cache/results/figs/` | every benchmark in `RESULTS.md` (budget ablation, allocation trade-off, …) |
| Environment specs | `envs/` | `hack-r`, `hack-julia`, `hack-geo` specs, lock files, install scripts, clone commit locks |

## 3. Research packages (`research_tests/`, run natively; envs `hack-r`, `hack-julia`; geo clients in `hack-geo`)

| Package | Methods it provides | Benchmarked here (best result, same protocol) |
|---|---|---|
| **BGLR** (R) | Bayesian regression: BRR, BayesA/B/C, Bayesian LASSO, RKHS | Used as the RKHS engine for the nlkernel/SKM kernels (below) |
| **bigstatsr** (R) | Penalized regression on file-backed matrices | Elastic net / LASSO, within-family r **0.261** (fwd 2006–07) |
| **bWGR** (R/C++) | EM and MCMC whole-genome regression; multi-trait; multi-environment | emRR 0.253, emBC 0.249, emEN 0.238, emBB 0.233, emBL 0.223 (within-family r) |
| **VIGoR** (R) | Variational Bayes BL / EBL / BayesB / BayesC | EBL 0.238, BayesB 0.195 (within-family r) |
| **nlkernel** (R) | Gaussian, Laplacian, polynomial, Bessel kernels, PCA/KPCA, multi-kernel via BGLR | Family testcross r: PCA **0.637**, polynomial 0.619, GBLUP 0.617, Laplacian 0.603, Gaussian 0.597, Bessel 0.560 |
| **SKM** (R) | Sparse kernels (arc-cosine, Gaussian, …), ML wrappers, grouped CV | Arc-cosine kernel, family r 0.617 |
| **hibayes** (R) | Bayesian alphabet incl. BayesR, single-step | installed, not benchmarked |
| **sommer** (R) | REML mixed models with G × E covariance structures | installed, not benchmarked |
| **lme4GS** (R) | lme4 with genomic kernels | installed, not benchmarked |
| **MixedModels.jl** (Julia) | Fast REML for crossed random effects | Plot-level variance components for the digital twin (see §4.10) |
| **JWAS.jl** (Julia) | Bayesian multi-trait, single-step, neural-network mixed models | installed, not benchmarked |

## 4. Our models (`Let's Win/`)

### 4.1 Data layer — `10_build_dataset.py`, `stage1.py`, `hackdata.py`
- **Uses:** phenotypes, design, genotypes.
- **Provides:**
  - within-family line deviations `y_w`, family effects `pop_eff` (location-adjusted), line totals `y_tot`;
  - reliabilities and variance components;
  - a 2008 quarantine (loaders take `before=`).
- **Results:** 100% of phenotyped lines linked to genotypes. Line-mean heritability 0.45 (YLD), 0.70 (MST), 0.59 (TWT).

### 4.2 Genotype imputation — `hmm.py`, `60_imputation_bench.py`
- **Uses:** parent genotypes, genetic map, raw progeny calls, generation type.
- **Model:** parent-aware HMM (F2 4-state, BC/DH 2-state), numba.
- **Performance:** **75.7%** of hidden real calls recovered (flanking marker 57.7%, family mean 51.9%). Downstream within-family r **0.219 → 0.259 (+18%)**.

### 4.3 Within-family DNA model — `gp.py`, `20_gp_forward.py`
- **Uses:** HMM dosages (2,911 SNPs), `y_w`.
- **Model:** rrBLUP (ridge), λ by inner forward split.
- **Performance:** within-family r **0.259** (fwd 2006–07); 2008: 0.161 (C1), 0.195 (C2).

### 4.4 Family-mean models — `famodels.py`, `30_popmean_h2h.py`
- **Uses:** parents, BC contributions, tester, parent genotypes, historical family effects.
- **Performance** (testcross r, fwd 2006–07):

| Model | r |
|---|---|
| parent-genomic ridge | **0.665** |
| pedigree GCA ridge | 0.569 |
| tester history | 0.520 |
| parent history | 0.383 |

Tester-controlled r is about 0.24–0.27 for all of them. On 2008 the family r was **0.609 / 0.697**.

### 4.5 Line scores — `40_score.py`
- **Uses:** 4.3 + 4.4, calibration from 3 replayed seasons, simulated progeny spread.
- **Provides:** GCA, testcross, SD, confidence tier per line.
- **Performance, 2008 (sealed):**
  - line-level r **0.562 / 0.566**;
  - top-15% hit rate 0.43 / 0.41 (random 0.15);
  - 80% interval coverage 0.70 / 0.80.
- **Ceiling:** the split-half reliability of observed 2008 line values caps any predictor at r 0.647 / 0.636, so the scores reach **87–89% of the achievable accuracy**.

### 4.6 Plot allocation — `50_allocation.py`, `69_budget_ablation.py`, `90_final_2008.py`
- **Uses:** line scores, plot design.
- **Strategies:** spread, tilt τ, family-capped, concentrate, parent history, random; budget sweep 5–100%.
- **Performance:**
  - Best budget **15%**, strategy tilt τ = 0.5.
  - 2004–07 replay: 5.60 bu/ac vs 4.46 for planting everything.
  - **2008 (sealed):** 5.42 vs 4.74 (+14%); **74,361 of 87,286 plots saved (85%)**; 7.7× gain per plot. Parent history at the same budget: 3.75.

### 4.7 Nonlinear kernels (Python) — `70_kernel_bench.py`
- **Uses:** parent profiles (family) or HMM dosages (lines, Nyström).
- **Performance:**
  - Family: linear 0.669, Bessel 0.668, Gaussian 0.664.
  - Lines: polynomial 0.258, Gaussian 0.256, Bessel 0.253, Laplacian 0.243 (linear exact 0.259).

### 4.8 Parent-haplotype (segment GCA) model — `65_haplotype_features.py`, `66_haplotype_gp.py`
- **Uses:** HMM ancestry per 5/10/20 cM bin × parent.
- **Performance:** markers + haplotypes 0.257, haplotypes only 0.178 (within-family r).

### 4.9 Cross prediction — `61_cross_bench.py`
- **Uses:** parents only.
- **Performance:**
  - family mean r **0.656** (0.714 for families with no parent seen before);
  - σG r 0.205;
  - usefulness criterion no better than the family mean.

### 4.10 Digital twin — `twin.py`, `62`–`64`, `68_twin_pipeline.py`, `native/reml_varcomp.jl`
- **Uses:** real crosses, plot design, marker panels and genotyping error; simulated progeny, true merit and plots.
- **REML variance components** (MixedModels.jl), e.g. C1 2004–05: location-year 605, family × location 140, tester 34, SET 29, family 10, line 38, residual 272.
- **Performance:**
  - Genotype layer matches real inheritance for F2/BC (ratios within 1 point, crossovers −7 to −9%, marker-correlation decay within 0.026).
  - Calibrated world: φ 0.2, γ 1.
  - 2006–07 check: within r 0.171 vs 0.259 real; tester-controlled family r 0.279 vs 0.282 real.
  - Truth-graded: DNA pre-selection gives 1.7–2.6× the true gain of phenotype-only selection.
  - **Augmentation** (training on twin data) lowers accuracy: within r 0.259 → 0.220–0.250.

### 4.11 External-data environment models — `external_features.py`, `71_env_external.py`
- **Uses:** NASA POWER stage covariates, SSURGO, NASS county history.
- **Performance** (site yield level r, fwd 2006–07):

| Model | r |
|---|---|
| location history | 0.258 |
| provided monthly features | 0.224 |
| external weather + soil | 0.259 |
| **+ NASS county history** | **0.338** |

Location-specific family ranking gain: +0.015 at best.

### 4.12 Crop model — `cropmodel.py`, `78_cropmodel_tests.py`
- **Uses:** daily weather, SSURGO AWC, NASS irrigated share, latitude-based planting date.
- **Model:** GDD phenology (115 RM), Beer's law, RUE 3.8 g/MJ, soil-water bucket, stress-dependent harvest index.
- **Performance:**
  - Within-year r with observed site means **0.331** (rain-fed version 0.135).
  - Site yield level, fwd 2006–07: **0.420** (January forecast), 0.427 (perfect weather).
  - G × E ranking: no gain.

### 4.13 Maturity × season G × E — `79_maturity_gxe.py`
- **Uses:** DNA-predicted family harvest moisture, crop-model season length, latitude.
- **Performance:**
  - maturity prediction r **0.80–0.90**;
  - interaction deviations r 0.22–0.30;
  - within-location ranking gain +0.004 (forecast) / +0.017 (perfect weather).

### 4.14 Other accuracy levers tested

| Lever | Script | Result |
|---|---|---|
| free linear stacking | `73_stacking.py` | line r 0.536 vs 0.561 |
| constrained NNLS stacking | `76_stack_v2.py` | 2008 0.565 vs 0.564 |
| + actual 2008 weather G × E (perfect forecast) | `75_weather_gxe_component.py` | 0.567 |
| relatedness-weighted DNA training | `74_related_training.py` | +0.003 |
| combined field-stage index | `72_field_index.py` | λ = 0 chosen (no gain) |

### 4.15 Simulator — `simulator.py`
- **Uses:** 4.3–4.5, 4.12, 4.13, NASS county history, 44 weather years (1981–2024).
- **Provides:** yield distributions (mean, P10, P90) per family × site; per-state recommendations (expected and robust); family best regions; site risk.
- **Result:** family-ranking agreement between states, Spearman 0.97 / 0.98.

### 4.16 Extra public environmental layers — `native/external/fetch_geo_layers.py`, `82_geo_layers_test.py`
- **Uses:** gridMET, 3DEP terrain, NHDPlus streams, Drought Monitor, NOAA storms, MODIS NDVI, added to the crop model + NASS.
- **Performance** (site yield r, fwd 2006–07; base 0.420 forecast / 0.427 perfect):

| Added layer | Forecast r | Perfect r |
|---|---|---|
| gridMET-driven crop model (instead of POWER) | 0.403 | 0.405 |
| + terrain | 0.421 | 0.422 |
| + NDVI (partial) | 0.419 | 0.429 |
| + Drought Monitor | 0.409 | 0.423 |
| + NOAA storms | 0.415 | 0.411 |
| + all layers | 0.391 | 0.408 |

- **Family ranking within location:** gain −0.026.

### 4.17 Judge mode — `judge_mode.py`, `make_judge_sample.py`
- **Uses:** a 19 MB bundled sample (202 historical + 12 new C1 families).
- **Performance:** runs in 9 s; within-family r 0.249; advanced lines +4.6 bu/ac vs the average candidate.

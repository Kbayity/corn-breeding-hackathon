# Maize advancement advisor — Streamlit app

A local web app for the 2008 maize line-advancement decision, with three panels:
- **Farmer view:** the plan in plain language.
- **Advanced:** your own data sources, budget, strategy, prediction date and custom crosses.
- **Analytics:** how each prediction changed as new data arrived.

This package holds the app code, the model modules it calls, and the precomputed, forward-validated prediction tables (36 MB). It needs **no raw hackathon data** to run.

## Run it (about 2 minutes)

Python 3.12 on Linux or macOS.

```bash
python -m venv .venv && source .venv/bin/activate      # or a conda env
pip install -r requirements.txt
cd app
streamlit run app.py
```

Open **http://localhost:8501**. Start it from inside `app/` so the dark theme in `app/.streamlit/config.toml` is applied. To reach it from another machine on the same network, use the Network URL Streamlit prints.

---

## What the app does

### 1. Farmer view (2008 plan)
- **Four highlights:**
  - **2,395 of 15,968 lines** to plant;
  - **5.42 bu/ac** genetic gain, **+14%** vs planting everything;
  - **74,361 plots saved** (85%);
  - **about $11M** saved at an assumed $150 per plot.
- **Charts:**
  - gain by approach: our plan vs planting everything vs the traditional parent record vs random;
  - a plots-used donut;
  - the families getting the most plots, coloured by predicted family value.
- **Actions:** the four steps to take this season, the next crosses to make, and a download of the advancement list.

### 2. Advanced
**Prediction date:**
- **Best prediction date** uses every trial season before the target year, all genotypes and pedigree, and that season's weather up to **31 August**. That is the earliest date at which the site forecast reaches its full-season accuracy. No later season is ever used.
- **Custom date** uses only what existed on that date:
  - a season's trials count from **1 November** of that season (after harvest);
  - in-season weather counts up to the date.
  - For example, 1 March 2007 → trials through 2006; 5 August 2008 → trials through 2007 plus weather to end of July.

**Data-source switches**, labelled **Hackathon** or **Public**:
- Hackathon: trial history + pedigree, parent DNA, line DNA, tester.
- Public: crop model (NASA POWER weather + SSURGO soil), county yields (USDA NASS), gridMET, Drought Monitor, storms, MODIS, Landsat.
- Genetic switches recompute the line predictions live. Environment switches select the closest validated site-forecast configuration.

**Custom inputs:**
- share of plots;
- strategy: recommended (keep every family, tilt toward predicted-good ones), conservative (even spread) or aggressive (top predicted lines only);
- tilt strength and cost per plot;
- a **custom cross**: any two parents, generation and tester. It is scored live in about 13 s with its evidence (each parent's earlier families, genotyped or not, tester history).

**Outputs:**
- lines and families kept, and plot cost saved;
- against the season's actual results (2008 marked **post-hoc**), each vs the traditional baseline:
  - value of the lines planted;
  - line accuracy;
  - true top-10% lines caught;
- the replay-validated field gain and bad-year risk (P10) for the chosen strategy and budget;
- the recommended lines, each with an explanation (family part from parents' record and parent DNA, own DNA vs siblings, tester);
- a site-forecast chart, predicted vs observed;
- a table of every data point used, tagged Hackathon / Public.

### 3. Analytics
- **A line or family:** its prediction at each date a new season of trials arrived (1 November of each season). It is split into family part vs own DNA, or parents' record vs parent DNA, with a table of what changed, e.g. "a parent was tested for the first time".
- **A location:** its forecast from January → end of June → July → August → full season, with and without MODIS NDVI, against the actual result.
- **Accuracy over time:** how accurate the forecasts were for all lines and all locations at each date in the chosen season.

### Checks
- **The app reproduces the sealed decision:** at default settings, it gives the sealed 2008 advancement list exactly and the 2008 accuracy (line r **0.562 / 0.566**, C1 / C2).
- **Every panel and control was tested headlessly** with Streamlit's test harness, with no errors.
- **2008 was evaluated once,** after the decision was sealed. Every 2008 comparison in the app is labelled post-hoc, and nothing is tuned on it.

### Limits
- **Coverage:** line and family predictions are precomputed for target seasons **2005–2008** and for data up to **3 seasons back**.
- **Calibration:** values at cutoffs other than the normal January one (1 season back) are not calibrated to bu/ac. Read them as relative.
- **Satellite:** site forecasts with satellite data exist only for the end of June, July and August.
- **Cost:** plot cost ($150) is an assumption from the course slides.

---

## Contents

| Path | What |
|---|---|
| `app/app.py`, `app/core.py` | The app (UI) and its data / logic layer |
| `app/precompute.py` | Rebuilds `cache/app/` from the full pipeline cache (about 40 min; needs the full project, not this package) |
| `app/.streamlit/config.toml` | Dark theme, colourblind-safe accent |
| `hackdata.py`, `famodels.py`, `gp.py`, `evalkit.py`, `50_allocation.py`, `paths.py` | Model modules used for live recomputation and custom crosses |
| `cache/app/` | Precomputed line and family predictions per season and data cutoff, marker effects, truth tables |
| `cache/results/` | Validated outputs:<br>- 2008 report (explanations)<br>- in-season site forecasts<br>- satellite site forecasts<br>- budget replay<br>- horizon test<br>- next-cross shortlist |
| `cache/model/pops.parquet`, `cache/exploration/` | Family table, parent genotypes and marker map (for custom crosses) |
| `final_2008/` | The sealed 2008 advancement list and its one evaluation |

`paths.py` is the packaged version: the cache is `./cache` next to it, overridable with `HACK_CACHE`.

# Maize Advancement Advisor — pitch website

Interactive site built on the real, sealed 2008 line-advancement decision (see `../docs/`
and `../app/final_2008/`). Splash → role picker (Farmer / Geneticist / Data scientist) →
a guided Story mode, all computed client-side from the real per-line/per-family data —
no backend, no mock numbers.

**Live:** https://web-kappa-kohl-39.vercel.app

## Run locally

```bash
npm install
npm run dev   # http://localhost:3000
```

## Regenerate the data file

`public/data/maize.json` and `public/data/advancement_list.csv` are generated from the
sealed pipeline outputs in `../app/`:

```bash
python3 scripts/export_data.py
```

## Structure

- `src/lib/` — ported allocation algorithm (`plan.ts`), geometry, and validated result tables
- `src/components/` — Splash, RoleSelect, Farmer/Geneticist/DataScientist/Story panels,
  the shared `FieldScene` kernel/plant visualization
- `scripts/export_data.py` — real-data export (see above)

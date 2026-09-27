#!/usr/bin/env python3
"""Export the real 2008 maize-advancement results into public/data/maize.json.

Source of truth: ../app (the sealed, forward-validated 2008 decision). Reads plain CSVs
only (stdlib csv+json, no pandas dependency).

Output shape (consumed by src/lib/data.ts):
  {
    cols: { f, rec, dna, d, t, cl, tier, sealed },   # one entry per line, len == n_lines
    fams: [ {pop, gen, p1, p2, seen, prob}, ... ],    # one entry per family, index == cols.f value
    sample: [ {i}, ... ],                              # ~320 kernels for the field/cob/helix visuals,
                                                          # grouped consecutively by family
    crosses: [ {cl, p1, p2, fam, best, prob}, ... ],     # next-cross shortlist
    reasons: { "<line index>": "<real written reason from the sealed advancement list>" },
  }

Also copies final_2008/advancement_list.csv verbatim to public/data/advancement_list.csv
so the site can offer a real download of the actual sealed deliverable.
"""
import csv
import json
import shutil
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent.parent / "app"
OUT = Path(__file__).resolve().parent.parent / "public" / "data" / "maize.json"
OUT_CSV = Path(__file__).resolve().parent.parent / "public" / "data" / "advancement_list.csv"

TIER = {"low": 0, "medium": 1, "high": 2}
CL = {"C1": 0, "C2": 1}
NK = 320  # target number of sample kernels for the visualizations


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    families = read_csv(SRC / "cache/results/report_2008/families.csv")
    lines = read_csv(SRC / "cache/results/report_2008/lines.csv")
    advancement = read_csv(SRC / "final_2008/advancement_list.csv")
    crosses_raw = read_csv(SRC / "cache/results/forecast/future_2027/crosses.csv")

    fam_order = [r["POP"] for r in families]
    fam_index = {pop: i for i, pop in enumerate(fam_order)}

    fams = [
        {
            "pop": r["POP"],
            "gen": r["GEN"],
            "p1": r["P1"],
            "p2": r["P2"],
            "seen": int(r["n_par_seen"]),
            "prob": round(float(r["prob_beats_average"]), 4),
        }
        for r in families
    ]

    sealed_keys = {r["LINE_KEY"] for r in advancement}
    reason_by_key = {r["LINE_KEY"]: r["reason"] for r in advancement}

    # sort lines by (family, rank_in_family) so the sample export can take a
    # contiguous, best-first slice per family
    lines.sort(key=lambda r: (fam_index[r["POP"]], int(r["rank_in_family"])))

    f_idx, rec, dna, d, t, cl, tier, sealed = [], [], [], [], [], [], [], []
    reasons = {}
    fam_lines = [[] for _ in fam_order]  # line row-index (post-sort) per family
    for i, r in enumerate(lines):
        j = fam_index[r["POP"]]
        f_idx.append(j)
        rec.append(round(float(r["F_P1_track_record"]) + float(r["F_P2_track_record"]), 4))
        dna.append(round(float(r["F_P1_dna"]) + float(r["F_P2_dna"]), 4))
        d.append(round(float(r["D"]), 4))
        t.append(round(float(r["T"]), 4))
        cl.append(CL[r["CL"]])
        tier.append(TIER[r["tier"]])
        sealed.append(r["LINE_KEY"] in sealed_keys)
        fam_lines[j].append(i)
        reason = reason_by_key.get(r["LINE_KEY"])
        if reason:
            reasons[i] = reason

    cols = {
        "f": f_idx, "rec": rec, "dna": dna, "d": d, "t": t,
        "cl": cl, "tier": tier, "sealed": sealed,
    }

    # --- sample[]: ~NK kernels for the field/cob/helix visuals, grouped
    # consecutively by family (largest-remainder rounding so counts sum to NK) ---
    n_total = len(lines)
    raw_quota = [max(1.0, NK * len(fam_lines[j]) / n_total) for j in range(len(fam_order))]
    base = [max(1, int(q)) for q in raw_quota]
    remainder = NK - sum(base)
    order = sorted(range(len(fam_order)), key=lambda j: -(raw_quota[j] - int(raw_quota[j])))
    k = 0
    while remainder > 0 and k < len(order):
        base[order[k]] += 1
        remainder -= 1
        k += 1
    while remainder < 0:
        # extremely unlikely (only if NK < number of families); trim from the largest
        biggest = max(range(len(base)), key=lambda j: base[j])
        if base[biggest] > 1:
            base[biggest] -= 1
            remainder += 1
        else:
            break

    sample = []
    for j in range(len(fam_order)):
        quota = min(base[j], len(fam_lines[j]))
        for k2 in range(quota):
            sample.append({"i": fam_lines[j][k2 % len(fam_lines[j])]})

    # --- crosses[]: next-cross shortlist ---
    crosses = [
        {
            "cl": r["CL"],
            "p1": r["P1"],
            "p2": r["P2"],
            "fam": round(float(r["family_gca"]), 2),
            "best": round(float(r["best5pct_line_gca"]), 2),
            "prob": round(float(r["prob_family_beats_avg"]), 4),
        }
        for r in crosses_raw
        if r["shortlist"] == "True"
    ]

    payload = {"cols": cols, "fams": fams, "sample": sample, "crosses": crosses, "reasons": reasons}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    shutil.copyfile(SRC / "final_2008/advancement_list.csv", OUT_CSV)

    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
    print(f"  lines: {n_total}, families: {len(fam_order)}, sealed: {sum(sealed)}, "
          f"sample: {len(sample)}, crosses: {len(crosses)}, reasons: {len(reasons)}")
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()

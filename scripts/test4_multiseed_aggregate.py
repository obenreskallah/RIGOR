"""
Test 4 — multi-seed aggregation of Test 3.

Accepts one Test 3 CSV (seed column, one row per seed) or several CSVs
(one per seed). Aggregates every (system, dataset, host, split) pair.

Usage:
    python test4_multiseed_aggregate.py \
        --inputs results/p1_vs_p2_results.csv \
        --out results/multiseed_stability.csv

Reports mean, std, and relative std (sigma_tilde, Bilot 2025b Eq. 3) for
precision_P1/P2, recall_P1/P2, and IF_empirical.
"""

import argparse
import csv
import statistics
import sys
from collections import defaultdict


NUMERIC_COLS = ["precision_P2", "recall_P2", "precision_P1", "recall_P1", "IF_empirical"]
KEY_COLS = ["system", "dataset", "host", "split"]


def load_csv(path):
    with open(path, "r", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", nargs="+", required=True,
                     help="P1/P2 CSV (one file with a seed column, or one file per seed)")
    ap.add_argument("--out", default="multiseed_stability.csv")
    args = ap.parse_args()

    if len(args.inputs) < 1:
        ap.error("provide at least one CSV")

    n_seed_hint = len(args.inputs)
    grouped = defaultdict(lambda: defaultdict(list))

    for path in args.inputs:
        rows = load_csv(path)
        n_seed_hint = max(n_seed_hint, len({r.get("seed", "") for r in rows if r.get("seed") not in (None, "")}) or 1)
        for row in rows:
            key = tuple(row[k] for k in KEY_COLS)
            for col in NUMERIC_COLS:
                val = row.get(col)
                if val not in (None, "", "None"):
                    grouped[key][col].append(float(val))

    if n_seed_hint < 3:
        print("[Test 4] WARNING: fewer than 3 seeds — std. dev. is not "
              "informative. This paper archives seeds 0/1/2 on every "
              "system×dataset pair, not CADETS only.",
              file=sys.stderr)

    out_rows = []
    for key, cols in grouped.items():
        row = dict(zip(KEY_COLS, key))
        row["n_seeds"] = max(len(v) for v in cols.values()) if cols else 0
        for col in NUMERIC_COLS:
            vals = cols.get(col, [])
            if len(vals) >= 2:
                mean_v = statistics.mean(vals)
                std_v = statistics.stdev(vals)
                row[f"{col}_mean"] = round(mean_v, 6)
                row[f"{col}_std"] = round(std_v, 6)
                row[f"{col}_sigma_tilde_pct"] = round((std_v / mean_v) * 100, 2) if mean_v else None
            elif len(vals) == 1:
                row[f"{col}_mean"] = round(vals[0], 6)
                row[f"{col}_std"] = None
                row[f"{col}_sigma_tilde_pct"] = None
            else:
                row[f"{col}_mean"] = None
                row[f"{col}_std"] = None
                row[f"{col}_sigma_tilde_pct"] = None
        out_rows.append(row)

    fieldnames = KEY_COLS + ["n_seeds"]
    for col in NUMERIC_COLS:
        fieldnames += [f"{col}_mean", f"{col}_std", f"{col}_sigma_tilde_pct"]

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print(f"[Test 4] Done ({len(args.inputs)} file(s) aggregated). "
          f"Results in {args.out}", file=sys.stderr)
    print("Note: precision_P2_sigma_tilde_pct is comparable to Figure 7 "
          "of Bilot 2025b (sigma_ADP).",
          file=sys.stderr)


if __name__ == "__main__":
    main()

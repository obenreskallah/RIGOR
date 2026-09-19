"""
Agregation multi-seed (Test 3 et Test 4).

Les seeds multiples s'appliquent a CHAQUE combinaison systeme x dataset du
scope, pas seulement a CADETS : sinon les autres hosts n'auraient qu'un
point (seed=0) et pas de barre d'erreur.

Accepte soit un CSV unique produit par test3_p1_vs_p2_postprocessing.py
(colonne seed, une ligne par seed), soit plusieurs CSV (un par seed).

Usage:
    python test4_multiseed_aggregate.py \
        --inputs results/p1_vs_p2_results.csv \
        --out results/multiseed_stability.csv

Calcule, pour chaque (system, dataset, host, split) : moyenne et ecart-type
de precision_P1, precision_P2, recall_P1, recall_P2, IF_empirical, et
sigma_tilde (Bilot2025b Eq. 3) sur precision_P2.
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
                     help="CSV P1/P2 (un fichier avec colonne seed, ou un fichier par seed)")
    ap.add_argument("--out", default="multiseed_stability.csv")
    args = ap.parse_args()

    if len(args.inputs) < 1:
        ap.error("fournir au moins un CSV")

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
        print("[Test 4] ATTENTION: moins de 3 seeds — l'écart-type n'est pas "
              "informatif. Le scope du papier vise seeds 0/1/2 sur CHAQUE "
              "combinaison système×dataset, pas seulement CADETS.",
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

    print(f"[Test 4] Termine ({len(args.inputs)} fichiers agreges). "
          f"Resultats dans {args.out}", file=sys.stderr)
    print("Rappel: sigma_tilde_pct sur precision_P2_sigma_tilde_pct est "
          "directement comparable a la Figure 7 de Bilot2025b (sigma_ADP).",
          file=sys.stderr)


if __name__ == "__main__":
    main()

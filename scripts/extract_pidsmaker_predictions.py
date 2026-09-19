"""Convert PIDSMaker results (results.pth / result_*.pth) to the CSV
node_id,predicted_label,score that Test 3 expects.

When given an evaluation directory, keeps the epoch with the best ADP.

Usage:
    python scripts/extract_pidsmaker_predictions.py \
        --eval-dir /path/to/artifacts/evaluation/evaluation/<hash>/CADETS_E3 \
        --out results/predictions/threatrace_CADETS_E3_seed0.csv

    python scripts/extract_pidsmaker_predictions.py \
        --pth /path/to/result_epoch_5.pth \
        --out results/predictions/threatrace_CADETS_E3_seed0.csv
"""

import argparse
import csv
from pathlib import Path


def _load_torch(path):
    import torch

    return torch.load(path, map_location="cpu", weights_only=False)


def pick_best_result_pth(eval_dir: Path) -> Path:
    pr_dir = eval_dir / "precision_recall_dir"
    if not pr_dir.is_dir():
        results = eval_dir / "results" / "results.pth"
        if results.exists():
            return results
        raise FileNotFoundError(f"No precision_recall_dir or results.pth in {eval_dir}")

    best_adp = float("-inf")
    best_path = None
    for stats_file in sorted(pr_dir.glob("stats_*.pth")):
        stats = _load_torch(stats_file)
        adp = float(stats.get("adp_score", float("-inf")))
        epoch_tag = stats_file.name.replace("stats_", "").replace(".pth", "")
        result_file = pr_dir / f"result_{epoch_tag}.pth"
        if result_file.exists() and adp >= best_adp:
            best_adp = adp
            best_path = result_file
    if best_path is None:
        raise FileNotFoundError(f"No result_*.pth in {pr_dir}")
    print(f"[extract] selected epoch (best ADP={best_adp}): {best_path}")
    return best_path


def results_to_rows(obj):
    rows = []
    if isinstance(obj, dict) and "y_preds" in obj and "nodes" in obj:
        for nid, y_hat, score in zip(obj["nodes"], obj["y_preds"], obj["pred_scores"]):
            rows.append((str(nid), int(y_hat), float(score)))
        return rows
    if isinstance(obj, dict):
        for nid, rec in obj.items():
            if not isinstance(rec, dict) or "y_hat" not in rec:
                continue
            rows.append((str(nid), int(rec["y_hat"]), float(rec.get("score", 0.0))))
        return rows
    raise TypeError(f"Unrecognized PIDSMaker format: {type(obj)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", help="Host folder (e.g. CADETS_E3) under artifacts/evaluation/")
    ap.add_argument("--pth", help="result_*.pth or results.pth file")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if bool(args.eval_dir) == bool(args.pth):
        raise SystemExit("Specify exactly one of --eval-dir or --pth")

    src = Path(args.pth) if args.pth else pick_best_result_pth(Path(args.eval_dir))
    rows = results_to_rows(_load_torch(src))
    if not rows:
        raise SystemExit(f"No predictions extracted from {src}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id", "predicted_label", "score"])
        w.writerows(rows)
    n_flagged = sum(1 for _, y, _ in rows if y == 1)
    print(f"[extract] {len(rows)} nodes, {n_flagged} flagged -> {out}")


if __name__ == "__main__":
    main()

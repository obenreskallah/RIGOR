"""
Test 3 — precision/recall under P1 (2-hop) vs P2 (strict node-level)
from the same raw per-node predictions.

IF = precision_P1 / precision_P2 on a single run.

- P2: a flagged node is a true positive iff it is itself in V_attack.
- P1 (precision): a flagged node is a true positive iff it is in V_attack
  or in the 2-hop neighbourhood of some node in V_attack.
- P1 (recall): an attack node is detected iff at least one flagged node
  lies in its 2-hop neighbourhood (or is itself).

Usage:
    python test3_p1_vs_p2_postprocessing.py --config datasets.json --out p1_vs_p2_results.csv

Each evaluated entry needs `path`, `ground_truth_path`, `predictions_path`,
and `system`. Predictions default to CSV `node_id,predicted_label[,score]`.
Optional top-level `"seeds"` with `{seed}` in `predictions_path` expands
one entry across seeds.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test1_graph_stats import resolve_path, paths_exist
from test2_prop2_geometric import build_adjacency, load_attack_nodes


def load_predictions(path: str):
    """Return the set of node IDs flagged malicious (already-thresholded labels)."""
    p = Path(path)
    flagged = set()
    with open(p, "r", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            node_id, label = row[0], row[1]
            if str(label) in ("1", "True", "true", "malicious"):
                flagged.add(node_id)
    return flagged


def expand_ground_truth_2hop(adj, attack_nodes):
    """Union of {v} ∪ N_2(v) over attack nodes (extended ground truth)."""
    expanded = set()
    for v in attack_nodes:
        if v not in adj:
            continue
        expanded.add(v)
        visited = {v}
        frontier = [v]
        for _hop in range(2):
            next_frontier = []
            for u in frontier:
                for w in adj.get(u, ()):
                    if w not in visited:
                        visited.add(w)
                        next_frontier.append(w)
            frontier = next_frontier
        expanded |= visited
    return expanded


def recall_p1_detected_count(adj, attack_nodes, flagged):
    """Attack nodes with ≥1 flagged node in their 2-hop neighbourhood (or themselves)."""
    detected = 0
    for v in attack_nodes:
        if v not in adj:
            continue
        if v in flagged:
            detected += 1
            continue
        visited = {v}
        frontier = [v]
        found = False
        for _hop in range(2):
            if found:
                break
            next_frontier = []
            for u in frontier:
                for w in adj.get(u, ()):
                    if w in flagged:
                        found = True
                        break
                    if w not in visited:
                        visited.add(w)
                        next_frontier.append(w)
                if found:
                    break
            frontier = next_frontier
        if found:
            detected += 1
    return detected


def compute_p1_p2(adj, attack_nodes_all, flagged):
    attack_in_graph = {v for v in attack_nodes_all if v in adj}
    flagged_in_graph = {v for v in flagged if v in adj}

    tp2 = flagged_in_graph & attack_in_graph
    fp2 = flagged_in_graph - attack_in_graph
    fn2 = attack_in_graph - flagged_in_graph
    precision_p2 = len(tp2) / len(flagged_in_graph) if flagged_in_graph else 0.0
    recall_p2 = len(tp2) / len(attack_in_graph) if attack_in_graph else 0.0

    expanded_gt = expand_ground_truth_2hop(adj, attack_in_graph)
    tp1_for_precision = flagged_in_graph & expanded_gt
    fp1 = flagged_in_graph - expanded_gt
    precision_p1 = len(tp1_for_precision) / len(flagged_in_graph) if flagged_in_graph else 0.0

    detected_p1 = recall_p1_detected_count(adj, attack_in_graph, flagged_in_graph)
    recall_p1 = detected_p1 / len(attack_in_graph) if attack_in_graph else 0.0

    return {
        "n_attack_nodes": len(attack_in_graph),
        "n_flagged": len(flagged_in_graph),
        "precision_P2": round(precision_p2, 6),
        "recall_P2": round(recall_p2, 6),
        "tp_P2": len(tp2), "fp_P2": len(fp2), "fn_P2": len(fn2),
        "precision_P1": round(precision_p1, 6),
        "recall_P1": round(recall_p1, 6),
        "fp_P1": len(fp1),
        "IF_empirical": round(precision_p1 / precision_p2, 3) if precision_p2 > 0 else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True,
                     help="datasets.json with path, ground_truth_path, "
                          "predictions_path, and system on each evaluated entry")
    ap.add_argument("--out", default="p1_vs_p2_results.csv")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    rows = []
    seeds = cfg.get("seeds") or []
    graph_cache = {}
    for entry in cfg["datasets"]:
        expanded = []
        pred_tmpl = entry.get("predictions_path") or ""
        if seeds and "{seed}" in pred_tmpl:
            for s in seeds:
                e = dict(entry)
                e["seed"] = s
                e["predictions_path"] = pred_tmpl.replace("{seed}", str(s))
                expanded.append(e)
        else:
            expanded.append(dict(entry))

        for item in expanded:
            pred_path = item.get("predictions_path")
            gt_path = item.get("ground_truth_path")
            if not pred_path or not gt_path:
                print(f"[Test 3] SKIP {item.get('system', '?')}/{item['dataset']}/{item['host']}: "
                      f"missing predictions_path or ground_truth_path.",
                      file=sys.stderr)
                continue

            edge_path = resolve_path(item["path"], args.config)
            gt_path = resolve_path(gt_path, args.config)
            pred_path = resolve_path(pred_path, args.config)
            seed = item.get("seed", "")
            label = f"{item.get('system')}/{item['dataset']}/{item['host']}"
            if seed != "":
                label += f"/seed{seed}"
            if not paths_exist(edge_path) or not paths_exist(gt_path) or not paths_exist(pred_path):
                print(f"[Test 3] SKIP {label}: missing file (edges/gt/predictions).",
                      file=sys.stderr)
                continue

            system = item.get("system", "unknown_system")
            print(f"[Test 3] {label} ...", file=sys.stderr)

            cache_key = (edge_path, gt_path)
            if cache_key not in graph_cache:
                adj, _n_edges = build_adjacency(edge_path)
                graph_cache[cache_key] = (adj, load_attack_nodes(gt_path))
            adj, attack_nodes = graph_cache[cache_key]
            flagged = load_predictions(pred_path)

            result = compute_p1_p2(adj, attack_nodes, flagged)
            row = {
                "system": system,
                "dataset": item["dataset"], "host": item["host"], "split": item["split"],
                "seed": seed,
                **result,
            }
            rows.append(row)
            print(f"  -> precision_P2={row['precision_P2']}  precision_P1={row['precision_P1']}  "
                  f"IF_empirical={row['IF_empirical']}", file=sys.stderr)

    fieldnames = ["system", "dataset", "host", "split", "seed", "n_attack_nodes", "n_flagged",
                  "precision_P2", "recall_P2", "tp_P2", "fp_P2", "fn_P2",
                  "precision_P1", "recall_P1", "fp_P1", "IF_empirical"]
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"\n[Test 3] Done. Results in {args.out}", file=sys.stderr)
    print("Note: compare IF_empirical to Test 1 ceiling_k_bar2 on the same "
          "dataset — empirical IF should be of similar order or below "
          "(Proposition 2 is an upper bound).",
          file=sys.stderr)


if __name__ == "__main__":
    main()

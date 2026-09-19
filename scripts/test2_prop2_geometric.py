"""
Test 2 — direct geometric check of Proposition 2 (no detector).

For each ground-truth attack node, measure |N_2(v*)| and compare it to
k_bar^2 and k_max^2. Requires the graph plus attack-node IDs
(`ground_truth_path` in datasets.json).

Usage:
    python test2_prop2_geometric.py --config datasets.json --out prop2_geometric.csv

Reuses `load_edges()` and `build_adjacency()` from test1_graph_stats.py —
adapt the loader there, not here.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test1_graph_stats import resolve_path, paths_exist, build_adjacency


def load_attack_nodes(path: str):
    """Malicious node IDs from a file, directory, or list of paths.

    Formats: JSON list; TXT one ID per line; CSV where the ID is the field
    before the first comma (do not use csv.reader — the second field is often
    a Python dict containing commas).
    """
    if isinstance(path, (list, tuple)):
        nodes = set()
        for p in path:
            nodes |= load_attack_nodes(p)
        return nodes

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Ground truth not found: {path}")

    if p.is_dir():
        nodes = set()
        for f in sorted(p.iterdir()):
            if f.suffix.lower() in {".csv", ".txt", ".json"} and not f.name.startswith("."):
                nodes |= load_attack_nodes(str(f))
        return nodes

    if p.suffix.lower() == ".json":
        with open(p) as f:
            return {str(x) for x in json.load(f)}

    nodes = set()
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            node_id = line.split(",", 1)[0].strip()
            if node_id:
                nodes.add(node_id)
    return nodes


def two_hop_neighborhood_size(adj, node):
    """|N_2(node)|: distinct nodes reachable in at most 2 hops, excluding `node`."""
    visited = {node}
    frontier = [node]
    for _hop in range(2):
        next_frontier = []
        for u in frontier:
            for v in adj.get(u, ()):
                if v not in visited:
                    visited.add(v)
                    next_frontier.append(v)
        frontier = next_frontier
    visited.discard(node)
    return len(visited)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="prop2_geometric.csv")
    ap.add_argument("--summary-out", default="prop2_geometric_summary.csv")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    per_node_rows = []
    summary_rows = []

    for entry in cfg["datasets"]:
        gt_path = entry.get("ground_truth_path")
        if not gt_path:
            print(f"[Test 2] SKIP {entry['dataset']}/{entry['host']}/{entry['split']}: "
                  f"no ground_truth_path in config", file=sys.stderr)
            continue

        edge_path = resolve_path(entry["path"], args.config)
        gt_path = resolve_path(gt_path, args.config)
        if not paths_exist(edge_path):
            print(f"[Test 2] SKIP {entry['dataset']}/{entry['host']}/{entry['split']}: "
                  f"edge file missing.",
                  file=sys.stderr)
            continue
        if not paths_exist(gt_path):
            print(f"[Test 2] SKIP {entry['dataset']}/{entry['host']}/{entry['split']}: "
                  f"ground truth missing ({gt_path})", file=sys.stderr)
            continue
        print(f"[Test 2] {entry['dataset']}/{entry['host']}/{entry['split']} ...", file=sys.stderr)
        adj, n_edges = build_adjacency(edge_path)
        attack_nodes = load_attack_nodes(gt_path)
        attack_nodes_in_graph = [n for n in attack_nodes if n in adj]
        missing = len(attack_nodes) - len(attack_nodes_in_graph)
        if missing:
            print(f"  [!] {missing} ground-truth attack nodes absent from the graph "
                  f"(check ID alignment between files)", file=sys.stderr)

        n2_sizes = []
        degrees = []
        for node in attack_nodes_in_graph:
            deg = len(adj.get(node, ()))
            n2 = two_hop_neighborhood_size(adj, node)
            degrees.append(deg)
            n2_sizes.append(n2)
            per_node_rows.append({
                "dataset": entry["dataset"], "host": entry["host"], "split": entry["split"],
                "node_id": node, "degree": deg, "n2_size": n2,
            })

        if not n2_sizes:
            print(f"  [!] No usable attack nodes, skipping summary.", file=sys.stderr)
            continue

        n_nodes = len(adj)
        k_bar = (n_edges / n_nodes) if n_nodes else 0.0
        k_max = max((len(v) for v in adj.values()), default=0)
        mean_n2 = sum(n2_sizes) / len(n2_sizes)

        summary = {
            "dataset": entry["dataset"], "host": entry["host"], "split": entry["split"],
            "n_attack_nodes": len(n2_sizes),
            "mean_degree_attack_nodes": round(sum(degrees) / len(degrees), 2),
            "mean_n2_empirical": round(mean_n2, 2),
            "k_bar_graph": round(k_bar, 4),
            "ceiling_k_bar2": round(k_bar ** 2, 2),
            "ceiling_k_max2": k_max ** 2,
            "ratio_mean_n2_over_k_bar2": round(mean_n2 / (k_bar ** 2), 4) if k_bar else None,
        }
        summary_rows.append(summary)
        print(f"  -> n_attack_nodes={summary['n_attack_nodes']}  "
              f"mean|N_2|={summary['mean_n2_empirical']}  "
              f"k_bar^2={summary['ceiling_k_bar2']}  "
              f"ratio={summary['ratio_mean_n2_over_k_bar2']} "
              f"(often >> 1 on hub-heavy graphs; Proposition 2 bounds IF, not mean |N_2|)",
              file=sys.stderr)

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dataset", "host", "split", "node_id", "degree", "n2_size"])
        w.writeheader()
        w.writerows(per_node_rows)

    with open(args.summary_out, "w", newline="") as f:
        fieldnames = ["dataset", "host", "split", "n_attack_nodes",
                      "mean_degree_attack_nodes", "mean_n2_empirical",
                      "k_bar_graph", "ceiling_k_bar2", "ceiling_k_max2",
                      "ratio_mean_n2_over_k_bar2"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(summary_rows)

    print(f"\n[Test 2] Done. Detail: {args.out}  Summary: {args.summary_out}", file=sys.stderr)


if __name__ == "__main__":
    main()

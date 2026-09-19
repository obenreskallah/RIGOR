"""
Test 1 — graph-degree statistics (k_bar, k_max) per dataset.

Usage:
    python test1_graph_stats.py --config datasets.json --out graph_stats.csv

The only format-specific function is `load_edges()`. Counting, k_bar/k_max,
and CSV export are generic.

`k_bar` uses the raw event count |E|/|V| (KAIROS / EA-THGN / Eq. (4); not
doubled). `k_max` is the max degree in the undirected, deduplicated graph
(Definition 1: E ⊆ V × V is a set). Both conventions are shared with Test 2
via `build_adjacency()`.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


EDGE_SUFFIXES = {".csv", ".jsonl", ".ndjson", ".json"}


def resolve_path(raw, config_file):
    """Resolve a path (or list of paths) relative to the datasets.json directory."""
    cfg_dir = Path(config_file).resolve().parent

    def one(p):
        pp = Path(p)
        if pp.is_absolute():
            return str(pp)
        cand = (cfg_dir / pp).resolve()
        if cand.exists():
            return str(cand)
        return str((Path.cwd() / pp).resolve())

    if isinstance(raw, (list, tuple)):
        return [one(p) for p in raw]
    return one(raw)


def paths_exist(resolved):
    if isinstance(resolved, (list, tuple)):
        return all(Path(p).exists() for p in resolved)
    return Path(resolved).exists()


def load_edges(path):
    """Yield (src_id, dst_id) from a file, directory, or list of paths.

    Formats: CSV `src,dst[,…]` (optional header); PROVATTACK JSONL
    (`logType=EVENT`, `logData.s` / `logData.d`); generic JSONL `{src, dst}`;
    JSON `{"edges": [[src, dst], …]}`.
    """
    if isinstance(path, (list, tuple)):
        for p in path:
            yield from load_edges(p)
        return

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Edge file not found: {path}")

    if p.is_dir():
        files = sorted(f for f in p.iterdir() if f.suffix.lower() in EDGE_SUFFIXES)
        if not files:
            raise FileNotFoundError(f"No edge files in {path}")
        for f in files:
            yield from load_edges(str(f))
        return

    suffix = p.suffix.lower()
    if suffix == ".csv":
        with open(p, "r", newline="") as f:
            reader = csv.reader(f)
            first = next(reader, None)
            if first is None:
                return
            skip_header = (
                len(first) >= 2
                and first[0].strip().lower() in {"src", "source", "src_id", "from"}
                and first[1].strip().lower() in {"dst", "dest", "dst_id", "to", "target"}
            )
            if not skip_header and len(first) >= 2:
                yield first[0], first[1]
            for row in reader:
                if len(row) < 2:
                    continue
                yield row[0], row[1]
    elif suffix in (".jsonl", ".ndjson"):
        with open(p, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                yield from _edges_from_json_record(obj)
    elif suffix == ".json":
        with open(p, "r") as f:
            obj = json.load(f)
        if isinstance(obj, dict) and "edges" in obj:
            for e in obj["edges"]:
                yield e[0], e[1]
        elif isinstance(obj, list):
            for rec in obj:
                yield from _edges_from_json_record(rec)
        else:
            raise NotImplementedError(f"Unhandled JSON structure for {path}")
    else:
        raise NotImplementedError(
            f"Unhandled format for {path} — extend load_edges()."
        )


def _edges_from_json_record(obj):
    """One JSONL record → 0..N edges. PROVATTACK EVENT records first, then generic keys."""
    log_type = obj.get("logType")
    if log_type == "NODE":
        return
    if log_type == "EVENT":
        log = obj.get("logData") or {}
        src, dst, d2 = log.get("s"), log.get("d"), log.get("d2")
        if src and dst:
            yield str(src), str(dst)
        # FileIoRenamePath: PIDSMaker also emits <s,d2> and <d,d2>
        if d2 and src:
            yield str(src), str(d2)
        if d2 and dst:
            yield str(dst), str(d2)
        return
    if "src" in obj and "dst" in obj:
        yield obj["src"], obj["dst"]
        return
    log = obj.get("logData") or {}
    if log.get("s") and log.get("d"):
        yield str(log["s"]), str(log["d"])


def build_adjacency(path):
    """One pass over edges → (adj, n_edges).

    `adj` is undirected and deduplicated ({node: set(neighbours)}), matching
    Definition 1. `n_edges` is the raw event count (no dedup), used only for
    k_bar = |E|/|V|. Shared with Test 2 for the 2-hop BFS.
    """
    adj = defaultdict(set)
    n_edges = 0
    for src, dst in load_edges(path):
        adj[src].add(dst)
        adj[dst].add(src)
        n_edges += 1
        if n_edges % 2_000_000 == 0:
            print(f"  ... {n_edges:,} edges indexed", file=sys.stderr)
    return adj, n_edges


def compute_stats(path: str):
    """k_bar from the raw event count; k_max/percentiles from undirected degree."""
    adj, n_edges = build_adjacency(path)
    n_nodes = len(adj)
    k_bar = (n_edges / n_nodes) if n_nodes else 0.0
    degree_values = sorted(len(v) for v in adj.values())
    k_max = degree_values[-1] if degree_values else 0

    return {
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "k_bar": round(k_bar, 4),
        "k_max": k_max,
        "ceiling_k_bar2": round(k_bar ** 2, 2),
        "ceiling_k_max2": k_max ** 2,
        "degree_p50": degree_values[len(degree_values) // 2] if degree_values else 0,
        "degree_p99": degree_values[int(len(degree_values) * 0.99)] if degree_values else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to datasets.json")
    ap.add_argument("--out", default="graph_stats.csv")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    rows = []
    for entry in cfg["datasets"]:
        edge_path = resolve_path(entry["path"], args.config)
        if not paths_exist(edge_path):
            print(f"[Test 1] SKIP {entry['dataset']}/{entry['host']}/{entry['split']}: "
                  f"edge file missing ({edge_path}).",
                  file=sys.stderr)
            continue
        print(f"[Test 1] {entry['dataset']}/{entry['host']}/{entry['split']} ...", file=sys.stderr)
        stats = compute_stats(edge_path)
        row = {
            "dataset": entry["dataset"],
            "host": entry["host"],
            "split": entry["split"],
            **stats,
        }
        rows.append(row)
        print(f"  -> |V|={row['n_nodes']:,}  |E|={row['n_edges']:,}  "
              f"k_bar={row['k_bar']}  k_max={row['k_max']}  "
              f"ceiling(k_bar^2)={row['ceiling_k_bar2']}", file=sys.stderr)

    fieldnames = ["dataset", "host", "split", "n_nodes", "n_edges", "k_bar",
                  "k_max", "ceiling_k_bar2", "ceiling_k_max2",
                  "degree_p50", "degree_p99"]
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[Test 1] Done. Results in {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()

# Scripts

Pure-Python (standard library only: `csv`, `json`, `collections`, `argparse`) — no installation required beyond Python 3.

| Script | Purpose | Depends on |
|---|---|---|
| `test1_graph_stats.py` | Recomputes mean/max node degree (k̄, k_max) directly from the edge list of each graph. | `datasets.json`: `path` |
| `test2_prop2_geometric.py` | Direct geometric measurement of the 2-hop neighborhood size \|N2(v\*)\| for every ground-truth attack node, via breadth-first search. | `datasets.json`: `path`, `ground_truth_path`; imports `load_edges()` from `test1_graph_stats.py` |
| `test3_p1_vs_p2_postprocessing.py` | Recomputes precision/recall under both the P1 (2-hop true-positive) and P2 (strict node-level) labeling criteria from a detector's raw per-node predictions. | `datasets.json`: `path`, `ground_truth_path`, `predictions_path`, `system` |
| `test4_multiseed_aggregate.py` | Aggregates `test3`'s per-seed output into mean/std/relative-std across seeds. | output of `test3` |
| `extract_pidsmaker_predictions.py` | Converts a PIDSMaker evaluation run's internal output into the flat per-node prediction CSV that `test3` expects. | a completed PIDSMaker run |
| `map_gt_to_nids.py` | Maps raw ground-truth node UUIDs (as published by DARPA / Aurora-style labeling tools) to the integer node IDs used internally by the graph export. | your graph's UUID↔ID mapping |

## The one thing you need to adapt

`load_edges()` inside `test1_graph_stats.py` is the only piece of code that depends on your specific edge-list file format. `test2` and `test3` import it, so adapting it once is enough for all three. If your files need `pandas`, `pyarrow`, or `networkx` to load, add that inside `load_edges()` / `load_predictions()` without touching the rest of the scripts — the CLI, CSV output, and statistics logic are format-agnostic.

## Config format

Copy `datasets.example.json` to `datasets.json` and fill in real paths — see the file for the exact schema (one object per dataset/host/split, with `path`, `ground_truth_path`, and, for Test 3 only, `predictions_path` + `system`).

## Quick check

Every script accepts `--help` and prints progress to stderr, which matters for large files (E3-THEIA's test edge list is ~9.4M edges). Try the smallest dataset you have first (FiveDirections or CADETS) before running against THEIA/ClearScope, to confirm `load_edges()` is correctly adapted before committing to a longer run.

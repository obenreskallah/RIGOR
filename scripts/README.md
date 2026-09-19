# Scripts

Tests 1–4 are Python 3.9+ **standard library only** (`csv`, `json`, `collections`, `argparse`, `statistics`). No install step.

`extract_pidsmaker_predictions.py` is the exception: it imports **PyTorch** to read PIDSMaker `*.pth` files. Skip it if your predictions are already a CSV.

| Script | Purpose | Config fields |
|---|---|---|
| `test1_graph_stats.py` | Mean/max degree (k̄, k_max) from the edge list | `path` |
| `test2_prop2_geometric.py` | \|N₂(v*)\| for each ground-truth attack node (BFS) | `path`, `ground_truth_path` |
| `test3_p1_vs_p2_postprocessing.py` | Precision/recall under P1 (2-hop) vs P2 (strict) | + `predictions_path`, `system` |
| `test4_multiseed_aggregate.py` | Mean/std/relative-std of Test 3 across seeds | Test 3 CSV(s) |
| `extract_pidsmaker_predictions.py` | PIDSMaker `result_*.pth` → `node_id,predicted_label,score` | a finished PIDSMaker eval dir or `--pth` |
| `map_gt_to_nids.py` | DARPA/Aurora UUIDs → integer node IDs in the edge list | `--uuid-map` CSV `uuid,index_id` |

CLI flags are only `--config` / `--out` (Tests 1–3), plus `--summary-out` (Test 2) and `--inputs` (Test 4). There is no `--predictions-dir` and no `run_all_in_one.py`.

## The one function to adapt

`load_edges()` in `test1_graph_stats.py` is the only format-specific loader. `test2` and `test3` import it. If your export is not CSV `src,dst`, JSONL, or `{"edges": [...]}`, change that function once.

## Config

Copy `datasets.example.json` → `datasets.json`. One object per (dataset, host, split). The CSVs published with this paper use `"split": "full"`. Optional top-level `"seeds": [0, 1, 2]` expands `{seed}` in `predictions_path` for Test 3.

Test 3 **skips** entries that have no `predictions_path` without printing a line. If the output CSV is header-only, the config was incomplete, not a successful empty experiment.

## Checks before a long run

- IDs in the edge list, ground truth, and predictions must be the same strings. A high “attack nodes absent from graph” count on stderr means you still need `map_gt_to_nids.py`.
- RAM scales with \|V\| + unique neighbours (full adjacency). Try the smallest host first.
- Test 2’s `ratio_mean_n2_over_k_bar2` is often ≫ 1 on DARPA graphs; that is not a failed run.

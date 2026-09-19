# Mapping: paper table → script → output file

| Paper element | Script | Output file(s) in `results/` |
|---|---|---|
| Table 6 (First-Party Graph Statistics: mean/max degree per graph) | `scripts/test1_graph_stats.py` | `graph_stats.csv`, `graph_stats_provattack_cadets.csv` |
| Table 7 (Direct Geometric Measurement of \|N2(v*)\|) | `scripts/test2_prop2_geometric.py` | `prop2_geometric.csv`, `prop2_geometric_summary.csv` |
| Table 8 (First-Party Detector-Level Precision Inflation, P1 vs. P2) | `scripts/test3_p1_vs_p2_postprocessing.py`, run against per-seed detector predictions from PIDSMaker | `p1_vs_p2_results.csv`, `out_*.csv` (per-dataset intermediate), `consolidated_without_e5.csv` |
| Seed-stability figures cited in Table 8's discussion (multi-seed std. dev.) | `scripts/test4_multiseed_aggregate.py` | `multiseed_stability.csv` |
| Ground-truth node mapping feeding Test 2 / Test 3 | `scripts/map_gt_to_nids.py` | (intermediate; feeds `ground_truth_path` in `datasets.json`) |
| Raw prediction extraction from a PIDSMaker container run | `scripts/extract_pidsmaker_predictions.py` | (intermediate; feeds `predictions_path` in `datasets.json`) |

For the exact execution order and the one format-specific adaptation point (`load_edges()` in `test1_graph_stats.py`), see `scripts/README.md`.

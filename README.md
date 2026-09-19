# RIGOR

**R**eporting **I**nstrument for **G**raph-based, **O**bjective, **R**eproducible evaluation

PIDS papers often report high precision under a *2-hop* true-positive rule (protocol **P1**). The same predictions, scored with *strict node-level* labels (protocol **P2**), can yield precision orders of magnitude lower.

RIGOR is that gap, made reusable:

1. **A checkable reporting instrument** — `checklist/RIGOR_Checklist.md` (Critical C1–C6, Recommended R1–R7). Any provenance-based intrusion detection (PIDS) paper can copy it. It does not depend on this repository’s graphs or numbers.
2. **A measurement protocol** — the scripts in `scripts/` that recompute graph-degree statistics, 2-hop neighbourhood sizes, and the inflation factor `IF = precision_P1 / precision_P2` from a detector’s *raw per-node decisions*. Another paper applies this to *its* graphs and *its* detector; it does not need our DARPA runs.

The first-party CSVs in `results/` are the numbers behind:

> O. Benreskallah, H. Seba, W.-K. Hidouci, K. Amrouche. **“Bounding the Illusion: A Formal and Empirical Account of Precision Inflation, Reproducibility, and Robustness in Provenance-Based Intrusion Detection.”** *Computers & Security* (under review).

This repository is **not** a detector, **not** a training harness, and **not** a redistribution of DARPA Transparent Computing.

---

## Which path are you on?

| You want to… | Start here | What you must bring |
|---|---|---|
| Adopt RIGOR in **your** paper / review a submission | [`checklist/RIGOR_Checklist.md`](checklist/RIGOR_Checklist.md) | Nothing else |
| Measure P1 vs P2 inflation on **your** graphs | [Apply the protocol](#apply-the-protocol-to-your-own-data) | Edge list + attack-node IDs + (for Test 3) per-node predictions, **all in the same ID space** |
| Audit **this** paper’s Tables 6–8 without downloading DARPA TC | [`results/`](results/) and [Example output](#example-output) | Nothing — the aggregate CSVs are already here |
| Rebuild Tables 6–8 from scratch | [Reproduce this paper’s numbers](#reproduce-this-papers-tables-68) | DARPA TC E3/E5 + PIDSMaker v4.0.0 + this protocol |

---

## What’s in this repository

```
RIGOR/
├── checklist/RIGOR_Checklist.md   # the instrument (CC-BY-4.0)
├── scripts/                       # the protocol (MIT, Python 3 stdlib for Tests 1–4)
│   ├── test1_graph_stats.py
│   ├── test2_prop2_geometric.py
│   ├── test3_p1_vs_p2_postprocessing.py
│   ├── test4_multiseed_aggregate.py
│   ├── extract_pidsmaker_predictions.py   # helper; needs PyTorch
│   ├── map_gt_to_nids.py                  # helper; UUID → graph node ID
│   └── datasets.example.json
├── results/                       # published CSVs for Tables 6–8 (see mapping below)
├── CITATION.cff
├── LICENSE                        # MIT — scripts
└── LICENSE-CHECKLIST              # CC-BY-4.0 — the checklist
```

---

## Apply the protocol to your own data

This is the reuse path for another paper. You do **not** need DARPA TC.

### Requirements

- Python 3.9+ standard library for Tests 1–4 (`csv`, `json`, `argparse`, `collections`, `statistics`).
- **RAM:** Tests 1–3 keep the full undirected adjacency in memory. Graphs with tens of millions of events (DARPA E3-THEIA is ~44M) need a workstation, not a typical laptop.
- PyTorch **only** if you use `extract_pidsmaker_predictions.py` to read a PIDSMaker `*.pth` file. Tests 1–4 never import it.

### Input contract (read this first)

The usual failure is not a Python exception. It is **silently wrong precision** because node IDs in the graph, the ground truth, and the predictions do not refer to the same objects.

**1. Edge list** — field `path` in `datasets.json`

`load_edges()` in `test1_graph_stats.py` is the only format-specific function. `test2` and `test3` import it. Supported out of the box:

| File | Expected content |
|---|---|
| `.csv` | Two leading columns `src,dst` (header optional if named `src`/`source`/`src_id`/`from` and `dst`/`dest`/`dst_id`/`to`/`target`) |
| `.jsonl` / `.ndjson` | Either generic `{src, dst}` or PROVATTACK-style `logType=EVENT` with `logData.s` / `logData.d` |
| `.json` | `{"edges": [[src, dst], …]}` or a list of the JSONL records above |
| directory | All files with those suffixes, concatenated |

Anything else: adapt `load_edges()` once.

**2. Attack nodes** — field `ground_truth_path`

One node ID per line (TXT), or the substring before the first comma (CSV), or a JSON list. IDs **must match** the edge-list IDs. If your labels are DARPA UUIDs and your graph uses integer `index_id`s, run `map_gt_to_nids.py` first (see helpers below).

**3. Predictions** — field `predictions_path` (Test 3 only)

CSV with header `node_id,predicted_label[,score]`. A node is flagged malicious when `predicted_label` is `1`, `True`, `true`, or `malicious`. Prefer the detector’s already-thresholded decision, not a raw score.

**4. Config**

```bash
cp scripts/datasets.example.json scripts/datasets.json
# set path, ground_truth_path; for Test 3 also predictions_path + system
```

Optional top-level `"seeds": [0, 1, 2]` with `{seed}` inside `predictions_path` expands Test 3 across seeds in one run.

### Commands

```bash
python3 scripts/test1_graph_stats.py --config scripts/datasets.json --out results/graph_stats.csv
python3 scripts/test2_prop2_geometric.py --config scripts/datasets.json --out results/prop2_geometric.csv
python3 scripts/test3_p1_vs_p2_postprocessing.py --config scripts/datasets.json --out results/p1_vs_p2_results.csv
python3 scripts/test4_multiseed_aggregate.py --inputs results/p1_vs_p2_results.csv --out results/multiseed_stability.csv
```

| Step | Measures | Needs |
|---|---|---|
| Test 1 | \|V\|, \|E\|, mean degree k̄, k_max, k̄² (Table 6 in our paper) | `path` |
| Test 2 | \|N₂(v*)\| for every attack node (Table 7) | `path`, `ground_truth_path` |
| Test 3 | precision/recall under P2 (strict) and P1 (2-hop), `IF_empirical` (Table 8) | + `predictions_path`, `system` |
| Test 4 | mean / std / relative std across seeds | Test 3 CSV(s) |

Missing files are skipped (stderr). Test 3 also **silently skips** entries that lack `predictions_path` — check that the output CSV is not header-only before treating the run as success.

**Seeds.** This paper’s archived CSVs use three seeds (`0/1/2`). Checklist item **C3** asks *new* submissions for **≥5** seeds. Use ≥5 when you adopt RIGOR; 3 is what is published here.

**Test 2 ratio.** The column `ratio_mean_n2_over_k_bar2` is often **≫ 1** on hub-heavy provenance graphs (682 on E3-CADETS in our CSV). That is expected: Proposition 2 bounds *precision inflation*, not the mean 2-hop size of attack nodes. A large ratio is not a failed run.

### Helpers (only if your IDs or detector dumps need conversion)

```bash
# UUID ground truth → integer IDs used in the edge list
python3 scripts/map_gt_to_nids.py \
  --uuid-map /path/to/uuid_to_index.csv \
  --gt-files /path/to/raw_gt.txt \
  --out /path/to/attack_node_ids.txt

# PIDSMaker evaluation *.pth → the CSV Test 3 expects (requires PyTorch)
python3 scripts/extract_pidsmaker_predictions.py \
  --eval-dir /path/to/artifacts/evaluation/.../CADETS_E3 \
  --out results/predictions/threatrace_CADETS_E3_seed0.csv
```

`--uuid-map` is a two-column CSV `uuid,index_id` (no assumed header). Count the “absents” line: a large miss rate means the map and the graph export do not belong together.

---

## Reproduce this paper’s Tables 6–8

The raw DARPA TC graphs are tens of gigabytes and are not ours to redistribute. Get Engagement 3/5 from [github.com/darpa-i2o/Transparent-Computing](https://github.com/darpa-i2o/Transparent-Computing). Detector runs used [PIDSMaker](https://github.com/ubc-provenance/PIDSMaker) **v4.0.0** — install and load data from that project, then export the **same** graph the detector trained on (node IDs must match its predictions).

Then apply the protocol above with `split: "full"` (the archived CSVs are not a train/test split). Compare against:

| Paper | Script | File to trust in `results/` |
|---|---|---|
| Table 6 | `test1_graph_stats.py` | **`graph_stats.csv`** (undirected, deduplicated k_max) |
| Table 7 | `test2_prop2_geometric.py` | `prop2_geometric.csv`, `prop2_geometric_summary.csv` |
| Table 8 | `test3` then `test4` | `p1_vs_p2_results.csv`, `multiseed_stability.csv` |

Do **not** use `graph_stats_provattack_cadets.csv` for Table 6: it is an older k_max definition (directed, not deduplicated) and disagrees with `graph_stats.csv`. Files `out_*.csv` and `consolidated_without_e5.csv` are sliced copies of Test 3, not produced by a separate script.

See [`scripts/README.md`](scripts/README.md) for exact commands and troubleshooting.

---

## Example output

Excerpts from `results/`, as produced by the scripts (discussion in the paper).

`graph_stats.csv` — Table 6, `split=full`:

| dataset | host | n_nodes | n_edges | k̄ | k_max | ceiling k̄² |
|---|---|---|---|---|---|---|
| E3 | CADETS | 2,615,632 | 36,484,667 | 13.95 | 871,610 | 194.57 |
| E3 | THEIA | 1,249,481 | 44,366,117 | 35.51 | 142,132 | 1,260.79 |
| E3 | CLEARSCOPE | 292,216 | 18,316,129 | 62.68 | 32,577 | 3,928.80 |

`p1_vs_p2_results.csv` — Table 8, one row per (system, dataset, seed):

| system | dataset | precision_P2 | precision_P1 | IF_empirical |
|---|---|---|---|---|
| THREATRACE | E3-CADETS | 0.000241 | 0.794158 | 3288.6× |
| MAGIC | E3-CADETS | 0.000533 | 0.926668 | 1737.1× |

`multiseed_stability.csv` aggregates those rows over the three archived seeds.

---

## Citation

See [`CITATION.cff`](CITATION.cff). Please fill ORCID/affiliation there before a Zenodo (or similar) archive.

## License

Code (`scripts/`) is MIT. The checklist is CC-BY-4.0 so it can be reused, translated, and adapted — `LICENSE` and `LICENSE-CHECKLIST`.

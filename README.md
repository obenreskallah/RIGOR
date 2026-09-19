# RIGOR

**R**eporting **I**nstrument for **G**raph-based, **O**bjective, **R**eproducible evaluation

RIGOR is a companion resource for provenance-based intrusion detection (PIDS) research. It provides:

1. **A reusable evaluation-reporting checklist** (`checklist/RIGOR_Checklist.md`) that any PIDS paper can adopt, independent of this repository's own results.
2. **The first-party measurement scripts and outputs** behind the precision-inflation analysis in:

   > O. Benreskallah, H. Seba, W.-K. Hidouci, K. Amrouche. **"Bounding the Illusion: A Formal and Empirical Account of Precision Inflation, Reproducibility, and Robustness in Provenance-Based Intrusion Detection."** *Computers & Security* (under review).

If you only want the checklist for your own paper, go straight to [`checklist/RIGOR_Checklist.md`](checklist/RIGOR_Checklist.md) — it has no dependency on the rest of this repo.

---

## What's in this repository

```
RIGOR/
├── checklist/
│   └── RIGOR_Checklist.md       # the checklist: Critical (C1-C6) + Recommended (R1-R7) items
├── scripts/
│   ├── test1_graph_stats.py     # graph-structural degree statistics (Table 6)
│   ├── test2_prop2_geometric.py # 2-hop neighborhood size, direct measurement (Table 7)
│   ├── test3_p1_vs_p2_postprocessing.py  # P1 (2-hop) vs. P2 (strict) precision from detector output (Table 8)
│   ├── test4_multiseed_aggregate.py      # multi-seed mean/std aggregation
│   ├── extract_pidsmaker_predictions.py  # helper: pull predictions out of a PIDSMaker run
│   ├── map_gt_to_nids.py                 # helper: map raw ground-truth UUIDs to graph node IDs
│   └── datasets.example.json             # config schema — copy to datasets.json and fill in your paths
├── results/                     # the actual outputs these scripts produced for the paper (see below)
├── docs/
│   └── mapping_table_to_script.md
├── CITATION.cff
├── LICENSE                      # MIT — scripts
└── LICENSE-CHECKLIST            # CC-BY-4.0 — the checklist document
```

## About the dataset — why it isn't in this repo

This repository intentionally contains **no raw provenance-graph data**. The underlying DARPA Transparent Computing (TC) engagement data is tens of gigabytes and is distributed directly by DARPA I2O; the derived, per-node prediction files used in the paper add several hundred more megabytes on top of that. Redistributing either would make this repo unusable to clone, would duplicate data DARPA already hosts, and in the case of DARPA TC, isn't ours to redistribute under its own terms.

What *is* here instead, in `results/`, are the small aggregate CSVs the scripts actually produced — the numbers that appear in the paper's Tables 6, 7, and 8. That's enough to audit the paper's reported figures and to see the exact shape of each script's output (see **Example output** below) without needing the raw graphs yourself. To reproduce the numbers from scratch, get DARPA TC Engagement 3/5 from [github.com/darpa-i2o/Transparent-Computing](https://github.com/darpa-i2o/Transparent-Computing) and follow **Usage** below.

## Usage

### 1. Checklist only

Copy `checklist/RIGOR_Checklist.md` into your own paper's repository, fill in the `Status`/`Evidence` columns for each item, and link it from your Data Availability statement. No installation needed — it's a Markdown file.

### 2. Reproducing the graph-structural measurements (Tables 6–7)

Requirements: Python 3, standard library only (no external dependencies).

```bash
cp scripts/datasets.example.json scripts/datasets.json
# edit datasets.json: replace each "path" / "ground_truth_path" with your own
# preprocessed DARPA TC edge-list and ground-truth files

python3 scripts/test1_graph_stats.py --config scripts/datasets.json --out results/graph_stats.csv
python3 scripts/test2_prop2_geometric.py --config scripts/datasets.json --out results/prop2_geometric.csv
```

The only part of the code that depends on your specific file format is `load_edges()` inside `test1_graph_stats.py` — adapt that one function and both scripts will work, since `test2` imports it.

### 3. Reproducing the detector-level precision-inflation measurement (Table 8)

This step additionally requires running a PIDS detector to get predictions. We used [PIDSMaker](https://github.com/ubc-provenance/PIDSMaker) (v4.0.0) — see its own repository for installation and dataset-loading instructions, since that is a general-purpose PIDS training/evaluation harness independent of this paper.

Once you have per-node predictions from a detector run:

```bash
# add "predictions_path" and "system" fields to each relevant entry in datasets.json
python3 scripts/test3_p1_vs_p2_postprocessing.py --config scripts/datasets.json --out results/p1_vs_p2_results.csv

# repeat across ≥3 random seeds, then aggregate:
python3 scripts/test4_multiseed_aggregate.py --inputs results/p1_vs_p2_results.csv --out results/multiseed_stability.csv
```

`extract_pidsmaker_predictions.py` and `map_gt_to_nids.py` are small helpers used to get from a raw PIDSMaker/Aurora run into the `predictions_path` / `ground_truth_path` format the scripts above expect — read their `--help` for their exact inputs.

See `docs/mapping_table_to_script.md` for the full table → script → output mapping.

## Example output

Real excerpts from `results/`, exactly as produced by the scripts above (see the paper for full discussion):

`graph_stats.csv` — Table 6, graph-structural degree statistics:

| dataset | host | n_nodes | n_edges | k̄ (mean degree) | k_max | ceiling k̄² |
|---|---|---|---|---|---|---|
| E3 | CADETS | 2,615,632 | 36,484,667 | 13.95 | 871,610 | 194.57 |
| E3 | THEIA | 1,249,481 | 44,366,117 | 35.51 | 142,132 | 1,260.79 |
| E3 | CLEARSCOPE | 292,216 | 18,316,129 | 62.68 | 32,577 | 3,928.80 |

`p1_vs_p2_results.csv` — Table 8, one row per (system, dataset, seed): P1 (2-hop) vs. P2 (strict node-level) precision, and the resulting empirical inflation factor:

| system | dataset | precision_P2 | precision_P1 | IF_empirical |
|---|---|---|---|---|
| THREATRACE | E3-CADETS | 0.000241 | 0.794158 | 3288.6× |
| MAGIC | E3-CADETS | 0.000533 | 0.926668 | 1737.1× |

`multiseed_stability.csv` — Table 8's seed-stability companion: mean/std/relative-std over ≥3 seeds per (system, dataset), confirming these numbers are not single-run artifacts.

## Citation

See [`CITATION.cff`](CITATION.cff). Please fill in your ORCID/affiliation details there before archiving a release (e.g. on Zenodo).

## License

Code (`scripts/`) is MIT-licensed. The checklist document is CC-BY-4.0 so it can be freely reused, translated, and adapted by other venues and communities — see `LICENSE` and `LICENSE-CHECKLIST` respectively.

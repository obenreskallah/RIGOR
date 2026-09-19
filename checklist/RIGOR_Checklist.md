# RIGOR — Reporting Instrument for Graph-based, Objective, Reproducible evaluation

*A reproducible, versioned operationalization of Requirements R1–R4 and the Evaluation Compliance Checklist (Table 3) proposed in:*

> Benreskallah, O., Seba, H., Hidouci, W.-K., Amrouche, K. "Bounding the Illusion: A Formal and Empirical Account of Precision Inflation, Reproducibility, and Robustness in Provenance-Based Intrusion Detection." *Computers & Security* (under review).

**Positioning.** A literature check (September 2026) found no prior work in this sub-field that formalizes evaluation-reporting requirements into a structured, itemized, checkable instrument. The closest related work calls for better standards only in prose: Wang, Zheng, Gui, Hua & Ul Hassan, *"R+R: From Claims to Crashes: A Systematic Re-evaluation of Graph-Based Network Intrusion Detection Systems"* (ACSAC 2025, DOI 10.1109/acsac67867.2025.00050) documents up to 40% metric variance from undocumented preprocessing/threshold choices and "urge[s] the community to adopt rigorous standards," and Guerra, Chapuis, Duc, Mozharovskyi & Nguyen, *"How Benchmarks and Evaluation Protocols Shape Conclusions in Provenance-Based Intrusion Detection"* (arXiv:2608.01454, Aug. 2026) independently reaches a closely related conclusion — but neither converts its recommendations into a checkable, itemized artifact with severity levels and a verification method per item. RIGOR is offered as that missing artifact: a reusable, checkable reporting instrument for the four requirements (R1–R4) argued for in the paper above, positioned as the first formalization of this kind for PIDS evaluation reporting rather than merely a restatement of existing calls for rigor. Authors preparing a provenance-based intrusion detection system (PIDS) submission can copy this file into their own repository and fill it in; reviewers and area chairs can use it as a scoring rubric at review time. Contributions and amendments are welcome via pull request.

**How to use this file:** copy it into your paper's repository as `RIGOR_Checklist.md` (or `CHECKLIST.md`), fill in the `Status` and `Evidence` columns, and link it from your paper's Data Availability / Reproducibility statement.

---

## Critical items (a submission should not be accepted without addressing these)

| # | Item | What it means | Status (☐/✅/❌/N/A) | Evidence / pointer |
|---|---|---|---|---|
| C1 | **Evaluation protocol named explicitly** | State which of P1 (2-hop TP), P2 (strict node-level), P3 (Aurora/execution-instrumented), P4 (window-level), or P5 (graph/trace-level) — or a clearly defined equivalent — produced every reported precision/recall/F1 figure. | ☐ | Section / line reference |
| C2 | **If P1 is used, P2 is also reported** (where artifacts permit) | Any P1-criterion precision above 0.50 must be accompanied by the same metric under strict (P2) node-level labeling on the same data/config. | ☐ | Table / figure reference |
| C3 | **Seed independence** | Performance reported as mean ± std (or full per-seed table) over **≥5 random seeds**, not a single run. | ☐ | Table reference |
| C4 | **Dataset preprocessing script publicly available** | The exact script(s) turning raw provenance logs into the graph fed to the model are in a public repository, not only described in prose. | ☐ | Repo URL / DOI |
| C5 | **Ground-truth labeling procedure described reproducibly** | State exactly how attack nodes/edges were identified (manual annotation, Aurora-style instrumentation, vendor report cross-reference, etc.), with enough detail that a third party could re-derive the same label set. | ☐ | Section reference |
| C6 | **Author-facing data/code availability statement matches the in-text claims** | If the manuscript references "the paper's repository" anywhere in the main text, the Data Availability section must name and link that exact repository (and, ideally, a persistent DOI, e.g. via Zenodo). *(This item exists because it is the single most common self-inflicted inconsistency in this sub-field — check it explicitly.)* | ☐ | Data Availability text |

## Recommended items (best practice; strengthens the submission but is not an automatic rejection trigger)

| # | Item | What it means | Status | Evidence / pointer |
|---|---|---|---|---|
| R1 | **Non-DARPA-TC dataset included** | At least one result on a dataset other than DARPA Transparent Computing, to test generalization beyond one benchmark's degree distribution. | ☐ | |
| R2 | **Adversarial / mimicry baseline evaluated** | Performance reported against a mimicry-style structural attack (e.g., Goyal et al. 2023's benchmark) or an equivalent adaptive-adversary test. | ☐ | |
| R3 | **Throughput / memory profile reported** | Wall-clock and memory footprint at the scale the system is claimed to support. | ☐ | |
| R4 | **Comparison against a standardized baseline suite** | Numbers compared against a shared re-implementation framework (e.g., PIDSMAKER) rather than only against each system's own originally reported figures. | ☐ | |
| R5 | **Concept drift acknowledged or evaluated** | Either an experiment on temporal drift, or an explicit limitation statement that none was performed. | ☐ | |
| R6 | **Exact hyperparameters and random seeds published** | Not just "mean ± std over 5 seeds" (C3), but the literal seed values and full hyperparameter/config files, so C3 is independently checkable. | ☐ | |
| R7 | **Author list / reference metadata complete** | Bibliography entries carry full author lists (not "et al." placeholders) and DOIs where available — a hygiene item that matters for the paper's own credibility on rigor. | ☐ | |

---

## Verification method (for reviewers / area chairs)

- **C1** — Check the "Evaluation" or "Experimental Setup" section for an explicit protocol name or equivalent definition.
- **C2** — Check the results table for both a permissive (P1-style) and a strict (P2-style) figure side by side.
- **C3** — Check for confidence intervals, standard deviations, or a per-seed table.
- **C4 / C5** — Check the artifact-availability / data-availability statement and attempt to resolve the linked repository.
- **C6** — Search the manuscript for every phrase referencing "repository," "code availability," "data availability statement," etc., and confirm each one resolves to an actual, named, linked location.
- **R1–R7** — Check the datasets table, adversarial evaluation section, system evaluation section, limitations section, and reference list, respectively.

---

## Versioning

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09 | Initial extraction from Table 3 of Benreskallah et al., "Bounding the Illusion..." (Computers & Security, under review), with item C6 added to address a self-audit finding. |
| 0.2 | 2026-09 | Renamed to **RIGOR** (Reporting Instrument for Graph-based, Objective, Reproducible evaluation); no content change to the items themselves. |

## License

Suggested: CC-BY-4.0 for this checklist document (so it can be freely reused, translated, and adapted by other venues/communities), MIT for any accompanying validation scripts.

## How to cite

If you use or adapt RIGOR, please cite the source paper (see top of this file) and, once available, its Zenodo/GitHub archival DOI.

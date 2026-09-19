"""
Test 2 -- Validation geometrique directe de la Proposition 2 (sans detecteur).

Pour chaque noeud d'attaque du ground truth, mesure |N_2(v*)| (taille du
voisinage a 2 hops) et compare a k_bar^2 (borne Proposition 2, r=1) et a
k_max^2 (borne pire cas). Ne depend d'aucun IDS -- uniquement du graphe et
du ground truth.

Usage:
    python test2_prop2_geometric.py --config datasets.json --out prop2_geometric.csv

Reutilise `load_edges()` ET `build_adjacency()` de test1_graph_stats.py --
adapte le loader la-bas, pas ici. Ce script attend EN PLUS un champ
"ground_truth_path" dans chaque entree de datasets.json, pointant vers un
fichier listant les IDs de noeuds malveillants (un ID par ligne, ou JSON
liste -- adapte `load_attack_nodes()` si besoin).

CORRECTIF : ce script definissait auparavant sa PROPRE copie de
`build_adjacency()`, identique en apparence a celle de test1_graph_stats.py
mais qui avait divergee : test1 calculait k_max sur un degre DIRIGE brut
(out+in, sans dedupliquer les aretes multiples/reciproques) tandis que ce
script le calculait deja correctement sur l'adjacence non dirigee dedupliquee
utilisee pour son propre BFS. Les deux "k_max" ne correspondaient donc pas
(jusqu'a ~400x d'ecart sur CADETS/THEIA/CLEARSCOPE), alors que k_bar
(= |E|/|V|, insensible a cette distinction) restait identique -- ce qui
masquait le probleme. `build_adjacency()` est maintenant importee de
test1_graph_stats.py -- une seule implementation, les deux scripts ne
peuvent plus diverger.

Implementation en dict d'adjacence + BFS manuel (pas de dependance a
networkx) pour rester leger sur un MacBook sans GPU, meme sur des graphes de
plusieurs millions d'aretes -- seul le sous-ensemble de noeuds d'attaque
(typiquement quelques centaines a quelques milliers) est explore en BFS, le
reste du graphe ne sert que de table de voisinage.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test1_graph_stats import load_edges, resolve_path, paths_exist, build_adjacency  # reutilise le meme loader ET la meme adjacence


def load_attack_nodes(path: str):
    """IDs malveillants. Accepte un fichier, un dossier, ou une liste de chemins.

    Formats:
      - CSV orthrus/reapr/PROVATTACK: UUID = premier champ avant la 1re virgule
        (ne pas utiliser csv.reader: le 2e champ est un dict Python avec virgules)
      - TXT ThreaTrace: un UUID par ligne
      - JSON: liste d'IDs
    """
    if isinstance(path, (list, tuple)):
        nodes = set()
        for p in path:
            nodes |= load_attack_nodes(p)
        return nodes

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Ground truth introuvable: {path}")

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
            # UUID = tout ce qui precede la premiere virgule (CSV GT PIDSMaker)
            node_id = line.split(",", 1)[0].strip()
            if node_id:
                nodes.add(node_id)
    return nodes


def two_hop_neighborhood_size(adj, node):
    """|N_2(node)|: nombre de noeuds distincts atteignables en <=2 sauts (exclut node lui-meme)."""
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
                  f"pas de ground_truth_path dans la config", file=sys.stderr)
            continue

        edge_path = resolve_path(entry["path"], args.config)
        gt_path = resolve_path(gt_path, args.config)
        if not paths_exist(edge_path):
            print(f"[Test 2] SKIP {entry['dataset']}/{entry['host']}/{entry['split']}: "
                  f"fichier d'aretes absent. Exporte d'abord le dump Postgres.",
                  file=sys.stderr)
            continue
        if not paths_exist(gt_path):
            print(f"[Test 2] SKIP {entry['dataset']}/{entry['host']}/{entry['split']}: "
                  f"ground truth absent ({gt_path})", file=sys.stderr)
            continue
        print(f"[Test 2] {entry['dataset']}/{entry['host']}/{entry['split']} ...", file=sys.stderr)
        adj, n_edges = build_adjacency(edge_path)
        attack_nodes = load_attack_nodes(gt_path)
        attack_nodes_in_graph = [n for n in attack_nodes if n in adj]
        missing = len(attack_nodes) - len(attack_nodes_in_graph)
        if missing:
            print(f"  [!] {missing} noeuds d'attaque du ground truth absents du graphe "
                  f"(verifie la correspondance d'IDs entre tes fichiers)", file=sys.stderr)

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
            print(f"  [!] Aucun noeud d'attaque exploitable, saut du resume.", file=sys.stderr)
            continue

        n_nodes = len(adj)
        # Meme convention que Test 1 / Proposition 2: k_bar = |E|/|V|
        k_bar = (n_edges / n_nodes) if n_nodes else 0.0
        # k_max: MEME adjacence dedupliquee que Test 1 (import partage) -- ne
        # peut plus diverger de graph_stats.csv.
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
              f"(doit etre <= 1 si la Proposition 2 tient en moyenne)", file=sys.stderr)

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

    print(f"\n[Test 2] Termine. Detail: {args.out}  Resume: {args.summary_out}", file=sys.stderr)


if __name__ == "__main__":
    main()

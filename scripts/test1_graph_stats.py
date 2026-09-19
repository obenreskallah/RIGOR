"""
Test 1 -- Recensement des statistiques de graphe (k_bar, k_max) par dataset.

Usage:
    python test1_graph_stats.py --config datasets.json --out graph_stats.csv

Ce script est volontairement agnostique du format exact de tes fichiers de
graphe : la SEULE fonction à adapter est `load_edges()` ci-dessous. Tout le
reste (comptage, calcul de k_bar/k_max, export CSV) est générique et ne
nécessite aucune modification.

Format attendu de `datasets.json` (à créer toi-même) :
{
  "datasets": [
    {"dataset": "E3", "host": "CADETS", "split": "train", "path": "/path/to/e3_cadets_train_edges.csv"},
    {"dataset": "E3", "host": "CADETS", "split": "test",  "path": "/path/to/e3_cadets_test_edges.csv"},
    {"dataset": "E3", "host": "THEIA",  "split": "train", "path": "..."},
    ...
    {"dataset": "PROVATTACK", "host": "PROVATTACK1", "split": "full", "path": "..."}
  ]
}

Chaque entrée pointe vers UN fichier contenant les arêtes du graphe pour ce
(dataset, host, split). Le format interne du fichier (CSV, JSON-lines,
pickle...) est géré par `load_edges()` -- adapte-le a ton pipeline de
pretraitement DARPA TC / PIDSMAKER.

Conçu pour tourner sur un MacBook sans GPU : le calcul est O(|E|) en temps et
O(|V|) en mémoire pour les degrés (pas besoin de charger le graphe entier en
mémoire si `load_edges` est un générateur -- voir la variante "streaming" plus
bas pour les tres gros fichiers, ex. E3-Theia test: ~9.4M arêtes).

CORRECTIF (voir aussi test2_prop2_geometric.py) : `build_adjacency()` est
maintenant defini UNE SEULE FOIS ici et importe par test2 -- avant ce
correctif, test1 calculait k_max sur le degre DIRIGE brut (out+in, sans
dedupliquer les aretes multiples/reciproques), tandis que test2 le calculait
sur une adjacence non dirigee dedupliquee (des sets) pour son propre usage
interne (BFS a 2 sauts). Les deux scripts rapportaient donc deux notions de
"k_max" differentes (jusqu'a ~400x d'ecart sur CADETS/THEIA/CLEARSCOPE) alors
que k_bar (= |E|/|V|, insensible a cette distinction) restait identique entre
les deux -- d'ou l'illusion de coherence. Definition 1 du papier modelise le
graphe de provenance par $E \\subseteq V \\times V$ (un ENSEMBLE, pas un
multi-ensemble) : c'est la version dedupliquee (celle que test2 utilisait
deja pour son propre BFS) qui est correcte. Les deux scripts partagent
desormais EXACTEMENT le meme calcul de k_max -- ils ne peuvent plus diverger.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


EDGE_SUFFIXES = {".csv", ".jsonl", ".ndjson", ".json"}


def resolve_path(raw, config_file):
    """Resout un chemin (ou une liste) par rapport au dossier de datasets.json."""
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
    """
    Generateur d'aretes (src_id, dst_id). Accepte un fichier, un dossier, ou
    une liste de chemins.

    Formats geres:
      - CSV `src,dst[,...]` (entete optionnelle)
      - JSONL PROVATTACK (`logType=EVENT`, champs `logData.s` / `logData.d`)
      - JSONL generique (`src`/`dst`)
      - JSON `{"edges": [[src, dst], ...]}`
    """
    if isinstance(path, (list, tuple)):
        for p in path:
            yield from load_edges(p)
        return

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Fichier d'aretes introuvable: {path}")

    if p.is_dir():
        files = sorted(f for f in p.iterdir() if f.suffix.lower() in EDGE_SUFFIXES)
        if not files:
            raise FileNotFoundError(f"Aucun fichier d'aretes dans {path}")
        for f in files:
            yield from load_edges(str(f))
        return

    suffix = p.suffix.lower()
    if suffix == ".csv":
        import csv as _csv
        with open(p, "r", newline="") as f:
            reader = _csv.reader(f)
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
            raise NotImplementedError(f"Structure JSON non geree pour {path}")
    else:
        raise NotImplementedError(
            f"Format non gere pour {path} -- ajoute un branch dans load_edges()."
        )


def _edges_from_json_record(obj):
    """Une ligne JSONL -> 0 a N aretes. PROVATTACK d'abord, puis cles generiques."""
    log_type = obj.get("logType")
    if log_type == "NODE":
        return
    if log_type == "EVENT":
        log = obj.get("logData") or {}
        src, dst, d2 = log.get("s"), log.get("d"), log.get("d2")
        if src and dst:
            yield str(src), str(dst)
        # FileIoRenamePath: PIDSMaker ajoute aussi <s,d2> et <d,d2>
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
    """Une seule passe sur les aretes -> (adj, n_edges).

    `adj` est un dict {node: set(voisins)} NON DIRIGE et DEDUPLIQUE (chaque
    arete src->dst ajoute src aux voisins de dst ET dst aux voisins de src ;
    un `set.add` sur une paire deja vue est un no-op) -- coherent avec la
    Definition 1 du papier ($E \\subseteq V \\times V$ est un ENSEMBLE).

    `n_edges` est le nombre BRUT d'evenements traites (sans deduplication),
    utilise uniquement pour k_bar = |E|/|V| (convention KAIROS / EA-THGN /
    Eq. (4) du papier -- chaque evenement compte comme une arete, k_bar
    n'est PAS multiplie par 2).

    Fonction PARTAGEE avec test2_prop2_geometric.py (qui l'utilise pour son
    BFS a 2 sauts) -- ne pas dupliquer cette logique ailleurs : c'est
    precisement la duplication qui a cause l'incoherence corrigee ici.
    """
    adj = defaultdict(set)
    n_edges = 0
    for src, dst in load_edges(path):
        adj[src].add(dst)
        adj[dst].add(src)
        n_edges += 1
        if n_edges % 2_000_000 == 0:
            print(f"  ... {n_edges:,} aretes indexees", file=sys.stderr)
    return adj, n_edges


def compute_stats(path: str):
    """Une seule passe sur les aretes (via build_adjacency): k_bar sur le
    compte brut d'evenements, k_max/percentiles sur le degre non dirige
    deduplique -- la MEME adjacence que celle utilisee par le BFS de Test 2."""
    adj, n_edges = build_adjacency(path)
    n_nodes = len(adj)

    # Proposition 2 du papier: k_bar = |E|/|V| (chaque evenement = une arete).
    # Ne PAS multiplier par 2 -- c'est la convention KAIROS / EA-THGN / Eq. (4).
    k_bar = (n_edges / n_nodes) if n_nodes else 0.0

    # k_max et percentiles: degre dans le graphe simple non dirige deduplique
    # (voir docstring de build_adjacency). Avant le correctif, ce bloc
    # utilisait un degre dirige brut (out+in, non deduplique), incoherent
    # avec test2 et avec Definition 1 du papier.
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
    ap.add_argument("--config", required=True, help="Chemin vers datasets.json")
    ap.add_argument("--out", default="graph_stats.csv")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    rows = []
    for entry in cfg["datasets"]:
        edge_path = resolve_path(entry["path"], args.config)
        if not paths_exist(edge_path):
            print(f"[Test 1] SKIP {entry['dataset']}/{entry['host']}/{entry['split']}: "
                  f"fichier d'aretes absent ({edge_path}). Exporte d'abord le dump Postgres.",
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

    print(f"\n[Test 1] Termine. Resultats dans {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()

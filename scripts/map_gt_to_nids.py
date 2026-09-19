"""Map ground-truth UUIDs to PIDSMaker index_id values.

Usage:
    python scripts/map_gt_to_nids.py \
        --uuid-map /path/to/uuid_to_index.csv \
        --gt-files /path/to/raw_gt.txt \
        --out /path/to/attack_node_ids.txt

`--uuid-map` is a two-column CSV `uuid,index_id`.
"""

import argparse
import csv
from pathlib import Path


def load_uuid_map(path: str) -> dict:
    mapping = {}
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            uuid, nid = row[0].strip(), row[1].strip()
            if uuid and nid:
                mapping[uuid.lower()] = nid
    return mapping


def iter_gt_uuids(path: str):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            yield line.split(",", 1)[0].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uuid-map", required=True)
    ap.add_argument("--gt-files", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    mapping = load_uuid_map(args.uuid_map)
    nids, seen = [], set()
    n_uuid = n_miss = 0
    for gt in args.gt_files:
        p = Path(gt)
        if not p.exists():
            raise FileNotFoundError(gt)
        for uuid in iter_gt_uuids(str(p)):
            n_uuid += 1
            nid = mapping.get(uuid.lower())
            if nid is None:
                n_miss += 1
                continue
            if nid not in seen:
                seen.add(nid)
                nids.append(nid)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        f.write("\n".join(nids) + ("\n" if nids else ""))
    print(f"[GT] {n_uuid} UUIDs, {len(nids)} index_id, {n_miss} missing -> {args.out}")


if __name__ == "__main__":
    main()

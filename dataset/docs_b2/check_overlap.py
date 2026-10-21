#!/usr/bin/env python3
"""Check whether danila_hh duplicates other dataset material on server."""
from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 50_000_000))
root = Path("/root/hakaton/dataset")
dh = root / "raw_sources/danila_hh"


def sha_prefix(p: Path, n: int = 2_000_000) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        left = n
        while left:
            b = f.read(min(1024 * 1024, left))
            if not b:
                break
            h.update(b)
            left -= len(b)
    return h.hexdigest()[:16]


def load_ids(path: Path, id_keys: list[str], delim: str = ",", limit: int = 5000):
    ids = set()
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        r = csv.DictReader(f, delimiter=delim)
        cols = r.fieldnames or []
        lower = {c.lower(): c for c in cols}
        key = None
        for k in id_keys:
            if k.lower() in lower:
                key = lower[k.lower()]
                break
        if not key:
            return set(), None, list(cols)[:12]
        for i, row in enumerate(r):
            v = (row.get(key) or "").strip()
            if v:
                ids.add(v)
            if i >= limit:
                break
    return ids, key, list(cols)[:12]


def main() -> None:
    print("=== danila_hh vs rest ===")
    files = [
        p
        for p in dh.rglob("*")
        if p.is_file()
        and p.suffix.lower() in {".csv", ".zip"}
        and ".cache" not in p.parts
    ]
    others = [
        p
        for p in (root / "raw_sources").rglob("*")
        if p.is_file()
        and "danila_hh" not in p.parts
        and p.suffix.lower() in {".csv", ".zip"}
    ]

    print("-- exact same basename+size outside danila_hh?")
    found = False
    for p in files:
        hits = [o for o in others if o.name == p.name and o.stat().st_size == p.stat().st_size]
        for h in hits:
            print("DUP", p.relative_to(dh), "==", h.relative_to(root))
            found = True
    if not found:
        print("none")

    print("-- sha of first 2MB among large CSVs (collision = likely same bytes)")
    cands = [p for p in files + others if p.suffix.lower() == ".csv" and p.stat().st_size > 1_000_000]
    by: dict[str, list[Path]] = {}
    for p in cands:
        by.setdefault(sha_prefix(p), []).append(p)
    coll = False
    for s, ps in by.items():
        names = [str(x.relative_to(root)) for x in ps]
        # only interesting if mix danila + non-danila
        has_d = any("danila_hh" in n for n in names)
        has_o = any("danila_hh" not in n for n in names)
        if has_d and has_o:
            print("COLLISION", s, names)
            coll = True
    if not coll:
        print("no danila↔other sha collisions")

    print("\n=== schema fingerprints ===")
    specs = [
        (dh / "textovic/repo/cleaned_data.csv", ","),
        (dh / "os_rf_mendeley/vacancies_russian_operating_systems.csv", ","),
        (dh / "it_vacancies_kaggle_alt/extracted/IT_vacancies_full.csv", ","),
        (root / "raw_sources/trudvsem/vacancies.csv", ";"),
    ]
    for p, d in specs:
        if not p.is_file():
            print("MISSING", p)
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as f:
            head = f.readline().strip()[:180]
        print(p.relative_to(root))
        print(" ", "sizeMB=", round(p.stat().st_size / 1e6, 1), "delim=", d)
        print(" ", "head=", head)

    print("\n=== ID overlap within danila_hh (first 5k rows) ===")
    t, tk, tc = load_ids(dh / "textovic/repo/cleaned_data.csv", ["id"])
    m, mk, mc = load_ids(dh / "os_rf_mendeley/vacancies_russian_operating_systems.csv", ["id"])
    i, ik, ic = load_ids(
        dh / "it_vacancies_kaggle_alt/extracted/IT_vacancies_full.csv", ["Ids", "id"]
    )
    print("textovic", tk, len(t), "cols", tc)
    print("mendeley", mk, len(m), "cols", mc)
    print("itvac", ik, len(i), "cols", ic)
    print("overlap textovic∩mendeley", len(t & m))
    print("overlap textovic∩itvac", len(t & i))
    print("overlap mendeley∩itvac", len(m & i))

    print("\n=== role vs eval package ===")
    print("danila_hh = raw vacancy corpora + heuristic match pairs (train pilot)")
    print("builds/public-v1|local-v1 = FSP eval scenarios (synthetic/oracle), not these CSVs")
    print("trudvsem = INID RF dump (;), different schema; bridge sample only reused intentionally")
    print("DONE")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Sample first N rows from trudvsem/vacancies.csv (RF bridge)."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

SRC = Path("/root/hakaton/dataset/raw_sources/trudvsem/vacancies.csv")
OUT = Path("/root/hakaton/dataset/raw_sources/danila_hh/trudvsem_bridge")
N = 800


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"missing {SRC}")
    OUT.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(min(sys.maxsize, 50_000_000))
    out_csv = OUT / "vacancies_sample.csv"
    rows = 0
    with SRC.open(encoding="utf-8", errors="replace", newline="") as fin, out_csv.open(
        "w", encoding="utf-8", newline=""
    ) as fout:
        reader = csv.DictReader(fin, delimiter=";")
        fieldnames = reader.fieldnames or []
        writer = csv.DictWriter(fout, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in reader:
            writer.writerow(row)
            rows += 1
            if rows >= N:
                break
    # peek text-ish columns
    textish = [
        c
        for c in fieldnames
        if any(
            x in c.lower()
            for x in ("duty", "qualif", "req", "desc", "skill", "profession", "position", "name")
        )
    ]
    meta = {
        "role": "bridge_rf_source_while_mendeley_blocked",
        "source_file": str(SRC),
        "source_bytes": SRC.stat().st_size,
        "sampled_rows": rows,
        "delimiter": ";",
        "columns_count": len(fieldnames),
        "textish_columns_guess": textish[:40],
        "note": "Not a substitute for Mendeley OS RF; uses local trudvsem vacancies.csv sample.",
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

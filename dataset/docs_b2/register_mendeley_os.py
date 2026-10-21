#!/usr/bin/env python3
"""Register Mendeley OS RF source and build pairs contrib into danila_hh."""
from __future__ import annotations

import csv
import json
import random
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path("/root/hakaton/dataset/raw_sources/danila_hh/os_rf_mendeley")
LABELS = Path("/root/hakaton/dataset/raw_sources/danila_hh/labels")
STATUS_PATH = Path("/root/hakaton/dataset/raw_sources/danila_hh/SOURCES_STATUS.json")
SEED = 20261009


def tokenize(text: str) -> set[str]:
    toks = re.findall(r"[A-Za-zА-Яа-яЁё0-9+#.]{2,}", (text or "").lower())
    stop = {"и", "в", "на", "по", "для", "the", "and", "with", "опыт", "работа"}
    return {t for t in toks if t not in stop}


def main() -> None:
    random.seed(SEED)
    csv.field_size_limit(min(sys.maxsize, 20_000_000))
    ROOT.mkdir(parents=True, exist_ok=True)

    zips = list(ROOT.glob("*.zip"))
    csvs = [p for p in ROOT.glob("*.csv")]
    extract_dir = ROOT / "extracted"
    if zips:
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zips[0], "r") as zf:
            zf.extractall(extract_dir)
        # prefer extracted csv if present
        extracted_csvs = list(extract_dir.rglob("*.csv"))
        if extracted_csvs:
            csvs = extracted_csvs + csvs

    if not csvs:
        raise SystemExit("no csv found in os_rf_mendeley")

    # canonical copy without spaces
    src = csvs[0]
    canonical = ROOT / "vacancies_russian_operating_systems.csv"
    if src.resolve() != canonical.resolve():
        shutil.copy2(src, canonical)

    rows = []
    with canonical.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get("name") or "").strip()
            desc = (row.get("description") or "").strip()
            skills = (row.get("raw_skills") or "").strip()
            need = (name + "\n" + desc).strip()
            cand = skills if skills else desc[:400]
            if len(need) < 60 or len(cand) < 5:
                continue
            if need == cand:
                continue
            rows.append({"need": need, "cand": cand, "skills": tokenize(cand)})

    pairs = []
    for i, r in enumerate(rows[:400]):
        pairs.append(
            {
                "pair_id": f"osrf-pos-{i}",
                "need_text": r["need"][:5000],
                "candidate_text": r["cand"][:3000],
                "label": "relevant",
                "label_origin": "team_rule",
                "rule": "mendeley_os_skills_vs_description",
                "source": "mendeley_2xyz5rwhcn",
            }
        )
    neg = 0
    attempts = 0
    while neg < 400 and attempts < 20000 and len(rows) >= 2:
        attempts += 1
        a, b = random.sample(rows, 2)
        if len(a["skills"] & b["skills"]) > 3:
            continue
        pairs.append(
            {
                "pair_id": f"osrf-neg-{neg}",
                "need_text": a["need"][:5000],
                "candidate_text": b["cand"][:3000],
                "label": "not_relevant",
                "label_origin": "heuristic",
                "rule": "mendeley_os_cross",
                "source": "mendeley_2xyz5rwhcn",
            }
        )
        neg += 1

    random.shuffle(pairs)
    for i, p in enumerate(pairs):
        p["split"] = "train" if i < int(len(pairs) * 0.8) else "test"

    LABELS.mkdir(parents=True, exist_ok=True)
    out_pairs = LABELS / "candidate_need_pairs_osrf.jsonl"
    with out_pairs.open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # merge into combined file
    combined = LABELS / "candidate_need_pairs_combined.jsonl"
    parts = []
    for name in ("candidate_need_pairs_v2.jsonl", "candidate_need_pairs_osrf.jsonl"):
        p = LABELS / name
        if p.is_file():
            parts.extend(p.read_text(encoding="utf-8").splitlines())
    with combined.open("w", encoding="utf-8") as f:
        for line in parts:
            if line.strip():
                f.write(line + "\n")

    meta = {
        "source": "Mendeley The vacancies data in Russian operating systems",
        "doi": "10.17632/2xyz5rwhcn.1",
        "license_claimed": "CC BY 4.0",
        "zip": str(zips[0]) if zips else None,
        "csv": str(canonical),
        "csv_bytes": canonical.stat().st_size,
        "usable_rows": len(rows),
        "pairs": len(pairs),
        "pairs_file": str(out_pairs),
        "combined_pairs": str(combined),
        "ok": True,
    }
    (ROOT / "MANIFEST.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    status = {}
    if STATUS_PATH.is_file():
        status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    status["os_rf_mendeley"] = {
        "ok": True,
        "path": str(canonical),
        "license_claimed": "CC BY 4.0",
        "doi": "10.17632/2xyz5rwhcn.1",
        "usable_rows": len(rows),
        "pairs": len(pairs),
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

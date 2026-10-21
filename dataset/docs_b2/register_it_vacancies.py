#!/usr/bin/env python3
"""Register IT_vacancies_full as replacement for dead Kaggle DE source."""
from __future__ import annotations

import csv
import json
import random
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path("/root/hakaton/dataset/raw_sources/danila_hh/it_vacancies_kaggle_alt")
LABELS = Path("/root/hakaton/dataset/raw_sources/danila_hh/labels")
STATUS = Path("/root/hakaton/dataset/raw_sources/danila_hh/SOURCES_STATUS.json")
SEED = 20261009
LIMIT_ROWS = 4000


def tokenize(text: str) -> set[str]:
    toks = re.findall(r"[A-Za-zА-Яа-яЁё0-9+#.]{2,}", (text or "").lower())
    stop = {"и", "в", "на", "по", "для", "the", "and", "with", "опыт", "работа"}
    return {t for t in toks if t not in stop}


def pick(row: dict, keys: list[str]) -> str:
    lower = {k.lower(): k for k in row}
    for want in keys:
        if want.lower() in lower:
            v = row.get(lower[want.lower()])
            if v:
                return str(v)
    return ""


def main() -> None:
    random.seed(SEED)
    csv.field_size_limit(min(sys.maxsize, 50_000_000))
    ROOT.mkdir(parents=True, exist_ok=True)

    zips = list(ROOT.glob("*.zip"))
    if not zips:
        raise SystemExit("no zip in it_vacancies_kaggle_alt")
    extract = ROOT / "extracted"
    extract.mkdir(exist_ok=True)
    with zipfile.ZipFile(zips[0], "r") as zf:
        zf.extractall(extract)
    csvs = list(extract.rglob("*.csv"))
    if not csvs:
        raise SystemExit("no csv in zip")
    csv_path = csvs[0]

    # sniff delimiter
    with csv_path.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(8192)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delim = dialect.delimiter
    except csv.Error:
        delim = ","

    rows_raw = []
    with csv_path.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        cols = reader.fieldnames or []
        for row in reader:
            rows_raw.append(row)
            if len(rows_raw) >= LIMIT_ROWS:
                break

    usable = []
    for row in rows_raw:
        name = pick(row, ["name", "title", "job_title", "vacancy", "position"])
        desc = pick(
            row,
            [
                "description",
                "desc",
                "snippet",
                "responsibility",
                "responsibilities",
                "duties",
            ],
        )
        skills = pick(
            row,
            ["key_skills", "skills", "raw_skills", "tech_stack", "tech_stackt", "requirement", "requirements"],
        )
        need = (name + "\n" + desc).strip()
        cand = skills if skills else (desc[:400] if desc else "")
        if len(need) < 40 or len(cand) < 5:
            continue
        if need.strip() == cand.strip():
            continue
        usable.append({"need": need, "cand": cand, "skills": tokenize(cand)})

    pairs = []
    for i, r in enumerate(usable[:500]):
        pairs.append(
            {
                "pair_id": f"itvac-pos-{i}",
                "need_text": r["need"][:5000],
                "candidate_text": r["cand"][:3000],
                "label": "relevant",
                "label_origin": "team_rule",
                "rule": "it_vacancies_skills_vs_description",
                "source": "IT_vacancies_full_alt_for_dead_kaggle",
            }
        )
    neg = 0
    attempts = 0
    while neg < 500 and attempts < 30000 and len(usable) >= 2:
        attempts += 1
        a, b = random.sample(usable, 2)
        if len(a["skills"] & b["skills"]) > 3:
            continue
        pairs.append(
            {
                "pair_id": f"itvac-neg-{neg}",
                "need_text": a["need"][:5000],
                "candidate_text": b["cand"][:3000],
                "label": "not_relevant",
                "label_origin": "heuristic",
                "rule": "it_vacancies_cross",
                "source": "IT_vacancies_full_alt_for_dead_kaggle",
            }
        )
        neg += 1

    random.shuffle(pairs)
    for i, p in enumerate(pairs):
        p["split"] = "train" if i < int(len(pairs) * 0.8) else "test"

    LABELS.mkdir(parents=True, exist_ok=True)
    out_pairs = LABELS / "candidate_need_pairs_itvac.jsonl"
    with out_pairs.open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    combined = LABELS / "candidate_need_pairs_combined.jsonl"
    parts = []
    for name in (
        "candidate_need_pairs_v2.jsonl",
        "candidate_need_pairs_osrf.jsonl",
        "candidate_need_pairs_itvac.jsonl",
    ):
        p = LABELS / name
        if p.is_file():
            parts.extend([ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()])
    with combined.open("w", encoding="utf-8") as f:
        for line in parts:
            f.write(line + "\n")

    meta = {
        "ok": True,
        "replaces": "olkhovaya/hh-ru-data-engineer-jobs-june-2026 (404)",
        "zip": str(zips[0]),
        "csv": str(csv_path),
        "csv_bytes": csv_path.stat().st_size,
        "delimiter": delim,
        "columns": cols,
        "rows_loaded": len(rows_raw),
        "usable_rows": len(usable),
        "pairs": len(pairs),
        "pairs_file": str(out_pairs),
        "note": "User-supplied IT_vacancies_full.csv.zip as Kaggle alt for Danila source #3",
    }
    (ROOT / "MANIFEST.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    st = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.is_file() else {}
    st["data_engineer_kaggle"] = {
        "ok": True,
        "mode": "alternate_user_file",
        "original_url_status": "404",
        "path": str(csv_path),
        "usable_rows": len(usable),
        "pairs": len(pairs),
        "file": "IT_vacancies_full.csv.zip",
    }
    STATUS.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

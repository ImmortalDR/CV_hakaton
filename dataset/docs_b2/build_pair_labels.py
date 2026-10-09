#!/usr/bin/env python3
"""
Build heuristic candidate↔need pairs from Textovic vacancies (Danila B2).

Labels are NOT expert fitness judgments:
  - positive: same vacancy skills used as both need and candidate (self-match sanity)
  - negative: shuffled cross-vacancy mismatch on skill tokens
  - unknown: reserved for human review queue

Does not touch the FSP eval package builds/ or train production matching.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

ROOT = Path("/root/hakaton/dataset")
REPO = ROOT / "raw_sources/danila_hh/textovic/repo"
OUT = ROOT / "raw_sources/danila_hh/labels"
SEED = 20261009


def _find_data_file() -> Path:
    preferred = REPO / "cleaned_data.csv"
    if preferred.is_file():
        return preferred
    for p in REPO.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".parquet", ".json", ".jsonl", ".csv"}:
            if ".cache" in p.parts:
                continue
            return p
    raise FileNotFoundError(f"No data file under {REPO}")


def _load_rows(path: Path, limit: int = 3000) -> list[dict]:
    if path.suffix.lower() == ".csv":
        import csv
        import sys

        csv.field_size_limit(min(sys.maxsize, 10_000_000))
        # Large file: stream first `limit` rows only
        with path.open(encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                rows.append(dict(row))
                if len(rows) >= limit:
                    break
        return rows
    if path.suffix.lower() == ".parquet":
        try:
            import pyarrow.parquet as pq

            table = pq.read_table(path)
            cols = table.column_names
            n = min(limit, table.num_rows)
            rows = []
            for i in range(n):
                rows.append({c: table.column(c)[i].as_py() for c in cols})
            return rows
        except Exception as e:
            raise RuntimeError(f"parquet read failed: {e}") from e
    if path.suffix.lower() == ".jsonl":
        rows = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
                if len(rows) >= limit:
                    break
        return rows
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data[:limit]
        raise RuntimeError("unsupported json shape")
    raise RuntimeError(f"unsupported {path}")


def _text(row: dict) -> str:
    parts = []
    for key in (
        "description",
        "desc",
        "text",
        "name",
        "title",
        "key_skills",
        "skills",
        "snippet",
    ):
        v = row.get(key)
        if v is None:
            continue
        if isinstance(v, list):
            parts.append(" ".join(str(x) for x in v))
        else:
            parts.append(str(v))
    return "\n".join(parts)


def _skill_tokens(text: str) -> set[str]:
    toks = re.findall(r"[A-Za-zА-Яа-яЁё0-9+#.]{2,}", text.lower())
    stop = {"и", "в", "на", "по", "для", "the", "and", "with", "опыт", "работа"}
    return {t for t in toks if t not in stop}


def main() -> None:
    random.seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    data_path = _find_data_file()
    rows = _load_rows(data_path, limit=2500)
    usable = [r for r in rows if len(_text(r)) > 80]
    if len(usable) < 50:
        raise RuntimeError(f"too few usable rows: {len(usable)} from {data_path}")

    pairs = []
    # positives: self
    for i, r in enumerate(usable[:400]):
        t = _text(r)
        pairs.append(
            {
                "pair_id": f"pos-{i}",
                "need_text": t[:4000],
                "candidate_text": t[:4000],
                "label": "relevant",
                "label_origin": "team_rule",
                "rule": "self_match_same_vacancy_text",
                "source_file": str(data_path),
            }
        )
    # negatives: cross
    for i in range(400):
        a, b = random.sample(usable, 2)
        ta, tb = _text(a), _text(b)
        if len(_skill_tokens(ta) & _skill_tokens(tb)) > 12:
            continue
        pairs.append(
            {
                "pair_id": f"neg-{i}",
                "need_text": ta[:4000],
                "candidate_text": tb[:4000],
                "label": "not_relevant",
                "label_origin": "heuristic",
                "rule": "cross_vacancy_low_token_overlap",
                "source_file": str(data_path),
            }
        )

    random.shuffle(pairs)
    n = len(pairs)
    split_at = int(n * 0.8)
    for i, p in enumerate(pairs):
        p["split"] = "train" if i < split_at else "test"

    out_path = OUT / "candidate_need_pairs.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    summary = {
        "data_file": str(data_path),
        "rows_loaded": len(rows),
        "usable": len(usable),
        "pairs": n,
        "train": sum(1 for p in pairs if p["split"] == "train"),
        "test": sum(1 for p in pairs if p["split"] == "test"),
        "by_label": {
            "relevant": sum(1 for p in pairs if p["label"] == "relevant"),
            "not_relevant": sum(1 for p in pairs if p["label"] == "not_relevant"),
        },
        "warning": "Not expert fitness labels; pilot only. Do not claim market validity.",
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("OK", summary)


if __name__ == "__main__":
    main()

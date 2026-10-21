#!/usr/bin/env python3
"""
Honest-er heuristic pairs from Textovic CSV (Danila B2).

Positive != identical strings:
  need = vacancy description (+ title)
  candidate = skills / key_skills / requirements snippet only
Negative = skills from another vacancy vs this description (low skill overlap).
Unknown queue = medium overlap (for human later).

Still not expert labels.
"""
from __future__ import annotations

import csv
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path("/root/hakaton/dataset")
CSV_PATH = ROOT / "raw_sources/danila_hh/textovic/repo/cleaned_data.csv"
OUT = ROOT / "raw_sources/danila_hh/labels"
SEED = 20261009
LIMIT = 3000


def tokenize(text: str) -> set[str]:
    toks = re.findall(r"[A-Za-zА-Яа-яЁё0-9+#.]{2,}", (text or "").lower())
    stop = {"и", "в", "на", "по", "для", "the", "and", "with", "опыт", "работа", "года", "лет"}
    return {t for t in toks if t not in stop}


def pick(row: dict, keys: list[str]) -> str:
    for k in keys:
        for rk, rv in row.items():
            if rk and rk.lower() == k.lower() and rv:
                return str(rv)
    return ""


def need_text(row: dict) -> str:
    title = pick(row, ["name", "title", "vacancy", "position"])
    desc = pick(row, ["description", "desc", "text", "snippet", "responsibility", "responsibilities"])
    return (title + "\n" + desc).strip()


def cand_text(row: dict) -> str:
    skills = pick(row, ["key_skills", "skills", "skill", "tags", "keySkills"])
    req = pick(row, ["requirement", "requirements", "candidate_requirement"])
    # Prefer skills-only profile; fallback to short requirements
    parts = [p for p in (skills, req) if p]
    if not parts:
        # last resort: first 400 chars of description as "resume-like" — mark weak
        d = pick(row, ["description", "desc", "text"])
        return d[:400]
    return "\n".join(parts)[:3000]


def main() -> None:
    random.seed(SEED)
    csv.field_size_limit(min(sys.maxsize, 10_000_000))
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    with CSV_PATH.open(encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            n, c = need_text(row), cand_text(row)
            if len(n) < 80 or len(c) < 10:
                continue
            # skip if candidate == need (would recreate accuracy=1 trap)
            if n.strip() == c.strip():
                continue
            rows.append({"need": n, "cand": c, "skills": tokenize(c), "need_tok": tokenize(n)})
            if len(rows) >= LIMIT:
                break
    if len(rows) < 80:
        raise SystemExit(f"too few rows: {len(rows)}")

    pairs = []
    # positives: skills of vacancy vs its description
    for i, r in enumerate(rows[:500]):
        pairs.append(
            {
                "pair_id": f"pos-v2-{i}",
                "need_text": r["need"][:5000],
                "candidate_text": r["cand"][:3000],
                "label": "relevant",
                "label_origin": "team_rule",
                "rule": "same_vacancy_skills_vs_description",
            }
        )
    # negatives: low skill overlap
    neg = 0
    attempts = 0
    while neg < 500 and attempts < 8000:
        attempts += 1
        a, b = random.sample(rows, 2)
        ov = len(a["skills"] & b["skills"])
        if ov > 3:
            continue
        pairs.append(
            {
                "pair_id": f"neg-v2-{neg}",
                "need_text": a["need"][:5000],
                "candidate_text": b["cand"][:3000],
                "label": "not_relevant",
                "label_origin": "heuristic",
                "rule": f"cross_vacancy_skill_overlap_{ov}",
            }
        )
        neg += 1
    # unknown queue for humans
    unk = 0
    attempts = 0
    while unk < 80 and attempts < 8000:
        attempts += 1
        a, b = random.sample(rows, 2)
        ov = len(a["skills"] & b["skills"])
        if ov < 4 or ov > 10:
            continue
        pairs.append(
            {
                "pair_id": f"unk-v2-{unk}",
                "need_text": a["need"][:5000],
                "candidate_text": b["cand"][:3000],
                "label": "unknown",
                "label_origin": "heuristic",
                "rule": f"medium_overlap_{ov}_needs_human",
            }
        )
        unk += 1

    random.shuffle(pairs)
    # split only labeled (exclude unknown from train metrics later)
    labeled = [p for p in pairs if p["label"] != "unknown"]
    for i, p in enumerate(labeled):
        p["split"] = "train" if i < int(len(labeled) * 0.8) else "test"
    for p in pairs:
        if p["label"] == "unknown":
            p["split"] = "human_queue"

    out_path = OUT / "candidate_need_pairs_v2.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    summary = {
        "version": 2,
        "source_csv": str(CSV_PATH),
        "rows_used": len(rows),
        "pairs": len(pairs),
        "by_label": {
            k: sum(1 for p in pairs if p["label"] == k)
            for k in ("relevant", "not_relevant", "unknown")
        },
        "train_labeled": sum(1 for p in pairs if p.get("split") == "train"),
        "test_labeled": sum(1 for p in pairs if p.get("split") == "test"),
        "human_queue": sum(1 for p in pairs if p.get("split") == "human_queue"),
        "warning": "Heuristic/team_rule only; unknown queue for humans. Not market validity.",
    }
    (OUT / "SUMMARY_v2.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # keep human queue extract
    with (OUT / "human_queue_v2.jsonl").open("w", encoding="utf-8") as f:
        for p in pairs:
            if p["label"] == "unknown":
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print("OK", summary)


if __name__ == "__main__":
    main()

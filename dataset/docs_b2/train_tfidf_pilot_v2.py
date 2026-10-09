#!/usr/bin/env python3
"""TF-IDF pilot on v2 pairs (skills≠description). Skip unknown."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

PAIRS = Path("/root/hakaton/dataset/raw_sources/danila_hh/labels/candidate_need_pairs_v2.jsonl")
OUT = Path("/root/hakaton/dataset/raw_sources/danila_hh/models")


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-zА-Яа-яЁё0-9+#.]{2,}", text.lower())


def build_idf(docs: list[str]) -> dict[str, float]:
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(tokenize(d)))
    n = len(docs)
    return {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}


def vec(text: str, idf: dict[str, float]) -> dict[str, float]:
    toks = tokenize(text)
    tf = Counter(toks)
    L = max(len(toks), 1)
    return {t: (tf[t] / L) * idf.get(t, 0.0) for t in tf}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) & set(b)
    if not keys:
        return 0.0
    num = sum(a[k] * b[k] for k in keys)
    da = math.sqrt(sum(v * v for v in a.values()))
    db = math.sqrt(sum(v * v for v in b.values()))
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


def main() -> None:
    pairs = [json.loads(l) for l in PAIRS.read_text(encoding="utf-8").splitlines() if l.strip()]
    labeled = [p for p in pairs if p["label"] in ("relevant", "not_relevant")]
    train = [p for p in labeled if p.get("split") == "train"]
    test = [p for p in labeled if p.get("split") == "test"]
    docs = [p["need_text"] for p in train] + [p["candidate_text"] for p in train]
    idf = build_idf(docs)

    scores_pos, scores_neg = [], []
    for p in train:
        s = cosine(vec(p["need_text"], idf), vec(p["candidate_text"], idf))
        (scores_pos if p["label"] == "relevant" else scores_neg).append(s)
    thr = 0.5 * (
        (sum(scores_pos) / max(len(scores_pos), 1))
        + (sum(scores_neg) / max(len(scores_neg), 1))
    )

    def evaluate(name: str, rows: list[dict]) -> dict:
        tp = fp = tn = fn = 0
        scores = []
        for p in rows:
            s = cosine(vec(p["need_text"], idf), vec(p["candidate_text"], idf))
            scores.append(s)
            pred_pos = s >= thr
            gold_pos = p["label"] == "relevant"
            if pred_pos and gold_pos:
                tp += 1
            elif pred_pos and not gold_pos:
                fp += 1
            elif not pred_pos and not gold_pos:
                tn += 1
            else:
                fn += 1
        return {
            "split": name,
            "n": len(rows),
            "threshold": thr,
            "mean_score": sum(scores) / max(len(scores), 1),
            "accuracy": (tp + tn) / max(len(rows), 1),
            "precision_relevant": tp / (tp + fp) if (tp + fp) else None,
            "recall_relevant": tp / (tp + fn) if (tp + fn) else None,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        }

    report = {
        "method": "tfidf_cosine_v2_skills_vs_description",
        "warning": "Heuristic labels; not expert/market validity. v1 accuracy=1 was self-match artifact.",
        "train_score_means": {
            "relevant": sum(scores_pos) / max(len(scores_pos), 1),
            "not_relevant": sum(scores_neg) / max(len(scores_neg), 1),
        },
        "human_queue_pairs": sum(1 for p in pairs if p.get("label") == "unknown"),
        "train": evaluate("train", train),
        "test": evaluate("test", test),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tfidf_pilot_report_v2.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

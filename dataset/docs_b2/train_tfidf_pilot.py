#!/usr/bin/env python3
"""Pilot: TF-IDF + cosine on heuristic pairs. Stdlib + optional sklearn."""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

PAIRS = Path("/root/hakaton/dataset/raw_sources/danila_hh/labels/candidate_need_pairs.jsonl")
OUT = Path("/root/hakaton/dataset/raw_sources/danila_hh/models")


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-zА-Яа-яЁё0-9+#.]{2,}", text.lower())


def tfidf_vectors(docs: list[str]) -> tuple[list[dict[str, float]], dict[str, float]]:
    tokenized = [tokenize(d) for d in docs]
    df: Counter[str] = Counter()
    for toks in tokenized:
        df.update(set(toks))
    n = len(docs)
    idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
    vecs = []
    for toks in tokenized:
        tf = Counter(toks)
        L = max(len(toks), 1)
        vecs.append({t: (tf[t] / L) * idf[t] for t in tf})
    return vecs, idf


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) & set(b)
    num = sum(a[k] * b[k] for k in keys)
    da = math.sqrt(sum(v * v for v in a.values()))
    db = math.sqrt(sum(v * v for v in b.values()))
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


def main() -> None:
    pairs = []
    with PAIRS.open(encoding="utf-8") as f:
        for line in f:
            pairs.append(json.loads(line))
    train = [p for p in pairs if p["split"] == "train"]
    test = [p for p in pairs if p["split"] == "test"]

    # Fit IDF on train texts only
    docs = [p["need_text"] for p in train] + [p["candidate_text"] for p in train]
    _, idf = tfidf_vectors(docs)

    def vec(text: str) -> dict[str, float]:
        toks = tokenize(text)
        tf = Counter(toks)
        L = max(len(toks), 1)
        return {t: (tf[t] / L) * idf.get(t, 0.0) for t in tf}

    scores_pos = []
    scores_neg = []
    for p in train:
        s = cosine(vec(p["need_text"]), vec(p["candidate_text"]))
        if p["label"] == "relevant":
            scores_pos.append(s)
        else:
            scores_neg.append(s)
    # threshold: midpoint of means
    thr = 0.5 * (
        (sum(scores_pos) / max(len(scores_pos), 1))
        + (sum(scores_neg) / max(len(scores_neg), 1))
    )

    def eval_split(name: str, rows: list[dict]) -> dict:
        tp = fp = tn = fn = 0
        for p in rows:
            s = cosine(vec(p["need_text"]), vec(p["candidate_text"]))
            pred = "relevant" if s >= thr else "not_relevant"
            gold = p["label"]
            if pred == "relevant" and gold == "relevant":
                tp += 1
            elif pred == "relevant" and gold != "relevant":
                fp += 1
            elif pred != "relevant" and gold != "relevant":
                tn += 1
            else:
                fn += 1
        prec = tp / (tp + fp) if (tp + fp) else None
        rec = tp / (tp + fn) if (tp + fn) else None
        acc = (tp + tn) / max(len(rows), 1)
        return {
            "split": name,
            "n": len(rows),
            "threshold": thr,
            "accuracy": acc,
            "precision_relevant": prec,
            "recall_relevant": rec,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        }

    report = {
        "method": "tfidf_cosine_stdlib",
        "warning": "Heuristic labels + self-match positives — NOT market validity.",
        "train_score_means": {
            "relevant": sum(scores_pos) / max(len(scores_pos), 1),
            "not_relevant": sum(scores_neg) / max(len(scores_neg), 1),
        },
        "train": eval_split("train", train),
        "test": eval_split("test", test),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tfidf_pilot_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("OK", json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

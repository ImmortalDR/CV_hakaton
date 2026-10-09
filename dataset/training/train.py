"""CPU baseline and learned pair classifier. Source behaviour is not ground truth fit."""

from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import time
import joblib
import numpy as np
import scipy
from scipy import sparse
import sklearn
from sklearn.feature_extraction.text import HashingVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score, ndcg_score
from prepare import clean, write_json


def pair_features(vectorizer, rows):
    a = vectorizer.transform([clean(p["candidate_text"]) for p in rows])
    b = vectorizer.transform([clean(p["need_text"]) for p in rows])
    cosine = np.asarray(a.multiply(b).sum(axis=1)).ravel()
    features = sparse.hstack(
        [a.multiply(b), abs(a - b), sparse.csr_matrix(cosine[:, None])], format="csr"
    )
    return features, cosine, b


def remove_near_duplicates(splits):
    """Fixed label-blind guard, independent of fitted model vocabulary."""
    h = HashingVectorizer(
        n_features=2**20, alternate_sign=False, ngram_range=(2, 3), binary=True
    )
    removed = {}
    # Test is also isolated from validation, not just training.
    for target, references in [
        ("validation", ["train"]),
        ("test", ["train", "validation"]),
    ]:
        ref = [p for s in references for p in splits[s]]
        rows = splits[target]
        drop = set()
        for field in ("candidate_text", "need_text"):
            texts = sorted({p[field] for p in ref})
            if not rows or not texts:
                continue
            r = h.transform(texts)
            for start in range(0, len(rows), 128):
                q = h.transform([p[field] for p in rows[start : start + 128]])
                maximum = (q @ r.T).max(axis=1).toarray().ravel()
                drop.update(start + i for i, x in enumerate(maximum) if x >= 0.95)
        removed[target] = len(drop)
        splits[target] = [p for i, p in enumerate(rows) if i not in drop]
    return removed


def metrics(rows, scores):
    y = np.array([p["label"] for p in rows])
    groups = defaultdict(list)
    for i, p in enumerate(rows):
        groups[(p["job_id"], p["need_text"])].append(i)
    ndcg, precision = [], []
    for indices in groups.values():
        if len(indices) < 2 or len(set(y[indices])) < 2:
            continue
        truth, score = y[indices], scores[indices]
        ndcg.append(float(ndcg_score(truth[None, :], score[None, :], k=5)))
        # Fractional expectation at the cutoff avoids order-dependent tied scores.
        k = min(5, len(indices))
        cut = np.sort(score)[-k]
        higher, tied = score > cut, score == cut
        precision.append(
            float((truth[higher].sum() + (k - higher.sum()) * truth[tied].mean()) / k)
        )
    return {
        "n": len(rows),
        "positives": int(y.sum()),
        "positive_fraction": float(y.mean()) if len(y) else None,
        "average_precision": (
            float(average_precision_score(y, scores)) if len(set(y)) == 2 else None
        ),
        "roc_auc": float(roc_auc_score(y, scores)) if len(set(y)) == 2 else None,
        "mixed_vacancy_pools": len(ndcg),
        "ndcg_at_5": float(np.mean(ndcg)) if ndcg else None,
        "precision_at_min_5_n": float(np.mean(precision)) if precision else None,
    }


def bootstrap(rows, learned, baseline, repeats=500):
    groups = defaultdict(list)
    for i, p in enumerate(rows):
        groups[p["group_id"]].append(i)
    keys = sorted(groups)
    rng = np.random.default_rng(20261009)
    deltas = []
    y = np.array([p["label"] for p in rows])
    for _ in range(repeats):
        ix = np.concatenate(
            [groups[keys[i]] for i in rng.integers(0, len(keys), len(keys))]
        )
        if len(set(y[ix])) < 2:
            continue
        deltas.append(
            average_precision_score(y[ix], learned[ix])
            - average_precision_score(y[ix], baseline[ix])
        )
    return {
        "unit": "connected_component",
        "components": len(keys),
        "valid_repeats": len(deltas),
        "ap_gain_95_percentile_ci": (
            np.quantile(deltas, [0.025, 0.975]).tolist() if deltas else None
        ),
    }


def assert_isolated(splits):
    for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
        for key in (
            "pair_id",
            "person_id",
            "cv_id",
            "job_id",
            "candidate_text",
            "need_text",
            "group_id",
        ):
            if {p[key] for p in splits[a]} & {p[key] for p in splits[b]}:
                raise ValueError(f"Split leakage: {a}/{b}/{key}")


def train(root, out):
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    raw = (root / "pairs.jsonl").read_bytes()
    source_report = json.loads((root / "pairs-report.json").read_text())
    if hashlib.sha256(raw).hexdigest() != source_report["pairs_sha256"]:
        raise ValueError("Frozen pairs hash mismatch")
    rows = [json.loads(line) for line in raw.splitlines()]
    splits = {
        s: [p for p in rows if p["split"] == s] for s in ("train", "validation", "test")
    }
    assert_isolated(splits)
    removed = remove_near_duplicates(splits)
    assert_isolated(splits)
    frozen = {
        "pairs_sha256": source_report["pairs_sha256"],
        "near_duplicate_threshold": 0.95,
        "removed": removed,
        "splits": {s: [p["pair_id"] for p in splits[s]] for s in splits},
    }
    write_json(out / "split-manifest.json", frozen)
    counts = {
        s: {str(y): sum(p["label"] == y for p in splits[s]) for y in (0, 1)}
        for s in splits
    }
    # Safety gate, never silently switch to an easier split.
    if any(n < 10 for c in counts.values() for n in c.values()):
        write_json(
            out / "training-report.json",
            {
                "status": "insufficient_independent_classes",
                "counts": counts,
                "near_duplicates_removed": removed,
                "production_promotion_allowed": False,
            },
        )
        raise ValueError(
            "Need >=10 examples of each class in each independent split; see report"
        )
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_features=12000,
        sublinear_tf=True,
        dtype=np.float64,
    )
    vectorizer.fit(
        sorted({p[k] for p in splits["train"] for k in ("candidate_text", "need_text")})
    )
    features = {s: pair_features(vectorizer, ps) for s, ps in splits.items()}
    labels = {s: np.array([p["label"] for p in ps]) for s, ps in splits.items()}
    candidates = []
    best = None
    best_ap = -1
    for C in (0.1, 1.0, 10.0):
        model = LogisticRegression(
            C=C,
            class_weight="balanced",
            solver="liblinear",
            max_iter=1000,
            random_state=20261009,
        )
        model.fit(features["train"][0], labels["train"])
        if int(model.n_iter_[0]) >= model.max_iter:
            raise RuntimeError("Pair classifier did not converge")
        score = model.decision_function(features["validation"][0])
        ap = float(average_precision_score(labels["validation"], score))
        candidates.append(
            {"C": C, "validation_ap": ap, "iterations": int(model.n_iter_[0])}
        )
        if ap > best_ap:
            best_ap = ap
            best = model
    # Same fixed C for the job-only control; no test-driven choices.
    control = LogisticRegression(
        C=best.C,
        class_weight="balanced",
        solver="liblinear",
        max_iter=1000,
        random_state=20261009,
    )
    control.fit(features["train"][2], labels["train"])
    if int(control.n_iter_[0]) >= control.max_iter:
        raise RuntimeError("Job-only control did not converge")
    artifact = {
        "vectorizer": vectorizer,
        "classifier": best,
        "target": source_report["target"],
        "production_promotion_allowed": False,
        "pairs_sha256": source_report["pairs_sha256"],
    }
    joblib.dump(artifact, out / "model.joblib", compress=3)
    restored = joblib.load(
        out / "model.joblib"
    )  # Only our freshly created local artifact.
    learned = {s: best.decision_function(features[s][0]) for s in splits}
    replay = restored["classifier"].decision_function(
        pair_features(restored["vectorizer"], splits["test"])[0]
    )
    if not np.allclose(replay, learned["test"], rtol=0, atol=1e-12):
        raise AssertionError("Reload mismatch")
    scores = {
        s: {
            "learned_pair": metrics(splits[s], learned[s]),
            "tfidf_cosine": metrics(splits[s], features[s][1]),
            "job_text_only": metrics(
                splits[s], control.decision_function(features[s][2])
            ),
            "constant": metrics(splits[s], np.zeros(len(splits[s]))),
        }
        for s in ("validation", "test")
    }
    ci = bootstrap(splits["test"], learned["test"], features["test"][1])
    # Model weights are trained even when the experiment doesn't justify promotion.
    report = {
        "status": "trained_offline",
        "target": source_report["target"],
        "counts": counts,
        "near_duplicates_removed": removed,
        "vocabulary_size": len(vectorizer.vocabulary_),
        "selected_C": best.C,
        "selection_metric": "validation_average_precision",
        "candidates": candidates,
        "scores": scores,
        "bootstrap": ci,
        "artifact_reload_equal": True,
        "production_promotion_allowed": False,
        "promotion_blockers": [
            "Actor/meaning of source refusal unresolved; labels are not suitability.",
            "Historical broad-IT cohort is not validated for current Python/Data matching.",
            "No independent human qualification labels or certification.",
        ],
        "pairs_sha256": source_report["pairs_sha256"],
        "model_sha256": hashlib.sha256((out / "model.joblib").read_bytes()).hexdigest(),
        "split_manifest_sha256": hashlib.sha256(
            (out / "split-manifest.json").read_bytes()
        ).hexdigest(),
        "versions": {
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "joblib": joblib.__version__,
        },
        "seconds": time.monotonic() - start,
        "max_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "code_sha256": {
            name: hashlib.sha256(
                Path(__file__).with_name(name).read_bytes()
            ).hexdigest()
            for name in ("prepare.py", "pairs.py", "train.py")
        },
    }
    write_json(out / "training-report.json", report)
    with (out / "test-predictions.jsonl").open("x") as f:
        for i, p in enumerate(splits["test"]):
            f.write(
                json.dumps(
                    {
                        "pair_id": p["pair_id"],
                        "label": p["label"],
                        "score": float(learned["test"][i]),
                        "baseline": float(features["test"][1][i]),
                    }
                )
                + "\n"
            )
    print(json.dumps(report, ensure_ascii=False, indent=2))


def predict(model_path, candidate, need):
    # Do not load downloaded/untrusted pickle/joblib files.
    m = joblib.load(model_path)
    if len(clean(candidate)) < 30 or len(clean(need)) < 60:
        return {
            "observed_event_score": None,
            "target": m["target"],
            "production_promotion_allowed": False,
            "status": "insufficient_professional_text",
        }
    rows = [{"candidate_text": candidate, "need_text": need}]
    value = float(
        m["classifier"].decision_function(pair_features(m["vectorizer"], rows)[0])[0]
    )
    return {
        "observed_event_score": value,
        "target": m["target"],
        "production_promotion_allowed": False,
        "meaning": "Uncalibrated historical event score; not competence, grade or verified match.",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    t = sub.add_parser("train")
    t.add_argument("--root", type=Path, required=True)
    t.add_argument("--out", type=Path, required=True)
    q = sub.add_parser("predict")
    q.add_argument("--model", type=Path, required=True)
    q.add_argument("--candidate-file", type=Path, required=True)
    q.add_argument("--need-file", type=Path, required=True)
    a = p.parse_args()
    if a.command == "train":
        train(a.root, a.out)
    else:
        print(
            json.dumps(
                predict(a.model, a.candidate_file.read_text(), a.need_file.read_text()),
                ensure_ascii=False,
            )
        )

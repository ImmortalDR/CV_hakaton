import importlib.util
import math
import sys
from pathlib import Path
from statistics import mean

from .common import records, write_json


def evaluate(root):
    root = Path(root)
    # Snapshot has only the pure matching and bank modules, no database or API.
    name = "fsp_eval_snapshot"
    spec = importlib.util.spec_from_file_location(
        name,
        root / "snapshot/mvp/__init__.py",
        submodule_search_locations=[str(root / "snapshot/mvp")],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    matching = importlib.import_module(name + ".matching")
    candidates = {
        r["record_id"]: r["payload"]
        for r in records(root / "data/synthetic/candidates.jsonl")
    }
    needs = {
        r["record_id"]: r["payload"]
        for r in records(root / "data/synthetic/needs.jsonl")
    }
    # Labels are opened by the evaluator only; candidate inputs never contain them.
    predictions = []
    pools = list(records(root / "data/synthetic/pools.jsonl"))
    for row in pools:
        pool = row["payload"]
        criteria = needs[pool["need_id"]]["criteria"]
        ranked = []
        for cid in pool["candidate_ids"]:
            c = candidates[cid]
            if matching.eligible(c, criteria):
                ranked.append(
                    {"id": cid, **c, "match": matching.rank_candidate(c, criteria)}
                )
        ranked = matching.group_sort(ranked)
        predictions.append(
            {
                "pool_id": row["record_id"],
                "need_id": pool["need_id"],
                "split": row["split"],
                "returned": [
                    {
                        "candidate_id": c["id"],
                        "score": c["match"]["score"],
                        "facts": c["match"]["facts"],
                    }
                    for c in ranked
                ],
            }
        )
    labels = {
        (r["payload"]["need_id"], r["payload"]["candidate_id"]): r["payload"]
        for r in records(root / "labels/matching.jsonl")
    }
    scores = []
    for row, prediction in zip(pools, predictions):
        qid = row["payload"]["need_id"]
        gold = {cid: labels[qid, cid] for cid in row["payload"]["candidate_ids"]}
        order = [r["candidate_id"] for r in prediction["returned"]]
        top = order[:5]
        positives = sum(g["decision"] == "recommend" for g in gold.values())
        hits = sum(gold[c]["decision"] == "recommend" for c in top)
        unknown = sum(gold[c]["decision"] == "insufficient_evidence" for c in top)
        # This explicitly conditional metric excludes unknown; never calls unknown a negative.
        judged_order = [cid for cid in order if gold[cid]["relevance"] is not None][:5]
        dcg = sum(
            gold[cid]["relevance"] / math.log2(i + 2)
            for i, cid in enumerate(judged_order)
        )
        idcg = sum(1 / math.log2(i + 2) for i in range(min(5, positives)))
        explained, grounded = 0, 0
        for item in prediction["returned"][:5]:
            expected = {
                f["requirement"]: f["state"]
                for f in gold[item["candidate_id"]]["requirements"]
            }
            for fact in item["facts"]:
                if fact["skill"] in expected:
                    explained += 1
                    grounded += fact["state"] == expected[fact["skill"]]
        scores.append(
            {
                "pool_id": row["record_id"],
                "split": row["split"],
                "scenario": row["payload"]["scenario"],
                "returned_count": len(order),
                "positives_in_pool": positives,
                "top5_relevant": hits,
                "precision_at_5_fixed": hits / 5,
                "precision_at_5_served": hits / len(top) if top else None,
                "unknown_in_top5": unknown,
                "mandatory_unmet_in_top5": sum(
                    gold[c]["decision"] == "reject" for c in top
                ),
                "judged_fraction_top5": (
                    (len(top) - unknown) / len(top) if top else None
                ),
                "ndcg_at_5_judged_only": dcg / idcg if idcg else None,
                "empty_when_no_confirmed_match": not order if positives == 0 else None,
                "grounded_fact_count": grounded,
                "checked_fact_count": explained,
            }
        )
    summary = {}
    for split in ["dev", "test"]:
        rows = [r for r in scores if r["split"] == split]
        summary[split] = {
            "queries": len(rows),
            "mean_precision_at_5_fixed": mean(r["precision_at_5_fixed"] for r in rows),
            "mandatory_unmet_in_top5": sum(r["mandatory_unmet_in_top5"] for r in rows),
            "unknown_in_top5": sum(r["unknown_in_top5"] for r in rows),
            "queries_with_empty_output": sum(r["returned_count"] == 0 for r in rows),
        }
    # Import cache must not contaminate another build evaluated in the same process.
    for key in list(sys.modules):
        if key == name or key.startswith(name + "."):
            del sys.modules[key]
    return {
        "status": "measured",
        "scope": "pure production matching functions; not live API",
        "summary": summary,
        "queries": scores,
        "limitations": [
            "Strict full-recommendation rubric; application also returns partial matches in its main list.",
            "P@5 fixed divides by 5; served precision reported separately; empty output is not precision=1.",
            "nDCG is judged-only and excludes unknown, not a full-pool relevance score.",
            "Scenario families appear in both splits; entity IDs are disjoint, not a claim of real-world generalization.",
        ],
    }, predictions

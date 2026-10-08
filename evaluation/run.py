"""Run frozen synthetic validation; writes measured results, including errors."""

import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from statistics import mean

from fsp import bank
from fsp.matching import VERSION as MATCHING_VERSION, eligible, rank_candidate
from evaluation.oracles import solve

ROOT = Path(__file__).parent
# Keep the original published benchmark on its original bank and rubric.
BANK_VERSION = "1.1.0"


def matching():
    data = json.loads((ROOT / "matching_fixtures.json").read_text())
    assert not (
        {p["id"] for p in data["dev"]["candidates"]}
        & {p["id"] for p in data["test"]["candidates"]}
    )
    results = {}
    for split in ("dev", "test"):
        rows = []
        for q in data[split]["queries"]:
            candidates = [
                p for p in data[split]["candidates"] if eligible(p, q["criteria"])
            ]
            scores = {
                p["id"]: rank_candidate(p, q["criteria"])["score"] for p in candidates
            }
            ranked = sorted(candidates, key=lambda p: (-scores[p["id"]], p["id"]))[:5]
            claims = set(q["criteria"]["required_skills"])
            baseline = sorted(
                candidates,
                key=lambda p: (
                    -len(claims & set(p["skills"])),
                    -(p["experience_years"] or 0),
                    p["id"],
                ),
            )[:5]
            ids = [p["id"] for p in ranked]
            bids = [p["id"] for p in baseline]
            relevant = set(q["relevant_ids"])
            rows.append(
                {
                    "query": q["id"],
                    "relevant_ids": sorted(relevant),
                    "top5": ids,
                    "baseline_top5": bids,
                    "p_at_5": len(set(ids) & relevant) / 5,
                    "baseline_p_at_5": len(set(bids) & relevant) / 5,
                    "false_positives": [x for x in ids if x not in relevant],
                    "false_negatives": [x for x in relevant if x not in ids],
                }
            )
        results[split] = {
            "candidates": len(data[split]["candidates"]),
            "queries": len(rows),
            "mean_p_at_5": mean(r["p_at_5"] for r in rows),
            "mean_baseline_p_at_5": mean(r["baseline_p_at_5"] for r in rows),
            "rows": rows,
        }
    return results


def grading():
    personas = json.loads((ROOT / "grade_personas.json").read_text())
    labels = ["unconfirmed", *bank.GRADES]
    matrix = {e: {p: 0 for p in labels} for e in labels}
    details = []
    oracle_checks = 0
    unique = set()
    for person in personas:
        predictions = []
        for variant in range(20):
            predicted = "unconfirmed"
            rng = random.Random(person["id"] + str(variant))
            for grade in bank.GRADES:
                qs = bank.generate(
                    person["specialization"],
                    grade,
                    "eval-" + person["id"] + "-" + str(variant),
                    version=BANK_VERSION,
                )
                unique.add(bank.fingerprint(qs))
                answers = {}
                for q in qs:
                    reference = solve(q)
                    assert abs(float(q["answer"]) - float(reference)) <= 0.005
                    oracle_checks += 1
                    capable = q["family"] in person["known_families"]
                    answers[q["id"]] = (
                        str(reference)
                        if capable and rng.random() >= person["slip_probability"]
                        else "не знаю"
                    )
                if bank.grade_answers(qs, answers, version=BANK_VERSION)["passed"]:
                    predicted = grade
            predictions.append(predicted)
            matrix[person["expected_grade"]][predicted] += 1
        details.append(
            {
                "persona": person["id"],
                "expected": person["expected_grade"],
                "predictions": dict(Counter(predictions)),
                "agreement": predictions.count(person["expected_grade"])
                / len(predictions),
                "variant_stability": max(Counter(predictions).values())
                / len(predictions),
            }
        )
    return {
        "personas": len(personas),
        "variants_per_persona": 20,
        "classifications": len(personas) * 20,
        "oracle_checks": oracle_checks,
        "unique_variants": len(unique),
        "confusion_matrix": matrix,
        "agreement": mean(d["agreement"] for d in details),
        "mean_variant_stability": mean(d["variant_stability"] for d in details),
        "details": details,
    }


def main():
    hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            ROOT / "PROTOCOL.md",
            ROOT / "matching_fixtures.json",
            ROOT / "grade_personas.json",
        ]
    }
    result = {
        "kind": "synthetic_simulation_not_human_validation",
        "bank_version": BANK_VERSION,
        "matching_version": MATCHING_VERSION,
        "fixture_sha256": hashes,
        "matching": matching(),
        "grading": grading(),
        "limitations": [
            "Авторские синтетические метки; внешних экспертов и испытуемых нет.",
            "Веса не обучались; train отсутствует. Dev использован для проверки процедуры.",
            "Параметрические варианты сохраняют известный алгоритм решения; защиты от LLM нет.",
            "Оценка профессиональных грейдов требует независимого пилота с людьми.",
            "Малая выборка и искусственные сценарии не позволяют оценить качество на рынке.",
        ],
    }
    (ROOT / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "test_p_at_5": result["matching"]["test"]["mean_p_at_5"],
                "baseline_p_at_5": result["matching"]["test"]["mean_baseline_p_at_5"],
                "grade_agreement": result["grading"]["agreement"],
                "oracle_checks": result["grading"]["oracle_checks"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

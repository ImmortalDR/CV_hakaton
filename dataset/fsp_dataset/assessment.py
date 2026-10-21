import importlib.util
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from .common import record, source_ref


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generate(writer, root, seed):
    root = Path(root)
    bank = load_module(root / "snapshot/mvp/bank.py", "eval_bank")
    reference = load_module(root / "snapshot/oracles.py", "eval_oracle")
    groups = defaultdict(list)
    items = defaultdict(lambda: defaultdict(list))
    oracle_errors = []
    question_count = 0
    confusion = Counter()
    for spec in bank.SPECS:
        for grade in bank.GRADES:
            for competence in ["weak", "partial", "strong", "noisy"]:
                pid = f"persona:{spec}:{grade}:{competence}"
                for variant in range(20):
                    aid = f"{pid}:{variant}"
                    actual_seed = f"fsp-dataset-{seed}:{aid}"
                    qs = bank.generate(spec, grade, actual_seed)
                    rng = random.Random(actual_seed + ":responses")
                    answers, refs = {}, {}
                    for index, q in enumerate(qs):
                        solved = str(reference.solve(q))
                        refs[q["id"]] = solved
                        question_count += 1
                        if abs(float(solved) - float(q["answer"])) > 0.005:
                            oracle_errors.append({"attempt": aid, "question": q["id"]})
                        capable = competence == "strong" or (
                            competence == "partial" and index % 2 == 0
                        )
                        if competence == "noisy":
                            capable = rng.random() >= 0.20
                        answers[q["id"]] = solved if capable else "не знаю"
                    result = bank.grade_answers(qs, answers)
                    expected = None if competence == "noisy" else competence == "strong"
                    if expected is not None:
                        confusion[(expected, result["passed"])] += 1
                    groups[pid].append(grade if result["passed"] else "unconfirmed")
                    for q, detail in zip(qs, result["details"]):
                        # Corrected item-total: this item is excluded from the total.
                        other = sum(
                            d["correct"]
                            for d in result["details"]
                            if d["id"] != detail["id"]
                        )
                        items[q["family"]][competence].append(
                            (int(detail["correct"]), other)
                        )
                    writer.add(
                        "assessment/attempts.jsonl",
                        record(
                            "assessment_attempt",
                            aid,
                            "assessment",
                            {
                                "persona_id": pid,
                                "specialization": spec,
                                "chosen_grade": grade,
                                "competence": competence,
                                "variant": variant,
                                "bank_version": bank.VERSION,
                                "seed": actual_seed,
                                "questions": qs,
                                "answers": answers,
                                "expected_pass": expected,
                                "application_result": result,
                                "reference_answers": refs,
                            },
                            split="dev" if variant < 4 else "test",
                            origin="synthetic",
                            label_origin="simulation",
                            refs=[
                                source_ref("mvp", "snapshot/mvp/bank.py", bank.VERSION),
                                source_ref(
                                    "team_synthetic", "fsp_dataset/assessment.py", pid
                                ),
                            ],
                        ),
                    )
    retest = []
    for pid, predictions in sorted(groups.items()):
        counts = Counter(predictions)
        n = len(predictions)
        agreements = sum(v * (v - 1) // 2 for v in counts.values())
        retest.append(
            {
                "persona": pid,
                "attempts": n,
                "pairs": n * (n - 1) // 2,
                "agreeing_pairs": agreements,
                "grade_counts": dict(counts),
            }
        )
    discrimination = []
    for family, strata in sorted(items.items()):
        pairs = [p for group in strata.values() for p in group]
        x, y = zip(*pairs)
        corr = (
            statistics.correlation(x, y)
            if len(set(x)) > 1 and len(set(y)) > 1
            else None
        )
        high = statistics.mean(p[0] for p in strata["strong"])
        low = statistics.mean(p[0] for p in strata["weak"])
        discrimination.append(
            {
                "family": family,
                "observations": len(pairs),
                "strong_correct_fraction": high,
                "weak_correct_fraction": low,
                "strong_minus_weak": high - low,
                "corrected_item_total_correlation": corr,
            }
        )
    return {
        "status": "measured_simulation",
        "real_human_attempts": 0,
        "attempts": sum(len(x) for x in groups.values()),
        "oracle_checks": question_count,
        "oracle_errors": oracle_errors,
        "bank_version": bank.VERSION,
        "test_retest_pairwise_agreement": sum(x["agreeing_pairs"] for x in retest)
        / sum(x["pairs"] for x in retest),
        "test_retest": retest,
        "item_discrimination": discrimination,
        "expected_pass_confusion": [
            {"expected": e, "actual": a, "count": n}
            for (e, a), n in sorted(confusion.items())
        ],
        "limitations": [
            "Выбранный грейд фиксирован; не выбираем максимальный из трёх тестов.",
            "Один и тот же синтетический профиль повторяет тест; пары повторов зависимы.",
            "Компетентность симулятора задана через способность решать семейства. Высокое разделение ожидаемо по конструкции.",
            "dev/test здесь разделяют варианты, не испытуемых; это тест генератора, не независимая выборка людей.",
            "Трудность и профессиональная валидность на людях не установлены.",
        ],
    }

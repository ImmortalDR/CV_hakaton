from decimal import Decimal
from collections import Counter

import pytest

from fsp import bank
from evaluation.oracles import solve


@pytest.mark.parametrize("spec,grade", list(bank.BLUEPRINT))
def test_variants_reproducible_and_independent_oracle(spec, grade):
    fingerprints = set()
    for seed in range(100):
        qs = bank.generate(spec, grade, f"unit-{seed}")
        assert qs == bank.generate(spec, grade, f"unit-{seed}")
        assert Counter(q["family"] for q in qs) == Counter([
            f for f in bank.BLUEPRINT[spec, grade] for _ in range(2)
        ])
        for q in qs:
            assert abs(Decimal(q["answer"]) - Decimal(str(solve(q)))) <= Decimal(
                "0.005"
            )
        fingerprints.add(bank.fingerprint(qs))
    assert len(fingerprints) == 100


def test_boundary_family_has_meaningful_different_answers():
    qs = [
        q
        for seed in range(100)
        for q in bank.generate("python", "Junior", seed)
        if q["family"] == "py_boundary"
    ]
    assert len({q["answer"] for q in qs}) >= 4


@pytest.mark.parametrize(
    "answer", ["NaN", "Infinity", "-Infinity", "", "1e9999", "x", "None"]
)
def test_bad_numeric_inputs_fail_without_crashing(answer):
    qs = bank.generate("data", "Junior", 13)
    result = bank.grade_answers(qs, {q["id"]: answer for q in qs})
    assert result["score"] == 0


def test_rounding_comma_threshold_and_empty_answers():
    qs = bank.generate("data", "Middle", 43)
    answers = {q["id"]: str(solve(q)).replace(".", ",") for q in qs}
    assert bank.grade_answers(qs, answers)["score"] == 100
    optional = [q["id"] for q in qs if q["skill"] != "sql"]
    answers.pop(optional[0])
    assert bank.grade_answers(qs, answers)["passed"]
    answers.pop(optional[1])
    assert not bank.grade_answers(qs, answers)["passed"]
    assert bank.grade_answers(qs, {})["score"] == 0


@pytest.mark.parametrize("spec,grade", list(bank.BLUEPRINT))
def test_core_skill_required_but_historical_rubric_preserved(spec, grade):
    qs = bank.generate(spec, grade, "core-regression")
    core = "python" if spec == "python" else "sql"
    answers = {q["id"]: str(solve(q)) for q in qs}
    answers.pop(next(q["id"] for q in qs if q["skill"] == core))
    result = bank.grade_answers(qs, answers)
    assert result["score"] == 75 and not result["passed"]
    assert bank.grade_answers(qs, answers, version="1.1.0")["passed"]
    assert bank.grade_answers(qs, answers, version="1.0.0")["passed"]


def test_seed_changes_question_order_without_changing_blueprint():
    orders = {tuple(q["family"] for q in bank.generate("python", "Junior", n)) for n in range(20)}
    assert len(orders) > 1

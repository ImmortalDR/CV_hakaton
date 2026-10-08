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
    assert bank.grade_answers(qs, answers)["passed"]
    answers.pop(optional[2])
    assert not bank.grade_answers(qs, answers)["passed"]
    assert bank.grade_answers(qs, {})["score"] == 0


@pytest.mark.parametrize("spec,grade", list(bank.BLUEPRINT))
def test_core_skill_required_but_historical_rubric_preserved(spec, grade):
    qs = bank.generate(spec, grade, "core-regression", version="1.2.0")
    core = "python" if spec == "python" else "sql"
    answers = {q["id"]: str(solve(q)) for q in qs}
    answers.pop(next(q["id"] for q in qs if q["skill"] == core))
    result = bank.grade_answers(qs, answers, version="1.2.0")
    assert result["score"] == 75 and not result["passed"]
    assert bank.grade_answers(qs, answers, version="1.1.0")["passed"]
    assert bank.grade_answers(qs, answers, version="1.0.0")["passed"]


def test_seed_changes_question_order_without_changing_blueprint():
    orders = {tuple(q["family"] for q in bank.generate("python", "Junior", n)) for n in range(20)}
    assert len(orders) > 1


@pytest.mark.parametrize("spec,grade", list(bank.BLUEPRINT))
def test_v2_one_core_mistake_allowed_but_two_cannot_be_hidden_by_total(spec, grade):
    qs = bank.generate(spec, grade, "v2-core")
    core = "python" if spec == "python" else "sql"
    answers = {q["id"]: str(solve(q)) for q in qs}
    core_ids = [q["id"] for q in qs if q["skill"] == core]
    assert len(qs) == 8 and len(core_ids) == 4
    answers.pop(core_ids[0])
    r = bank.grade_answers(qs, answers)
    assert r["passed"] and r["score"] == 87.5
    assert next(s for s in r["skills"] if s["skill"] == core)["state"] == "met"
    answers.pop(core_ids[1])
    r = bank.grade_answers(qs, answers)
    assert not r["passed"] and r["score"] == 75


def test_unknown_versions_and_empty_assessments_fail_closed():
    with pytest.raises(ValueError):
        bank.generate("python", "Junior", 1, version="99.0.0")
    with pytest.raises(ValueError):
        bank.grade_answers([], {})


@pytest.mark.parametrize("version", ["1.1.0", "1.2.0"])
def test_legacy_generation_preserves_size_and_blueprint(version):
    qs = bank.generate("python", "Junior", "historical", version=version)
    assert len(qs) == 4
    assert Counter(q["family"] for q in qs) == Counter({"py_filter": 2, "py_boundary": 2})


def test_historical_question_texts_match_frozen_release_fingerprints():
    import json
    from pathlib import Path
    rows = json.loads(Path('tests/legacy_bank_fingerprints.json').read_text())
    for r in rows:
        qs = bank.generate(r['spec'], r['grade'], r['seed'], version=r['version'])
        assert bank.fingerprint(qs) == r['fingerprint']

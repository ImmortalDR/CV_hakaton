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


@pytest.mark.parametrize('num,den,expected', [(2900,32,'90.63'), (1005,1000,'1.01'), (625,1000,'0.63')])
def test_half_up_exact_boundaries(num, den, expected):
    assert bank.round_ratio(num, den) == expected


def test_conditional_rounding_new_and_historical_versions():
    for seed in range(10000):
        qs = bank.generate('data', 'Middle', seed)
        q = next((q for q in qs if q['family'] == 'stats_conditional'
                  and q['params']['returning'] == 32 and q['params']['bought'] == 29), None)
        if q:
            break
    assert q is not None
    assert q['answer'] == '90.63'
    assert '90,625 → 90,63' in q['text']
    for answer in ['90.63', '90,63']:
        assert bank.grade_answers([q], {q['id']: answer})['details'][0]['correct']
    assert not bank.grade_answers([q], {q['id']: '90.62'})['details'][0]['correct']
    old = bank.generate('data', 'Middle', seed, version='2.0.0')
    old_q = next(x for x in old if x['id'] == q['id'])
    assert old_q['answer'] == '90.62'
    assert len(old) == 8 and bank.rubric('2.0.0')['core_min_correct'] == 3


def test_2_1_history_keeps_text_answers_order_and_rounding():
    import json
    from pathlib import Path
    for row in json.loads(Path('tests/bank_2_1_fingerprints.json').read_text()):
        qs = bank.generate(row['spec'], row['grade'], row['seed'], version=row['version'])
        assert bank.fingerprint(qs) == row['fingerprint']
        assert [q['answer'] for q in qs] == row['answers']
        assert bank.grade_answers(qs, {q['id']: q['answer'] for q in qs}, row['version'])['score'] == 100


@pytest.mark.parametrize('n,word', [(0,'попыток'),(1,'попытка'),(2,'попытки'),(4,'попытки'),(5,'попыток'),(11,'попыток'),(14,'попыток'),(21,'попытка'),(22,'попытки'),(25,'попыток'),(101,'попытка')])
def test_russian_count_boundaries(n, word):
    from fsp.formatting import count_label
    assert count_label(n, 'попытка', 'попытки', 'попыток') == f'{n} {word}'


def test_backoff_new_text_and_legacy_five_attempts():
    import random
    for seed in range(100):
        new = bank.question('http_backoff', random.Random(seed))
        old = bank.question('http_backoff', random.Random(seed), version='2.1.0')
        if new['params']['n'] == 5:
            assert '5 попыток HTTP' in new['text']
            assert '5 попытки HTTP' in old['text']
            assert new['answer'] == old['answer']
            break
    else:
        pytest.fail('No five-attempt case exercised')

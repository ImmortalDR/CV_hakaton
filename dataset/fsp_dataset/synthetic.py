"""Controlled cases and an explicit rubric; never imports the product ranker."""

import hashlib
import random

from .common import record, source_ref

GRADES = ["Junior", "Middle", "Senior"]
PRIMARY = {"python": "python", "data": "sql"}


def oracle(candidate, criteria):
    """Team's full-recommendation criterion, not the application's score formula.

    It deliberately does not prescribe the total order of equally suitable people.
    Missing qualification is unknown, not evidence of professional inability.
    """
    facts = []

    def add(name, state, reason):
        facts.append({"requirement": name, "state": state, "reason": reason})

    add(
        "specialization",
        "met" if candidate["specialization"] == criteria["specialization"] else "unmet",
        "Сравнение явно заданной специализации сценария",
    )
    grade = candidate["verified_grade"]
    add(
        "grade",
        (
            "unknown"
            if grade is None
            else "met" if grade in criteria["grades"] else "unmet"
        ),
        "Подтверждение только внутри явно синтетического сценария",
    )
    evidence = {e["skill"]: e["state"] for e in candidate["evidence"]}
    for skill in criteria["required_skills"]:
        add(
            skill,
            evidence.get(skill, "unknown"),
            "Контрольное свидетельство либо его отсутствие",
        )
    if criteria["fsp_only"]:
        add(
            "fsp",
            "met" if candidate["achievements"] else "unknown",
            "История ФСП обязательна только в этом запросе",
        )
    states = {f["state"] for f in facts}
    decision = (
        "reject"
        if "unmet" in states
        else "insufficient_evidence" if "unknown" in states else "recommend"
    )
    return {
        "decision": decision,
        "relevance": {"reject": 0, "recommend": 1, "insufficient_evidence": None}[
            decision
        ],
        "requirements": facts,
        "rubric_version": "full-recommendation-1.0",
        "label_semantics": "synthetic_evidence_match",
        "annotator_ids": [],
        "review_status": "programmatic_not_human",
    }


def generate(writer, seed=20261008):
    for split in ["dev", "test"]:
        for spec in PRIMARY:
            for grade in GRADES:
                for scenario in ["mixed", "none", "unknown", "fsp"]:
                    qid = f"syn:{split}:{spec}:{grade}:{scenario}"
                    required = "docker" if scenario == "unknown" else PRIMARY[spec]
                    criteria = {
                        "specialization": spec,
                        "grades": [grade],
                        "required_skills": [required],
                        "desired_skills": [],
                        "fsp_only": scenario == "fsp",
                    }
                    refs = [
                        source_ref("team_synthetic", "fsp_dataset/synthetic.py", qid)
                    ]
                    need = {
                        "criteria": criteria,
                        "title": f"Контрольная потребность {qid}",
                        "description": "Вымышленная потребность для проверки формальных требований",
                        "salary_min": 100000,
                        "salary_max": 150000,
                        "salary_currency": "RUB",
                        "leakage_group_id": qid,
                        "original_id": qid,
                        "mapping_status": "controlled",
                    }
                    writer.add(
                        "data/synthetic/needs.jsonl",
                        record(
                            "need",
                            qid,
                            "matching",
                            need,
                            split=split,
                            origin="synthetic",
                            refs=refs,
                        ),
                    )
                    ids = []
                    # IDs hide the archetype: tie-breaking must not use the gold label.
                    rng = random.Random(f"{seed}:{qid}")
                    for index in range(10):
                        cid = (
                            "syn:c:"
                            + hashlib.sha256(
                                f"{seed}:{qid}:{index}".encode()
                            ).hexdigest()[:20]
                        )
                        ids.append(cid)
                        state = (
                            "met" if index < 6 else "unmet" if index == 6 else "unknown"
                        )
                        if scenario == "none":
                            state = "unmet"
                        if scenario == "unknown":
                            state = "unknown"
                        confirmed = grade if index != 9 else None
                        cspec = (
                            spec
                            if index != 8
                            else "data" if spec == "python" else "python"
                        )
                        simulation_id = f"sim:{cid}" if confirmed else None
                        payload = {
                            "specialization": cspec,
                            "claimed_grade": grade,
                            "verified_grade": confirmed,
                            "grade_status": (
                                "simulated_confirmed" if confirmed else "not_assessed"
                            ),
                            "skills": [PRIMARY[spec], "docker"],
                            "evidence": (
                                []
                                if state == "unknown"
                                else [
                                    {
                                        "skill": required,
                                        "state": state,
                                        "evidence_type": "simulated_assessment",
                                    }
                                ]
                            ),
                            "test_score": rng.choice([75, 100]),
                            "achievements": (
                                [{"provider": "demo_fsp", "points": 3}]
                                if index in [1, 3, 6, 7]
                                else []
                            ),
                            "leakage_group_id": cid,
                            "profile_text": f"Вымышленный профиль {cid}",
                            "original_id": cid,
                            "simulation_ref": simulation_id,
                            "mapping_status": "controlled",
                        }
                        cref = [
                            source_ref(
                                "team_synthetic",
                                "fsp_dataset/synthetic.py",
                                f"{qid}/case/{index}",
                            )
                        ]
                        writer.add(
                            "data/synthetic/candidates.jsonl",
                            record(
                                "candidate",
                                cid,
                                "matching",
                                payload,
                                split=split,
                                origin="synthetic",
                                refs=cref,
                            ),
                        )
                        if simulation_id:
                            writer.add(
                                "data/synthetic/simulations.jsonl",
                                record(
                                    "simulation",
                                    simulation_id,
                                    "matching",
                                    {
                                        "candidate_id": cid,
                                        "declared_outcome": grade,
                                        "provenance": "controlled_fixture_not_real_test",
                                    },
                                    split=split,
                                    origin="synthetic",
                                    label_origin="simulation",
                                    refs=cref,
                                ),
                            )
                        label = oracle(payload, criteria) | {
                            "candidate_id": cid,
                            "need_id": qid,
                        }
                        writer.add(
                            "labels/matching.jsonl",
                            record(
                                "judgment",
                                "j:" + cid,
                                "matching",
                                label,
                                split=split,
                                origin="synthetic",
                                label_origin="team_rule_oracle",
                                refs=cref,
                            ),
                        )
                    rng.shuffle(ids)
                    writer.add(
                        "data/synthetic/pools.jsonl",
                        record(
                            "pool",
                            "pool:" + qid,
                            "matching",
                            {
                                "need_id": qid,
                                "candidate_ids": ids,
                                "selection_method": "fixed_archetypes_seeded_order",
                                "scenario": scenario,
                            },
                            split=split,
                            origin="synthetic",
                            refs=refs,
                        ),
                    )


WORKFLOWS = [
    (
        "R11",
        "Приглашение без корректной RUB-вилки отклоняется",
        "tests/test_api.py::test_invitation_salary_contract",
    ),
    (
        "R12",
        "Принятие раскрывает контакты только пригласившему работодателю",
        "tests/test_api.py::test_contacts_full_lifecycle_pdf_search_history_and_chat",
    ),
    (
        "R13",
        "Кандидат не видит чужие приглашения",
        "tests/test_api.py::test_rejection_never_grants_and_invitation_owner_lists",
    ),
    (
        "R06",
        "Неуспешная попытка не понижает ранее подтверждённый грейд",
        "tests/test_api.py::test_failed_first_attempt_lower_choice_and_failed_retake_keeps_grade",
    ),
    (
        "R08",
        "Без ФСП можно зарегистрироваться и пройти тест",
        "tests/test_api.py::test_server_grading_no_leaks_no_injection_and_idempotence",
    ),
]


def workflow(writer):
    for requirement, behavior, node in WORKFLOWS:
        writer.add(
            "scenarios/workflow.jsonl",
            record(
                "workflow",
                "workflow:" + requirement,
                "workflow",
                {
                    "requirement": requirement,
                    "expected_behavior": behavior,
                    "test_node": node,
                    "execution_status": "not_run",
                },
                origin="synthetic",
                label_origin="team_rule_oracle",
                refs=[
                    source_ref(
                        "team_synthetic", "REQUIREMENTS_TRACEABILITY.md", requirement
                    )
                ],
            ),
        )

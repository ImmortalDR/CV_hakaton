"""Author-defined synthetic scenarios; no production scorer is imported.

This creates an inspectable JSON fixture, including explicit relevance labels.
All IDs, skill claims and evidence belong to invented people.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent
CATEGORIES = [
    ("python", "Junior", "python", "testing"),
    ("python", "Middle", "python", "http"),
    ("python", "Senior", "python", "http"),
    ("data", "Junior", "sql", "statistics"),
    ("data", "Middle", "sql", "statistics"),
    ("data", "Senior", "sql", "transactions"),
]


def split(name, categories):
    candidates, queries = [], []
    for group, (spec, grade, primary, secondary) in enumerate(categories):
        prefix = f"{name}-{group}"
        # ID, evidence on primary/secondary, claims, years, test, sport.
        # Evidence is assigned by the scenario author, never inferred from prose.
        cases = [
            ("a", "met", "met", [primary, secondary], 3, 100, 0),
            ("b", "met", "unmet", [primary], 2, 75, 0),
            ("c", "met", None, [], 1, 75, 0),
            ("d", None, "met", [primary, secondary], 12, 75, 3),
            ("e", "unmet", "met", [primary, secondary], 15, 75, 0),
            ("f", None, None, [primary, secondary], 20, 0, 0),
            ("g", "met", "met", [], 0, 100, 1),
            ("h", "met", "unmet", [primary], None, 75, 3),
        ]
        for key, one, two, claims, years, score, sport in cases:
            evidence = [
                {
                    "skill": skill,
                    "state": state,
                    "source": "assessment",
                    "id": f"{prefix}-{key}-{skill}",
                    "correct": 2 if state == "met" else 1,
                    "total": 2,
                    "version": "fixture-1",
                    "date": "2026-10-01",
                }
                for skill, state in [(primary, one), (secondary, two)]
                if state
            ]
            candidates.append(
                {
                    "id": f"{prefix}-{key}",
                    "specialization": spec,
                    "verified_grade": grade if key != "f" else None,
                    "skills": claims,
                    "experience_years": years,
                    "evidence": evidence,
                    "test_score": score,
                    "achievements": (
                        [
                            {
                                "provider": "demo_fsp",
                                "points": sport,
                                "verification": "simulated",
                            }
                        ]
                        if sport
                        else []
                    ),
                }
            )
        queries.append(
            {
                "id": f"{prefix}-query",
                "text": f"Нужен {grade} {spec}: {primary}, желательно {secondary}.",
                "criteria": {
                    "specialization": spec,
                    "grades": [grade],
                    "required_skills": [primary],
                    "desired_skills": [secondary],
                    "min_years": None,
                    "fsp_only": False,
                },
                "relevant_ids": [
                    f"{prefix}-{key}" for key in ["a", "b", "c", "g", "h"]
                ],
                "reason": "Категория подтверждена; основной навык доказан. Неподтверждённый стаж и спортивный опыт не заменяют навык.",
            }
        )
    if name == "test":
        queries.append(
            {
                "id": "test-uncovered-react",
                "text": "Python Junior с обязательным React",
                "criteria": {
                    "specialization": "python",
                    "grades": ["Junior"],
                    "required_skills": ["react"],
                    "desired_skills": [],
                    "min_years": None,
                    "fsp_only": False,
                },
                "relevant_ids": [],
                "reason": "В fixture нет проверки React. Выдавать слабое соответствие допустимо, считать кандидатов релевантными — нет.",
            }
        )
        queries.append(
            {
                "id": "test-both-required",
                "text": "Python Junior: обязательны Python и тестирование",
                "criteria": {
                    "specialization": "python",
                    "grades": ["Junior"],
                    "required_skills": ["python", "testing"],
                    "desired_skills": [],
                    "min_years": None,
                    "fsp_only": False,
                },
                "relevant_ids": ["test-0-a", "test-0-g"],
                "reason": "Два обязательных навыка: релевантны только оба подтверждённых. Это более строгая контрольная разметка.",
            }
        )
    return {"candidates": candidates, "queries": queries}


def main():
    data = {
        "schema_version": 1,
        "source": "synthetic_author_labels",
        "human_experts": 0,
        "train": None,
        "dev": split("dev", [CATEGORIES[0], CATEGORIES[3]]),
        "test": split("test", CATEGORIES),
    }
    (ROOT / "matching_fixtures.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )
    people = []
    for spec, families in [
        (
            "python",
            [
                "py_filter",
                "py_boundary",
                "py_alias",
                "http_keys",
                "py_dag",
                "http_backoff",
            ],
        ),
        (
            "data",
            [
                "sql_where",
                "stats_median",
                "sql_join",
                "stats_weighted",
                "sql_rank",
                "tx_snapshot",
            ],
        ),
    ]:
        # Expected levels are explicit labels for a simulation, not observations of people.
        for label, known, expected, error in [
            ("novice", [], "unconfirmed", 0),
            ("junior", families[:2], "Junior", 0),
            ("middle", families[:4], "Middle", 0),
            ("senior", families, "Senior", 0),
            ("narrow", [families[0], families[2], families[4]], "unconfirmed", 0),
            ("noisy-middle", families[:4], "Middle", 0.2),
        ]:
            people.append(
                {
                    "id": spec + "-" + label,
                    "specialization": spec,
                    "known_families": known,
                    "expected_grade": expected,
                    "slip_probability": error,
                }
            )
    (ROOT / "grade_personas.json").write_text(
        json.dumps(people, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()

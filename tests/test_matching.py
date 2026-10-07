from fsp.matching import eligible, group_sort, rank_candidate


def test_unknown_never_becomes_proof_and_sport_does_not_change_category():
    candidate = {
        "id": "x",
        "specialization": "python",
        "verified_grade": "Junior",
        "skills": ["python"],
        "experience_years": 20,
        "evidence": [],
        "test_score": 0,
        "achievements": [
            {"provider": "untrusted", "points": 999},
            {"provider": "demo_fsp", "points": 3},
        ],
    }
    criteria = {
        "specialization": "python",
        "grades": ["Junior"],
        "required_skills": ["python"],
        "min_years": 5,
    }
    result = rank_candidate(candidate, criteria)
    assert result["score"] == 3
    assert all(f["state"] == "unknown" for f in result["facts"])
    assert not eligible(candidate, criteria | {"grades": ["Senior"]})
    junior = candidate | {"match": {"score": 100}}
    senior = candidate | {"id": "s", "verified_grade": "Senior", "match": {"score": 1}}
    assert [p["id"] for p in group_sort([junior, senior])] == ["s", "x"]


def test_explicit_evidence_and_zero_experience_remain_distinct():
    p = {
        "skills": [],
        "experience_years": 0,
        "test_score": 75,
        "evidence": [{"skill": "python", "state": "met"}],
    }
    result = rank_candidate(
        p,
        {
            "required_skills": ["python", "docker"],
            "desired_skills": ["react"],
            "min_years": 0,
        },
    )
    assert result["score"] == 45
    assert [f["state"] for f in result["facts"]] == [
        "met",
        "unknown",
        "unknown",
        "unknown",
    ]
    assert result["facts"][-1]["source"] == "self_report"
    assert result["facts"][-1]["claimed_years"] == 0

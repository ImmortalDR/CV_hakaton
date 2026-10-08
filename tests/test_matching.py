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


def test_required_skill_coverage_is_not_a_score_threshold():
    criteria = {"required_skills": ["python", "testing"], "desired_skills": ["react"]}
    p = {"test_score": 100, "skills": ["testing"], "evidence": [{"skill": "python", "state": "met"}]}
    r = rank_candidate(p, criteria)
    assert not r["required_skills_met"]
    assert r["missing_skills"] == ["testing"] and r["unmet_skills"] == []
    p["evidence"].append({"skill": "testing", "state": "unmet"})
    r = rank_candidate(p, criteria)
    assert not r["required_skills_met"]
    assert r["missing_skills"] == [] and r["unmet_skills"] == ["testing"]
    p["evidence"][-1]["state"] = "met"
    r = rank_candidate(p, criteria)
    assert r["required_skills_met"]  # unknown desired React does not block
    assert rank_candidate(p, {"required_skills": []})["required_skills_met"]


def test_untrusted_achievement_does_not_satisfy_fsp_filter():
    p = {"specialization": "python", "verified_grade": "Junior", "achievements": [{"provider": "untrusted", "points": 999}]}
    criteria = {"specialization": "python", "grades": ["Junior"], "fsp_only": True}
    assert not eligible(p, criteria)
    p["achievements"].append({"provider": "demo_fsp", "points": 2})
    assert eligible(p, criteria)

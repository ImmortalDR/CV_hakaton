"""Evidence-based scoring v1. No name, contact, age or sex features."""

from .bank import GRADES

VERSION = "matching-1.1.0"


def skill_coverage(facts):
    """Only required skill evidence defines coverage; never infer it from score.

    Experience stays a separately labelled self-report. Missing evidence and a
    failed assessment remain distinguishable, including mixed partial matches.
    """
    required = [f for f in facts if f["kind"] == "required_skills"]
    missing = [f["skill"] for f in required if f["state"] == "unknown"]
    failed = [f["skill"] for f in required if f["state"] == "unmet"]
    return {
        "required_skills_met": not missing and not failed,
        "missing_skills": missing,
        "unmet_skills": failed,
    }


def verified_achievements(candidate):
    # Only our explicit demo provider is currently supported; arbitrary imported
    # achievements must not satisfy the FSP filter or award ranking points.
    return [a for a in candidate.get("achievements", []) if a.get("provider") == "demo_fsp"]


def rank_candidate(candidate, criteria):
    facts = []
    evidence = {e["skill"]: e for e in candidate.get("evidence", [])}
    points = {}
    for kind, weight in [("required_skills", 60), ("desired_skills", 15)]:
        skills = criteria.get(kind, [])
        met = 0
        for s in skills:
            e = evidence.get(s)
            state = e["state"] if e else "unknown"
            met += state == "met"
            facts.append(
                {
                    "skill": s,
                    "kind": kind,
                    "state": state,
                    "source": (
                        "assessment"
                        if e
                        else (
                            "self_report"
                            if s in candidate.get("skills", [])
                            else "none"
                        )
                    ),
                    "evidence": e,
                }
            )
        points[kind] = weight * met / len(skills) if skills else 0
    if criteria.get("min_years") is not None:
        # A resume claim is never objective verification of professional tenure.
        facts.append(
            {
                "skill": "experience",
                "kind": "required",
                "state": "unknown",
                "source": (
                    "self_report"
                    if candidate.get("experience_years") is not None
                    else "none"
                ),
                "claimed_years": candidate.get("experience_years"),
                "evidence": None,
            }
        )
    test = 0.2 * candidate.get("test_score", 0)
    fsp = min(
        5,
        sum(
            a.get("points", 0)
            for a in verified_achievements(candidate)
        ),
    )
    return {
        "score": round(sum(points.values()) + test + fsp, 2),
        "facts": facts,
        "breakdown": {**points, "test": test, "fsp": fsp},
        "methodology": VERSION,
        **skill_coverage(facts),
    }


def eligible(candidate, criteria):
    return (
        candidate.get("specialization") == criteria["specialization"]
        and candidate.get("verified_grade") in criteria["grades"]
        and (not criteria.get("fsp_only") or bool(verified_achievements(candidate)))
    )


def group_sort(items):
    # Grade order only groups the display; the numeric score never crosses categories.
    return sorted(
        items,
        key=lambda c: (
            c["specialization"],
            -(
                GRADES.index(c["verified_grade"])
                if c.get("verified_grade") in GRADES
                else -1
            ),
            -c["match"]["score"],
            c["id"],
        ),
    )

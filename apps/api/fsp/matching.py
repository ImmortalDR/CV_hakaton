"""Evidence-based scoring v1. No name, contact, age or sex features."""

from .bank import GRADES


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
            for a in candidate.get("achievements", [])
            if a.get("provider") == "demo_fsp"
        ),
    )
    return {
        "score": round(sum(points.values()) + test + fsp, 2),
        "facts": facts,
        "breakdown": {**points, "test": test, "fsp": fsp},
        "methodology": "matching-1.0.0",
    }


def eligible(candidate, criteria):
    return (
        candidate.get("specialization") == criteria["specialization"]
        and candidate.get("verified_grade") in criteria["grades"]
        and (not criteria.get("fsp_only") or bool(candidate.get("achievements")))
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

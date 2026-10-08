"""Versioned, closed JSON schemas for envelopes and typed payloads."""

STR = {"type": "string"}
ID = {"type": "string", "minLength": 1}
NULLSTR = {"type": ["string", "null"]}
NUM = {"type": "number"}
BOOL = {"type": "boolean"}


def obj(properties, required=None):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }


def arr(items):
    return {"type": "array", "items": items}


STATE = {"enum": ["met", "unmet", "unknown"]}
REF = obj({"source_id": ID, "file": ID, "locator": ID})
FACT = obj(
    {"skill": ID, "state": STATE, "evidence_type": {"enum": ["simulated_assessment"]}}
)
CRITERIA = obj(
    {
        "specialization": ID,
        "grades": arr(ID),
        "required_skills": arr(ID),
        "desired_skills": arr(ID),
        "fsp_only": BOOL,
    }
)
QUESTION = obj(
    {
        "id": ID,
        "family": ID,
        "skill": ID,
        "text": ID,
        "answer": STR,
        "explanation": ID,
        "params": {"type": "object"},
    }
)
GRADE_RESULT = obj(
    {
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "passed": BOOL,
        "threshold": {"type": "integer"},
        "details": arr(
            obj({"id": ID, "correct": BOOL, "expected": STR, "explanation": ID})
        ),
        "skills": arr(
            obj(
                {
                    "skill": ID,
                    "correct": {"type": "integer", "minimum": 0},
                    "total": {"type": "integer", "minimum": 1},
                    "state": STATE,
                }
            )
        ),
    }
)
PAYLOADS = {
    "candidate": obj(
        {
            "specialization": NULLSTR,
            "claimed_grade": NULLSTR,
            "verified_grade": NULLSTR,
            "grade_status": {"enum": ["not_assessed", "simulated_confirmed"]},
            "skills": arr(ID),
            "evidence": arr(FACT),
            "test_score": NUM,
            "achievements": arr(obj({"provider": ID, "points": NUM})),
            "leakage_group_id": ID,
            "profile_text": STR,
            "original_id": ID,
            "simulation_ref": NULLSTR,
            "mapping_status": ID,
        }
    ),
    "need": obj(
        {
            "criteria": {"anyOf": [CRITERIA, {"type": "null"}]},
            "title": STR,
            "description": STR,
            "salary_min": {"type": ["number", "null"]},
            "salary_max": {"type": ["number", "null"]},
            "salary_currency": NULLSTR,
            "leakage_group_id": ID,
            "original_id": ID,
            "mapping_status": ID,
        }
    ),
    "judgment": obj(
        {
            "candidate_id": ID,
            "need_id": ID,
            "decision": {"enum": ["recommend", "reject", "insufficient_evidence"]},
            "relevance": {"enum": [0, 1, None]},
            "requirements": arr(obj({"requirement": ID, "state": STATE, "reason": ID})),
            "rubric_version": ID,
            "label_semantics": {"const": "synthetic_evidence_match"},
            "annotator_ids": arr(ID),
            "review_status": {"const": "programmatic_not_human"},
        }
    ),
    "pool": obj(
        {
            "need_id": ID,
            "candidate_ids": arr(ID),
            "selection_method": ID,
            "scenario": ID,
        }
    ),
    "simulation": obj(
        {
            "candidate_id": ID,
            "declared_outcome": ID,
            "provenance": {"const": "controlled_fixture_not_real_test"},
        }
    ),
    "outcome": obj(
        {
            "candidate_id": ID,
            "need_id": ID,
            "flags": obj(
                {
                    "browsed": {"enum": [0, 1]},
                    "delivered": {"enum": [0, 1]},
                    "satisfied": {"enum": [0, 1]},
                }
            ),
            "label_semantics": {"const": "historical_outcome"},
            "original_record": ID,
        }
    ),
    "legacy_pair": obj(
        {
            "candidate_id": ID,
            "need_id": ID,
            "satisfied": {"enum": [0, 1]},
            "original_split": ID,
            "label_semantics": {"const": "legacy_source_classification"},
        }
    ),
    "legacy_pool": obj(
        {
            "need_id": ID,
            "candidate_ids": arr(ID),
            "labels": arr({"enum": [-1, 0, 1]}),
            "label_semantics": {"const": "legacy_source_ranking_not_semantic_gold"},
        }
    ),
    "auxiliary": obj(
        {
            "source_task": ID,
            "original_values": {"type": "object"},
            "label_semantics": ID,
            "original_locator": ID,
        }
    ),
    "historical_event": obj(
        {
            "original_values": {"type": "object"},
            "label_semantics": {"const": "unresolved_source_event_direction"},
            "usable_for_semantic_scoring": {"const": False},
        }
    ),
    "assessment_attempt": obj(
        {
            "persona_id": ID,
            "specialization": ID,
            "chosen_grade": ID,
            "competence": {"enum": ["weak", "partial", "strong", "noisy"]},
            "variant": {"type": "integer"},
            "bank_version": ID,
            "seed": ID,
            "questions": {**arr(QUESTION), "minItems": 1},
            "answers": {"type": "object", "additionalProperties": STR},
            "expected_pass": {"type": ["boolean", "null"]},
            "application_result": GRADE_RESULT,
            "reference_answers": {"type": "object", "additionalProperties": STR},
        }
    ),
    "workflow": obj(
        {
            "requirement": ID,
            "expected_behavior": ID,
            "test_node": ID,
            "execution_status": {"enum": ["not_run", "passed", "failed"]},
        }
    ),
}


def schema_for(kind):
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:fsp:dataset:1.0:{kind}",
        **obj(
            {
                "schema_version": {"const": "1.0"},
                "kind": {"const": kind},
                "record_id": ID,
                "track": ID,
                "split": {"enum": ["dev", "test", "external"]},
                "data_origin": {"enum": ["synthetic", "source", "adapted"]},
                "label_origin": {
                    "enum": [
                        "none",
                        "team_rule_oracle",
                        "source_annotation",
                        "simulation",
                    ]
                },
                "source_refs": {**arr(REF), "minItems": 1},
                "payload": PAYLOADS[kind],
            }
        ),
    }

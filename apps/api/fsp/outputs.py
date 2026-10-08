"""Public response contracts. Private database objects are never serialized."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .schemas import Grade, NeedInput, Spec


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Notice(Output):
    message: str


class Registration(Notice):
    demo_verification_url: str | None
    delivery: Literal["simulated", "smtp"]


class User(Output):
    id: str
    email: str
    role: Literal["candidate", "employer"]
    demo: bool


class Health(Output):
    status: Literal["ok"]
    demo: bool
    version: str


class AssessmentRubric(Output):
    question_count: int
    minutes: int
    threshold: int
    core_min_correct: int
    core_total: int


class Catalog(Output):
    specializations: dict[str, str]
    grades: list[Grade]
    skills: dict[str, str]
    bank_version: str
    grade_cooldown_days: int
    retake_hours: int
    demo: bool
    rubric: AssessmentRubric


class Evidence(Output):
    id: str
    skill: str
    state: Literal["met", "unmet"]
    correct: int
    total: int
    attempt_id: str
    version: str
    date: datetime
    source: Literal["assessment"]


class Achievement(Output):
    provider: Literal["demo_fsp"]
    title: str
    result: str
    points: int
    date: str
    verification: Literal["simulated"]


class Fact(Output):
    skill: str
    kind: str
    state: Literal["met", "unmet", "unknown"]
    source: Literal["assessment", "self_report", "none"]
    evidence: Evidence | None
    claimed_years: int | None = None


class Match(Output):
    score: float
    facts: list[Fact]
    breakdown: dict[str, float]
    methodology: str
    required_skills_met: bool | None = None
    missing_skills: list[str] = []
    unmet_skills: list[str] = []


class Contacts(Output):
    email: str
    phone: str


class Profile(Output):
    id: str
    display_name: str
    specialization: Spec
    verified_grade: Grade | None
    skills: list[str]
    experience_years: int | None
    experience_source: Literal["self_report"]
    evidence: list[Evidence]
    test_score: float
    achievements: list[Achievement]
    demo: bool
    contacts: Contacts | None
    # These fields are only populated for the owner or an authorized company.
    about: str | None = None
    roles: str | None = None
    soft_skills: str | None = None
    name: str | None = None
    phone: str | None = None
    industry: str | None = None
    claimed_grade: Grade | None = None
    processing: bool | None = None
    published: bool | None = None
    show_experience: bool | None = None
    fsp_identity: str | None = None
    grade_changed_at: datetime | None = None
    next_grade_change: datetime | None = None
    match: Match | None = None


class Question(Output):
    id: str
    text: str
    skill: str


class AnswerDetail(Output):
    id: str
    correct: bool
    expected: str
    explanation: str


class SkillResult(Output):
    skill: str
    correct: int
    total: int
    state: Literal["met", "unmet"]


class Result(Output):
    score: float
    passed: bool
    threshold: int
    details: list[AnswerDetail]
    skills: list[SkillResult]


class Attempt(Output):
    id: str
    specialization: Spec
    grade: Grade
    status: Literal["active", "completed", "expired"]
    version: str
    created_at: datetime
    expires_at: datetime
    result: Result | None
    questions: list[Question]
    rubric: AssessmentRubric


class Company(Output):
    id: str
    name: str
    description: str
    sector: str
    contact: str


class Snapshot(Output):
    id: str
    created_at: datetime
    criteria: NeedInput
    items: list[Profile]
    hidden_count: int


class SearchHistory(Output):
    id: str
    created_at: datetime
    title: str


class Invitation(Output):
    id: str
    candidate_id: str
    company_name: str
    description: str
    salary_min: int
    salary_max: int
    currency: Literal["RUB"]
    employer_contact: str
    status: Literal["sent", "viewed", "accepted", "rejected"]
    created_at: datetime
    updated_at: datetime
    candidate_name: str
    contacts: Contacts | None


class Message(Output):
    id: str
    text: str
    mine: bool
    created_at: datetime


class Error(Output):
    detail: str
    fields: list[dict[str, str]] | None = None

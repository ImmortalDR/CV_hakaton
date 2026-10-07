from typing import Literal
from uuid import UUID
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
from .bank import SKILLS

Spec = Literal["python", "data"]
Grade = Literal["Junior", "Middle", "Senior"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Registration(Input):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    role: Literal["candidate", "employer"]
    processing: Literal[True]


class Login(Input):
    email: EmailStr
    password: str = Field(max_length=128)


class Verify(Input):
    token: str = Field(min_length=20, max_length=100)


class ProfileInput(Input):
    name: str = Field(min_length=2, max_length=160)
    phone: str = Field(default="", max_length=80)
    about: str = Field(default="", max_length=3000)
    industry: Literal["ИТ"] = "ИТ"
    specialization: Spec
    claimed_grade: Grade
    skills: list[str] = Field(default_factory=list, max_length=20)
    roles: str = Field(default="", max_length=500)
    soft_skills: str = Field(default="", max_length=1000)
    experience_years: int | None = Field(default=None, ge=0, le=60, strict=True)
    processing: bool
    published: bool
    show_experience: bool = True

    @field_validator("skills")
    @classmethod
    def skills_known(cls, v):
        if any(s not in SKILLS for s in v):
            raise ValueError("Выберите навыки из справочника")
        return list(dict.fromkeys(v))

    @model_validator(mode="after")
    def consent(self):
        if self.published and not self.processing:
            raise ValueError("Для публикации необходимо согласие на обработку")
        return self


class CompanyInput(Input):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=3000)
    sector: str = Field(min_length=2, max_length=160)
    contact: str = Field(min_length=5, max_length=300)


class StartAttempt(Input):
    grade: Grade


class Answers(Input):
    answers: dict[str, str] = Field(max_length=4)

    @field_validator("answers")
    @classmethod
    def bounded(cls, v):
        if any(k not in ["1", "2", "3", "4"] or len(x) > 100 for k, x in v.items()):
            raise ValueError("Недопустимый ответ")
        return v


class NeedInput(Input):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=3000)
    specialization: Spec
    grades: list[Grade] = Field(min_length=1, max_length=3)
    required_skills: list[str] = Field(default_factory=list, max_length=8)
    desired_skills: list[str] = Field(default_factory=list, max_length=8)
    min_years: int | None = Field(default=None, ge=0, le=60, strict=True)
    fsp_only: bool = False
    confirmed: Literal[True]

    @field_validator("required_skills", "desired_skills")
    @classmethod
    def known(cls, v):
        return ProfileInput.skills_known(v)


class InviteInput(Input):
    candidate_id: UUID
    request_id: UUID
    description: str = Field(min_length=10, max_length=3000)
    salary_min: int = Field(gt=0, le=10000000, strict=True)
    salary_max: int = Field(gt=0, le=10000000, strict=True)
    currency: Literal["RUB"]

    @model_validator(mode="after")
    def salary(self):
        if self.salary_min > self.salary_max:
            raise ValueError("Нижняя граница зарплаты больше верхней")
        return self


class Decision(Input):
    status: Literal["viewed", "accepted", "rejected"]


class ChatInput(Input):
    text: str = Field(min_length=1, max_length=2000)


class FspLink(Input):
    identity: Literal["demo-winner", "demo-participant", "unlink"]


class DemoLogin(Input):
    account: Literal["candidate", "employer", "other_employer"]

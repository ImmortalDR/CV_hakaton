"""Persistent entities. Public projections live in services, never ORM serialization."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("role IN ('candidate','employer')"),)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Verification(Base):
    __tablename__ = "email_verifications"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(160), default="Новая компания")
    description: Mapped[str] = mapped_column(Text, default="")
    sector: Mapped[str] = mapped_column(String(160), default="")
    contact: Mapped[str] = mapped_column(String(300), default="")


class CompanyMember(Base):
    __tablename__ = "company_members"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)


class Profile(Base):
    __tablename__ = "profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), default="")
    phone: Mapped[str] = mapped_column(String(80), default="")
    about: Mapped[str] = mapped_column(Text, default="")
    industry: Mapped[str] = mapped_column(String(60), default="ИТ")
    specialization: Mapped[str] = mapped_column(String(20), default="python")
    claimed_grade: Mapped[str] = mapped_column(String(20), default="Junior")
    verified_grade: Mapped[str | None] = mapped_column(String(20))
    verified_attempt_id: Mapped[str | None] = mapped_column(String(36))
    grade_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    skills: Mapped[list] = mapped_column(JSON, default=list)
    roles: Mapped[str] = mapped_column(String(500), default="")
    soft_skills: Mapped[str] = mapped_column(String(1000), default="")
    experience_years: Mapped[int | None] = mapped_column(Integer)
    processing: Mapped[bool] = mapped_column(Boolean, default=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    show_experience: Mapped[bool] = mapped_column(Boolean, default=True)
    fsp_identity: Mapped[str | None] = mapped_column(String(80), unique=True)
    achievements: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (
        CheckConstraint(
            "experience_years IS NULL OR experience_years BETWEEN 0 AND 60"
        ),
    )


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    processing: Mapped[bool] = mapped_column(Boolean)
    publication: Mapped[bool] = mapped_column(Boolean)
    version: Mapped[str] = mapped_column(String(20), default="2026-10-07")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    specialization: Mapped[str] = mapped_column(String(20))
    grade: Mapped[str] = mapped_column(String(20))
    seed: Mapped[str] = mapped_column(String(40))
    version: Mapped[str] = mapped_column(String(20))
    variant_hash: Mapped[str] = mapped_column(String(64), unique=True)
    questions: Mapped[list] = mapped_column(JSON)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("status IN ('active','completed','expired')"),)


class Evidence(Base):
    __tablename__ = "skill_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), index=True)
    skill: Mapped[str] = mapped_column(String(60))
    state: Mapped[str] = mapped_column(String(20))
    correct: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    version: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("attempt_id", "skill"),)


class Need(Base):
    __tablename__ = "employer_needs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    criteria: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Snapshot(Base):
    __tablename__ = "search_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    need_id: Mapped[str] = mapped_column(ForeignKey("employer_needs.id"))
    items: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Invitation(Base):
    __tablename__ = "invitations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    candidate_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(36))
    description: Mapped[str] = mapped_column(Text)
    salary_min: Mapped[int] = mapped_column(Integer)
    salary_max: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    company_name: Mapped[str] = mapped_column(String(160))
    employer_contact: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="sent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        UniqueConstraint("company_id", "request_id"),
        CheckConstraint("salary_min > 0 AND salary_max >= salary_min"),
        CheckConstraint("currency = 'RUB'"),
        CheckConstraint("status IN ('sent','viewed','accepted','rejected')"),
    )


class ContactGrant(Base):
    __tablename__ = "contact_grants"
    candidate_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id"), primary_key=True
    )
    invitation_id: Mapped[str] = mapped_column(ForeignKey("invitations.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    invitation_id: Mapped[str] = mapped_column(ForeignKey("invitations.id"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

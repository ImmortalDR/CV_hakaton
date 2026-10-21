"""Explicit, additive synthetic demo seed. Never resets or edits existing users."""

import os
import secrets
from datetime import timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from . import bank
from .main import PASSWORDS
from .models import (
    User,
    Profile,
    Company,
    CompanyMember,
    Consent,
    Attempt,
    Evidence,
    now,
)


def ready_candidate(db, user):
    """Create visible, graded examples only for a newly created synthetic user."""
    passed = None
    for offset, success in [(10, True), (9, False)]:
        value = secrets.token_hex(16)
        qs = bank.generate("python", "Junior", value)
        answers = {q["id"]: q["answer"] for q in qs}
        if not success:
            answers = {q["id"]: q["answer"] if i < 4 else "-9999" for i, q in enumerate(qs)}
        result = bank.grade_answers(qs, answers)
        at = now() - timedelta(days=offset)
        attempt = Attempt(user_id=user.id, specialization="python", grade="Junior",
            seed=value, version=bank.VERSION, variant_hash=bank.fingerprint(qs),
            questions=qs, answers=answers, result=result, status="completed",
            created_at=at, finished_at=at + timedelta(minutes=12), expires_at=at + timedelta(minutes=30))
        db.add(attempt)
        db.flush()
        for item in result["skills"]:
            db.add(Evidence(user_id=user.id, attempt_id=attempt.id, version=bank.VERSION, **item))
        if success:
            passed = attempt
    profile = Profile(user_id=user.id, name="Алексей · демо", phone="+7 000 000-00-00",
        skills=["python", "testing"], roles="Бэкенд-разработчик", specialization="python",
        claimed_grade="Junior", verified_grade="Junior", verified_attempt_id=passed.id,
        grade_changed_at=passed.finished_at, published=True, processing=True,
        about="Вымышленный кандидат. Результаты тестов созданы для демонстрации.")
    db.add(profile)
    db.add(Consent(user_id=user.id, processing=True, publication=True))
    return profile


def seed(db):
    for account in ["candidate", "employer", "other_employer"]:
        email = account + "@demo.example.org"
        if db.scalar(select(User).where(User.email == email)):
            continue
        u = User(
            email=email,
            role="candidate" if account == "candidate" else "employer",
            password_hash=PASSWORDS.hash(secrets.token_urlsafe(32)),
            verified=True,
            demo=True,
        )
        db.add(u)
        db.flush()
        if u.role == "candidate":
            ready_candidate(db, u)
        else:
            db.add(Consent(user_id=u.id, processing=True, publication=False))
            c = Company(
                name="Вымышленная компания" if account == "employer" else "Вектор · демо",
                description="Создаём сервисы обработки данных и надёжные API. Демонстрационная компания.",
                sector="Разработка программного обеспечения",
                contact="team@demo.example.org",
            )
            db.add(c)
            db.flush()
            db.add(CompanyMember(user_id=u.id, company_id=c.id))
    names = [
        "Анна",
        "Михаил",
        "Дарья",
        "Илья",
        "Мария",
        "Денис",
        "Полина",
        "Артём",
        "София",
        "Олег",
        "Алина",
        "Иван",
    ]
    index = 0
    for spec in bank.SPECS:
        for grade in bank.GRADES:
            for variant in range(2):
                email = f"profile-{index}@demo.example.org"
                if db.scalar(select(User).where(User.email == email)):
                    index += 1
                    continue
                u = User(
                    email=email,
                    role="candidate",
                    password_hash=PASSWORDS.hash(secrets.token_urlsafe(32)),
                    verified=True,
                    demo=True,
                )
                db.add(u)
                db.flush()
                seed_value = f"demo-v1-{index}"
                qs = bank.generate(spec, grade, seed_value)
                answers = {q["id"]: q["answer"] for q in qs}
                if variant:
                    answers["4"] = "-9999"
                result = bank.grade_answers(qs, answers)
                a = Attempt(
                    user_id=u.id,
                    specialization=spec,
                    grade=grade,
                    seed=seed_value,
                    version=bank.VERSION,
                    variant_hash=bank.fingerprint(qs),
                    questions=qs,
                    answers=answers,
                    result=result,
                    status="completed",
                    created_at=now() - timedelta(days=10),
                    finished_at=now() - timedelta(days=10),
                    expires_at=now() - timedelta(days=10),
                )
                db.add(a)
                db.flush()
                for e in result["skills"]:
                    db.add(
                        Evidence(
                            user_id=u.id, attempt_id=a.id, version=bank.VERSION, **e
                        )
                    )
                achievements = (
                    []
                    if variant
                    else [
                        {
                            "provider": "demo_fsp",
                            "title": "Демонстрационный турнир",
                            "result": "Призёр",
                            "points": 2,
                            "date": "2026-09-01",
                            "verification": "simulated",
                        }
                    ]
                )
                db.add(
                    Profile(
                        user_id=u.id,
                        name=names[index] + " · демо",
                        phone="+7 000 000-00-00",
                        specialization=spec,
                        claimed_grade=grade,
                        verified_grade=grade,
                        verified_attempt_id=a.id,
                        grade_changed_at=now() - timedelta(days=10),
                        skills=list(dict.fromkeys(q["skill"] for q in qs)),
                        roles=bank.SPECS[spec],
                        soft_skills="Совместная работа, обратная связь (самодекларация)",
                        experience_years=[1, 4, 8][bank.GRADES.index(grade)],
                        published=True,
                        processing=True,
                        achievements=achievements,
                        about="Синтетический профиль для демонстрации.",
                    )
                )
                db.add(Consent(user_id=u.id, processing=True, publication=True))
                index += 1


if __name__ == "__main__":
    if os.getenv("DEMO_MODE", "false").lower() != "true":
        print("Demo seed disabled")
    else:
        with Session(create_engine(os.environ["DATABASE_URL"])) as db:
            seed(db)
            db.commit()
        print("Synthetic demo seed is ready; existing users preserved")

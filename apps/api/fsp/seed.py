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
        db.add(Consent(user_id=u.id, processing=True, publication=False))
        if u.role == "candidate":
            db.add(
                Profile(
                    user_id=u.id,
                    name="Алексей · демо",
                    skills=["python", "testing"],
                    roles="Бэкенд-разработчик",
                    about="Демонстрационный аккаунт для самостоятельного прохождения теста.",
                    experience_years=None,
                )
            )
        else:
            c = Company(
                name="Орбита · демо" if account == "employer" else "Вектор · демо",
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

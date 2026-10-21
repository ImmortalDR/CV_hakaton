"""Separate synthetic candidate/employer pairs for repeatable jury walkthroughs."""
import hashlib
import secrets

from sqlalchemy import and_, or_
from .models import DemoRun, User, Company, CompanyMember, Consent

REFERENCE_EMAILS = tuple(f"profile-{i}@demo.example.org" for i in range(12))


def visible_to(viewer, candidate):
    if viewer.demo_run_id:
        return candidate.demo_run_id == viewer.demo_run_id or (
            candidate.demo_run_id is None and candidate.demo and candidate.email in REFERENCE_EMAILS)
    return candidate.demo_run_id is None


def scope(viewer):
    if viewer.demo_run_id:
        return or_(User.demo_run_id == viewer.demo_run_id, and_(
            User.demo_run_id.is_(None), User.demo.is_(True), User.email.in_(REFERENCE_EMAILS)))
    return User.demo_run_id.is_(None)


def create_run(db):
    # Import at call time to avoid seed/main initialization cycles.
    from .main import PASSWORDS, digest
    from .seed import ready_candidate
    token = secrets.token_urlsafe(32)
    run = DemoRun(token_hash=digest(token))
    db.add(run)
    db.flush()
    candidate = None
    password_hash = PASSWORDS.hash(secrets.token_urlsafe(32))
    for role in ("candidate", "employer"):
        user = User(email=f"{role}-{run.id}@demo.example.org", password_hash=password_hash,
            role=role, verified=True, demo=True, demo_run_id=run.id)
        db.add(user)
        db.flush()
        if role == "candidate":
            candidate = user
            ready_candidate(db, user)
        else:
            company = Company(name="Вымышленная компания", sector="Разработка программного обеспечения",
                description="Создаём сервисы обработки данных и надёжные API. Демонстрационная компания.",
                contact="team@demo.example.org")
            db.add(company)
            db.flush()
            db.add(CompanyMember(user_id=user.id, company_id=company.id))
            db.add(Consent(user_id=user.id, processing=True, publication=False))
    return {"token": token, "candidate_code": hashlib.sha256(candidate.id.encode()).hexdigest()[:8].upper()}

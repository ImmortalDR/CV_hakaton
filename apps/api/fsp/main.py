import hashlib
import copy
import os
import secrets
import smtplib
import time
from collections import defaultdict, deque
from datetime import timedelta
from email.message import EmailMessage
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.openapi.utils import get_openapi
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession, sessionmaker

from . import bank, schemas as S, outputs as O
from .matching import eligible, group_sort, rank_candidate
from .models import (
    Attempt,
    Company,
    CompanyMember,
    Consent,
    ContactGrant,
    Evidence,
    Invitation,
    Message,
    Need,
    Profile,
    Session,
    Snapshot,
    User,
    Verification,
    now,
)
from .pdf import profile_pdf
from .fsp_provider import DemoProvider

PASSWORDS = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def fail(status, message):
    raise HTTPException(status, message)


def create_app(database_url=None, demo=None, rate_limit=True):
    app = FastAPI(
        title="ФСП · Обратный найм",
        version="1.0.0",
        description="Категории по тестам, объяснимый подбор и адресное согласие на контакты.",
        openapi_url="/api/openapi.json",
        docs_url=None,
        redoc_url=None,
        responses={
            code: {"model": O.Error, "description": message}
            for code, message in {
                400: "Недействительная ссылка",
                401: "Требуется вход",
                403: "Нет доступа",
                404: "Запись недоступна",
                409: "Конфликт состояния",
                413: "Запрос слишком большой",
                422: "Ошибка полей",
                429: "Ограничение частоты",
                503: "Внешний сервис недоступен",
            }.items()
        },
    )
    engine = create_engine(
        database_url or os.environ["DATABASE_URL"],
        pool_pre_ping=True,
        pool_size=15,
        max_overflow=25,
    )
    app.state.engine = engine
    factory = sessionmaker(engine, expire_on_commit=False)
    app.state.factory = factory
    is_demo = (
        (os.getenv("DEMO_MODE", "false").lower() == "true") if demo is None else demo
    )
    app.state.demo = is_demo
    secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    limits = defaultdict(deque)

    @app.middleware("http")
    async def security(request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if request.headers.get("x-requested-with") != "fsp-web":
                return JSONResponse(
                    {"detail": "Запрос не подтверждён приложением"}, status_code=403
                )
            try:
                length = int(request.headers.get("content-length", "0") or 0)
            except ValueError:
                return JSONResponse(
                    {"detail": "Некорректная длина запроса"}, status_code=400
                )
            if length > 65536:
                return JSONResponse(
                    {"detail": "Запрос слишком большой"}, status_code=413
                )
        if rate_limit and request.url.path in (
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/verify",
        ):
            key = request.client.host if request.client else "unknown"
            q = limits[key]
            t = time.monotonic()
            while q and q[0] < t - 60:
                q.popleft()
            if len(q) >= 20:
                return JSONResponse(
                    {"detail": "Слишком много попыток. Повторите через минуту."},
                    status_code=429,
                )
            q.append(t)
        res = await call_next(request)
        res.headers["Cache-Control"] = "no-store"
        res.headers["X-Content-Type-Options"] = "nosniff"
        res.headers["Referrer-Policy"] = "no-referrer"
        res.headers["X-Frame-Options"] = "DENY"
        return res

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Проверьте обязательные поля и допустимые значения.",
                "fields": [
                    {"field": ".".join(map(str, e["loc"][1:])), "type": e["type"]}
                    for e in exc.errors()
                ],
            },
        )

    @app.exception_handler(IntegrityError)
    async def conflict(request, exc):
        return JSONResponse(
            status_code=409,
            content={"detail": "Запись уже существует. Обновите страницу."},
        )

    def database():
        with factory() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    DB = Annotated[DBSession, Depends(database, scope="function")]

    def authenticated(request: Request, db: DB):
        raw = request.cookies.get("fsp_session", "")
        s = db.get(Session, digest(raw)) if raw else None
        if not s or s.expires_at <= now():
            fail(401, "Войдите в личный кабинет")
        u = db.get(User, s.user_id)
        if not u or not u.verified:
            fail(401, "Подтвердите адрес почты")
        return u

    AUTH = Annotated[User, Depends(authenticated)]

    def candidate(user, db, lock=False):
        if user.role != "candidate":
            fail(403, "Доступно только кандидату")
        stmt = select(Profile).where(Profile.user_id == user.id)
        if lock:
            stmt = stmt.with_for_update()
        return db.scalar(stmt)

    def company(user, db, lock=False):
        if user.role != "employer":
            fail(403, "Доступно только работодателю")
        m = db.get(CompanyMember, user.id)
        stmt = select(Company).where(Company.id == m.company_id)
        return db.scalar(stmt.with_for_update() if lock else stmt)

    def session_cookie(user, db, response):
        token = secrets.token_urlsafe(32)
        db.add(
            Session(
                token_hash=digest(token),
                user_id=user.id,
                expires_at=now() + timedelta(days=1),
            )
        )
        response.set_cookie(
            "fsp_session",
            token,
            httponly=True,
            secure=secure,
            samesite="lax",
            max_age=86400,
            path="/",
        )

    def evidence_for(p, db):
        if not p.verified_attempt_id:
            return []
        return [
            {
                "id": e.id,
                "skill": e.skill,
                "state": e.state,
                "correct": e.correct,
                "total": e.total,
                "attempt_id": e.attempt_id,
                "version": e.version,
                "date": e.created_at.isoformat(),
                "source": "assessment",
            }
            for e in db.scalars(
                select(Evidence).where(Evidence.attempt_id == p.verified_attempt_id)
            )
        ]

    def projection(p, viewer, db, company_id=None):
        owner = p.user_id == viewer.id
        if not owner and viewer.role != "employer":
            fail(403, "Чужой профиль недоступен")
        u = db.get(User, p.user_id)
        if not owner and (not p.processing or not p.published or not u.verified):
            fail(404, "Профиль не опубликован")
        permitted = owner or (
            company_id and db.get(ContactGrant, (p.user_id, company_id)) is not None
        )
        attempt = (
            db.get(Attempt, p.verified_attempt_id) if p.verified_attempt_id else None
        )
        result = {
            "id": p.user_id,
            "display_name": (
                p.name if permitted else bank.SPECS[p.specialization] + " · кандидат"
            ),
            "specialization": p.specialization,
            "verified_grade": p.verified_grade,
            "skills": p.skills,
            "experience_years": (
                p.experience_years if owner or p.show_experience else None
            ),
            "experience_source": "self_report",
            "evidence": evidence_for(p, db),
            "test_score": attempt.result["score"] if attempt else 0,
            "achievements": p.achievements,
            "demo": u.demo,
            "contacts": {"email": u.email, "phone": p.phone} if permitted else None,
        }
        if permitted:
            result.update(about=p.about, roles=p.roles, soft_skills=p.soft_skills)
        if owner:
            result.update(
                name=p.name,
                phone=p.phone,
                industry=p.industry,
                claimed_grade=p.claimed_grade,
                processing=p.processing,
                published=p.published,
                show_experience=p.show_experience,
                fsp_identity=p.fsp_identity,
                grade_changed_at=p.grade_changed_at,
                next_grade_change=(
                    p.grade_changed_at + timedelta(days=90)
                    if p.grade_changed_at
                    else None
                ),
            )
        return result

    def attempt_view(a):
        return {
            "id": a.id,
            "specialization": a.specialization,
            "grade": a.grade,
            "status": (
                "expired"
                if a.status == "active" and a.expires_at <= now()
                else a.status
            ),
            "version": a.version,
            "created_at": a.created_at,
            "expires_at": a.expires_at,
            "result": a.result,
            "questions": [
                {k: q[k] for k in ("id", "text", "skill")} for q in a.questions
            ],
        }

    def invitation_for(i, user, db):
        if user.role == "candidate":
            if i.candidate_id != user.id:
                fail(404, "Приглашение не найдено")
        elif company(user, db).id != i.company_id:
            fail(404, "Приглашение не найдено")
        p = db.get(Profile, i.candidate_id)
        data = {
            "id": i.id,
            "candidate_id": i.candidate_id,
            "company_name": i.company_name,
            "description": i.description,
            "salary_min": i.salary_min,
            "salary_max": i.salary_max,
            "currency": i.currency,
            "employer_contact": i.employer_contact,
            "status": i.status,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
            "candidate_name": bank.SPECS[p.specialization] + " · кандидат",
            "contacts": None,
        }
        if (
            user.role == "employer"
            and p.processing
            and p.published
            and db.get(ContactGrant, (p.user_id, i.company_id))
        ):
            data["contacts"] = projection(p, user, db, i.company_id)["contacts"]
            data["candidate_name"] = p.name
        return data

    @app.get(
        "/api/health",
        response_model=O.Health,
        response_model_exclude_unset=True,
        tags=["Система"],
    )
    def health(db: DB):
        db.execute(text("SELECT 1"))
        return {"status": "ok", "demo": is_demo, "version": "1.0.0"}

    @app.get(
        "/api/catalog",
        response_model=O.Catalog,
        response_model_exclude_unset=True,
        tags=["Справочники"],
    )
    def catalog():
        return {
            "specializations": bank.SPECS,
            "grades": bank.GRADES,
            "skills": bank.SKILLS,
            "bank_version": bank.VERSION,
            "grade_cooldown_days": 90,
            "retake_hours": 24,
            "demo": is_demo,
        }

    @app.post(
        "/api/auth/register",
        response_model=O.Registration,
        response_model_exclude_unset=True,
        status_code=201,
        tags=["Вход"],
    )
    def register(data: S.Registration, db: DB):
        email = str(data.email).lower()
        if db.scalar(select(User).where(User.email == email)):
            fail(409, "Адрес уже зарегистрирован")
        u = User(
            email=email,
            password_hash=PASSWORDS.hash(data.password),
            role=data.role,
            demo=is_demo,
        )
        db.add(u)
        db.flush()
        if u.role == "candidate":
            db.add(Profile(user_id=u.id))
        else:
            c = Company()
            db.add(c)
            db.flush()
            db.add(CompanyMember(user_id=u.id, company_id=c.id))
        db.add(Consent(user_id=u.id, processing=True, publication=False))
        token = secrets.token_urlsafe(32)
        db.add(
            Verification(
                token_hash=digest(token),
                user_id=u.id,
                expires_at=now() + timedelta(hours=1),
            )
        )
        link = (
            os.getenv("PUBLIC_URL", "http://localhost:3080").rstrip("/")
            + "/#verify="
            + token
        )
        if not is_demo:
            host = os.getenv("SMTP_HOST")
            if not host:
                fail(503, "Доставка почты пока не настроена. Обратитесь к оператору.")
            msg = EmailMessage()
            msg["To"] = email
            msg["From"] = os.getenv("SMTP_FROM", "noreply@example.org")
            msg["Subject"] = "Подтвердите почту — ФСП"
            msg.set_content("Подтвердите адрес в течение часа: " + link)
            try:
                with smtplib.SMTP(
                    host, int(os.getenv("SMTP_PORT", "587")), timeout=10
                ) as smtp:
                    if os.getenv("SMTP_TLS", "true") == "true":
                        smtp.starttls()
                    if os.getenv("SMTP_USER"):
                        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
                    smtp.send_message(msg)
            except (OSError, smtplib.SMTPException):
                fail(503, "Письмо не отправлено. Повторите регистрацию позже.")
        return {
            "message": "Подтвердите адрес почты",
            "demo_verification_url": link if is_demo else None,
            "delivery": "simulated" if is_demo else "smtp",
        }

    @app.post(
        "/api/auth/verify",
        response_model=O.Notice,
        response_model_exclude_unset=True,
        tags=["Вход"],
    )
    def verify(data: S.Verify, db: DB):
        v = db.scalar(
            select(Verification)
            .where(Verification.token_hash == digest(data.token))
            .with_for_update()
        )
        if not v or v.used or v.expires_at <= now():
            fail(400, "Ссылка недействительна или уже использована")
        v.used = True
        db.get(User, v.user_id).verified = True
        return {"message": "Почта подтверждена. Теперь войдите в кабинет."}

    @app.post(
        "/api/auth/login",
        response_model=O.User,
        response_model_exclude_unset=True,
        tags=["Вход"],
    )
    def login(data: S.Login, response: Response, db: DB):
        u = db.scalar(select(User).where(User.email == str(data.email).lower()))
        try:
            if not u or not PASSWORDS.verify(u.password_hash, data.password):
                fail(401, "Неверная почта или пароль")
        except VerificationError:
            fail(401, "Неверная почта или пароль")
        if not u.verified:
            fail(403, "Сначала подтвердите адрес почты")
        session_cookie(u, db, response)
        return {"id": u.id, "role": u.role, "email": u.email, "demo": u.demo}

    @app.post(
        "/api/auth/demo",
        response_model=O.User,
        response_model_exclude_unset=True,
        tags=["Вход"],
    )
    def demo_login(data: S.DemoLogin, response: Response, db: DB):
        if not is_demo:
            fail(404, "Недоступно")
        u = db.scalar(
            select(User).where(
                User.email == data.account + "@demo.example.org", User.demo.is_(True)
            )
        )
        if not u:
            fail(503, "Демонстрационные данные ещё не загружены")
        session_cookie(u, db, response)
        return {"id": u.id, "role": u.role, "email": u.email, "demo": True}

    @app.get(
        "/api/auth/me",
        response_model=O.User,
        response_model_exclude_unset=True,
        tags=["Вход"],
    )
    def me(user: AUTH):
        return {
            "id": user.id,
            "role": user.role,
            "email": user.email,
            "demo": user.demo,
        }

    @app.post(
        "/api/auth/logout",
        response_model=O.Notice,
        response_model_exclude_unset=True,
        tags=["Вход"],
    )
    def logout(request: Request, response: Response, db: DB):
        db.execute(
            delete(Session).where(
                Session.token_hash == digest(request.cookies.get("fsp_session", ""))
            )
        )
        response.delete_cookie("fsp_session", path="/")
        return {"message": "Вы вышли"}

    @app.get(
        "/api/me/profile",
        response_model=O.Profile,
        response_model_exclude_unset=True,
        tags=["Кандидат"],
    )
    def own_profile(user: AUTH, db: DB):
        return projection(candidate(user, db), user, db)

    @app.put(
        "/api/me/profile",
        response_model=O.Profile,
        response_model_exclude_unset=True,
        tags=["Кандидат"],
    )
    def update_profile(data: S.ProfileInput, user: AUTH, db: DB):
        p = candidate(user, db, True)
        if p.verified_grade and p.specialization != data.specialization:
            fail(409, "В MVP подтверждённая специализация закреплена за профилем")
        active = db.scalar(
            select(Attempt).where(
                Attempt.user_id == user.id, Attempt.status == "active"
            )
        )
        if (
            active
            and active.expires_at > now()
            and p.specialization != data.specialization
        ):
            fail(409, "Завершите текущий тест перед сменой специализации")
        changed = (p.processing, p.published) != (data.processing, data.published)
        for k, v in data.model_dump().items():
            setattr(p, k, v)
        if changed:
            db.add(
                Consent(
                    user_id=user.id, processing=p.processing, publication=p.published
                )
            )
            if not p.processing or not p.published:
                db.execute(
                    delete(ContactGrant).where(ContactGrant.candidate_id == user.id)
                )
        db.flush()
        return projection(p, user, db)

    @app.post(
        "/api/me/fsp",
        response_model=O.Profile,
        response_model_exclude_unset=True,
        tags=["Кандидат"],
    )
    def fsp_link(data: S.FspLink, user: AUTH, db: DB):
        p = candidate(user, db, True)
        if data.identity != "unlink" and not is_demo:
            fail(503, "Реестр ФСП пока не подключён")
        if not p.processing:
            fail(409, "Нужно согласие на обработку профиля")
        p.fsp_identity = (
            None if data.identity == "unlink" else data.identity + ":" + user.id
        )
        p.achievements = (
            []
            if data.identity == "unlink"
            else DemoProvider().achievements(data.identity)
        )
        return projection(p, user, db)

    @app.get(
        "/api/me/attempts",
        response_model=list[O.Attempt],
        response_model_exclude_unset=True,
        tags=["Тестирование"],
    )
    def attempts(user: AUTH, db: DB):
        candidate(user, db)
        return [
            attempt_view(a)
            for a in db.scalars(
                select(Attempt)
                .where(Attempt.user_id == user.id)
                .order_by(Attempt.created_at.desc())
            )
        ]

    @app.post(
        "/api/me/attempts",
        response_model=O.Attempt,
        response_model_exclude_unset=True,
        status_code=201,
        tags=["Тестирование"],
    )
    def start_attempt(data: S.StartAttempt, user: AUTH, db: DB):
        p = candidate(user, db, True)
        t = now()
        if not p.name or not p.processing:
            fail(409, "Заполните профиль и согласие на обработку")
        active = db.scalar(
            select(Attempt).where(
                Attempt.user_id == user.id, Attempt.status == "active"
            )
        )
        if active:
            if active.expires_at > t:
                return attempt_view(active)
            active.status = "expired"
            active.finished_at = t
        if (
            p.verified_grade
            and data.grade != p.verified_grade
            and t < p.grade_changed_at + timedelta(days=90)
        ):
            fail(
                409,
                "Смена подтверждённого уровня доступна через 90 дней после последнего изменения",
            )
        previous = db.scalar(
            select(Attempt)
            .where(
                Attempt.user_id == user.id,
                Attempt.grade == data.grade,
                Attempt.specialization == p.specialization,
            )
            .order_by(Attempt.created_at.desc())
        )
        if previous and previous.created_at + timedelta(hours=24) > t:
            fail(
                409,
                "Пересдача того же уровня доступна через 24 часа; первый тест ниже можно выбрать сразу",
            )
        for _ in range(20):
            seed = secrets.token_hex(16)
            qs = bank.generate(p.specialization, data.grade, seed)
            fp = bank.fingerprint(qs)
            if not db.scalar(select(Attempt.id).where(Attempt.variant_hash == fp)):
                break
        else:
            fail(503, "Не удалось подготовить новый вариант. Повторите позже.")
        a = Attempt(
            user_id=user.id,
            specialization=p.specialization,
            grade=data.grade,
            seed=seed,
            version=bank.VERSION,
            variant_hash=fp,
            questions=qs,
            expires_at=t + timedelta(minutes=30),
        )
        p.claimed_grade = data.grade
        db.add(a)
        db.flush()
        return attempt_view(a)

    @app.post(
        "/api/me/attempts/{attempt_id}/submit",
        response_model=O.Attempt,
        response_model_exclude_unset=True,
        tags=["Тестирование"],
    )
    def submit(attempt_id: str, data: S.Answers, user: AUTH, db: DB):
        p = candidate(user, db, True)
        a = db.scalar(
            select(Attempt)
            .where(Attempt.id == attempt_id, Attempt.user_id == user.id)
            .with_for_update()
        )
        if not a:
            fail(404, "Попытка не найдена")
        if a.status == "completed":
            return attempt_view(a)
        if a.status == "expired" or a.expires_at <= now():
            a.status = "expired"
            a.finished_at = now()
            db.commit()
            fail(409, "Время теста истекло. Грейд сохранён.")
        if not p.processing:
            fail(409, "Согласие на обработку отозвано")
        result = bank.grade_answers(a.questions, data.answers)
        a.answers = data.answers
        a.result = result
        a.status = "completed"
        a.finished_at = now()
        for e in result["skills"]:
            db.add(Evidence(user_id=user.id, attempt_id=a.id, version=a.version, **e))
        if result["passed"]:
            if p.verified_grade != a.grade:
                p.grade_changed_at = now()
            p.verified_grade = a.grade
            p.verified_attempt_id = a.id
        db.flush()
        return attempt_view(a)

    @app.get(
        "/api/me/company",
        response_model=O.Company,
        response_model_exclude_unset=True,
        tags=["Работодатель"],
    )
    def own_company(user: AUTH, db: DB):
        c = company(user, db)
        return {
            k: getattr(c, k) for k in ("id", "name", "description", "sector", "contact")
        }

    @app.put(
        "/api/me/company",
        response_model=O.Company,
        response_model_exclude_unset=True,
        tags=["Работодатель"],
    )
    def update_company(data: S.CompanyInput, user: AUTH, db: DB):
        c = company(user, db, True)
        for k, v in data.model_dump().items():
            setattr(c, k, v)
        return {
            k: getattr(c, k) for k in ("id", "name", "description", "sector", "contact")
        }

    @app.get(
        "/api/candidates",
        response_model=list[O.Profile],
        response_model_exclude_unset=True,
        tags=["Подбор"],
    )
    def candidates(
        user: AUTH,
        db: DB,
        specialization: S.Spec | None = None,
        grade: S.Grade | None = None,
        skill: str | None = None,
        fsp_only: bool = False,
    ):
        c = company(user, db)
        if skill and skill not in bank.SKILLS:
            fail(422, "Неизвестный навык")
        profiles = db.scalars(
            select(Profile)
            .join(User)
            .where(
                Profile.published.is_(True),
                Profile.processing.is_(True),
                User.verified.is_(True),
            )
        )
        results = []
        for p in profiles:
            if (
                specialization
                and p.specialization != specialization
                or grade
                and p.verified_grade != grade
            ):
                continue
            view = projection(p, user, db, c.id)
            if fsp_only and not view["achievements"]:
                continue
            if skill and not any(
                e["skill"] == skill and e["state"] == "met" for e in view["evidence"]
            ):
                continue
            view["match"] = rank_candidate(view, {})
            results.append(view)
        return group_sort(results)

    @app.get(
        "/api/candidates/{candidate_id}",
        response_model=O.Profile,
        response_model_exclude_unset=True,
        tags=["Подбор"],
    )
    def candidate_detail(candidate_id: str, user: AUTH, db: DB):
        c = company(user, db)
        p = db.get(Profile, candidate_id)
        if not p:
            fail(404, "Профиль не найден")
        return projection(p, user, db, c.id)

    @app.get("/api/profiles/{candidate_id}/pdf", tags=["Профили"])
    def pdf(candidate_id: str, user: AUTH, db: DB):
        p = db.get(Profile, candidate_id)
        if not p:
            fail(404, "Профиль не найден")
        cid = company(user, db).id if user.role == "employer" else None
        return Response(
            profile_pdf(projection(p, user, db, cid)),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="profile.pdf"'},
        )

    def snapshot_view(s, user, db):
        criteria = db.get(Need, s.need_id).criteria
        results = []
        hidden = 0
        for item in s.items:
            p = db.get(Profile, item["id"])
            if not p or not p.published or not p.processing:
                hidden += 1
                continue
            v = projection(p, user, db, s.company_id)
            # Keep historical, non-identifying proof; recheck consent/contacts on every read.
            v.update(item.get("assessment", {}))
            v["match"] = copy.deepcopy(item["match"])
            if not p.show_experience:
                for fact in v["match"]["facts"]:
                    if fact["skill"] == "experience":
                        fact["claimed_years"] = None
                        fact["source"] = "none"
            results.append(v)
        return {
            "id": s.id,
            "created_at": s.created_at,
            "criteria": criteria,
            "items": results,
            "hidden_count": hidden,
        }

    @app.post(
        "/api/searches",
        response_model=O.Snapshot,
        response_model_exclude_unset=True,
        status_code=201,
        tags=["Подбор"],
    )
    def search(data: S.NeedInput, user: AUTH, db: DB):
        c = company(user, db)
        criteria = data.model_dump()
        items = []
        profiles = db.scalars(
            select(Profile)
            .join(User)
            .where(
                Profile.published.is_(True),
                Profile.processing.is_(True),
                User.verified.is_(True),
            )
        )
        for p in profiles:
            v = projection(p, user, db, c.id)
            if eligible(v, criteria):
                v["match"] = rank_candidate(v, criteria)
                items.append(v)
        items = group_sort(items)
        n = Need(company_id=c.id, criteria=criteria)
        db.add(n)
        db.flush()
        s = Snapshot(
            company_id=c.id,
            need_id=n.id,
            items=[
                {
                    "id": v["id"],
                    "match": v["match"],
                    "assessment": {
                        k: v[k]
                        for k in (
                            "specialization",
                            "verified_grade",
                            "skills",
                            "evidence",
                            "test_score",
                            "achievements",
                        )
                    },
                }
                for v in items
            ],
        )
        db.add(s)
        db.flush()
        return snapshot_view(s, user, db)

    @app.get(
        "/api/searches",
        response_model=list[O.SearchHistory],
        response_model_exclude_unset=True,
        tags=["Подбор"],
    )
    def history(user: AUTH, db: DB):
        c = company(user, db)
        return [
            {
                "id": s.id,
                "created_at": s.created_at,
                "title": db.get(Need, s.need_id).criteria["title"],
            }
            for s in db.scalars(
                select(Snapshot)
                .where(Snapshot.company_id == c.id)
                .order_by(Snapshot.created_at.desc())
                .limit(50)
            )
        ]

    @app.get(
        "/api/searches/{snapshot_id}",
        response_model=O.Snapshot,
        response_model_exclude_unset=True,
        tags=["Подбор"],
    )
    def old_search(snapshot_id: str, user: AUTH, db: DB):
        c = company(user, db)
        s = db.get(Snapshot, snapshot_id)
        if not s or s.company_id != c.id:
            fail(404, "Подборка не найдена")
        return snapshot_view(s, user, db)

    @app.post(
        "/api/invitations",
        response_model=O.Invitation,
        response_model_exclude_unset=True,
        status_code=201,
        tags=["Приглашения"],
    )
    def invite(data: S.InviteInput, user: AUTH, db: DB):
        c = company(user, db, True)
        if not c.contact or not c.description:
            fail(409, "Сначала заполните профиль компании и способ связи")
        p = db.get(Profile, str(data.candidate_id))
        if not p:
            fail(404, "Кандидат не найден")
        projection(p, user, db, c.id)
        existing = db.scalar(
            select(Invitation).where(
                Invitation.company_id == c.id,
                Invitation.request_id == str(data.request_id),
            )
        )
        if existing:
            if any(
                str(getattr(existing, k)) != str(v)
                for k, v in data.model_dump().items()
            ):
                fail(
                    409,
                    "Ключ повторного запроса уже использован для другого предложения",
                )
            return invitation_for(existing, user, db)
        payload = data.model_dump(mode="json")
        i = Invitation(
            company_id=c.id,
            author_id=user.id,
            company_name=c.name,
            employer_contact=c.contact,
            **payload
        )
        db.add(i)
        db.flush()
        return invitation_for(i, user, db)

    @app.get(
        "/api/invitations",
        response_model=list[O.Invitation],
        response_model_exclude_unset=True,
        tags=["Приглашения"],
    )
    def invitations(user: AUTH, db: DB):
        condition = (
            Invitation.candidate_id == user.id
            if user.role == "candidate"
            else Invitation.company_id == company(user, db).id
        )
        return [
            invitation_for(i, user, db)
            for i in db.scalars(
                select(Invitation)
                .where(condition)
                .order_by(Invitation.created_at.desc())
            )
        ]

    @app.patch(
        "/api/invitations/{invitation_id}",
        response_model=O.Invitation,
        response_model_exclude_unset=True,
        tags=["Приглашения"],
    )
    def decide(invitation_id: str, data: S.Decision, user: AUTH, db: DB):
        p = candidate(user, db, True)
        i = db.scalar(
            select(Invitation)
            .where(Invitation.id == invitation_id, Invitation.candidate_id == user.id)
            .with_for_update()
        )
        if not i:
            fail(404, "Приглашение не найдено")
        if i.status == data.status:
            return invitation_for(i, user, db)
        if i.status in ("accepted", "rejected"):
            fail(409, "Решение уже принято")
        if data.status == "accepted":
            if not p.processing or not p.published:
                fail(409, "Для раскрытия контактов включите публикацию профиля")
            grant = db.get(ContactGrant, (user.id, i.company_id))
            if not grant:
                db.add(
                    ContactGrant(
                        candidate_id=user.id,
                        company_id=i.company_id,
                        invitation_id=i.id,
                    )
                )
        i.status = data.status
        i.updated_at = now()
        db.flush()
        return invitation_for(i, user, db)

    def chat_allowed(invitation_id, user, db):
        i = db.get(Invitation, invitation_id)
        if not i:
            fail(404, "Диалог не найден")
        invitation_for(i, user, db)
        p = db.get(Profile, i.candidate_id)
        if (
            i.status != "accepted"
            or not p.processing
            or not p.published
            or not db.get(ContactGrant, (p.user_id, i.company_id))
        ):
            fail(
                403,
                "Диалог доступен после принятия приглашения и при действующем согласии",
            )
        return i

    @app.get(
        "/api/invitations/{invitation_id}/messages",
        response_model=list[O.Message],
        response_model_exclude_unset=True,
        tags=["Диалог"],
    )
    def messages(invitation_id: str, user: AUTH, db: DB):
        chat_allowed(invitation_id, user, db)
        return [
            {
                "id": m.id,
                "text": m.text,
                "mine": m.author_id == user.id,
                "created_at": m.created_at,
            }
            for m in db.scalars(
                select(Message)
                .where(Message.invitation_id == invitation_id)
                .order_by(Message.created_at)
            )
        ]

    @app.post(
        "/api/invitations/{invitation_id}/messages",
        response_model=O.Message,
        response_model_exclude_unset=True,
        status_code=201,
        tags=["Диалог"],
    )
    def send_message(invitation_id: str, data: S.ChatInput, user: AUTH, db: DB):
        chat_allowed(invitation_id, user, db)
        m = Message(invitation_id=invitation_id, author_id=user.id, text=data.text)
        db.add(m)
        db.flush()
        return {"id": m.id, "text": m.text, "mine": True, "created_at": m.created_at}

    @app.get("/api/docs", include_in_schema=False, response_class=HTMLResponse)
    def api_documentation():
        return '<!doctype html><html lang="ru"><meta charset="utf-8"><title>API ФСП</title><h1>API ФСП · 1.0.0</h1><p><a href="/api/openapi.json">OpenAPI 3.1 — входы, ответы и ошибки</a></p><p>Авторизация: cookie fsp_session после подтверждения почты и входа. Для изменения данных нужен заголовок X-Requested-With: fsp-web.</p><p>Документация и примеры: docs/delivery/API.md в репозитории. Спецификацию можно импортировать в Swagger Editor или Postman.</p></html>'

    def public_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema["components"]["securitySchemes"] = {
            "SessionCookie": {"type": "apiKey", "in": "cookie", "name": "fsp_session"}
        }
        public = {
            "/api/health",
            "/api/catalog",
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/verify",
            "/api/auth/demo",
            "/api/auth/logout",
        }
        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                if path not in public:
                    operation["security"] = [{"SessionCookie": []}]
                if method in ("post", "put", "patch", "delete"):
                    operation.setdefault("parameters", []).append(
                        {
                            "name": "X-Requested-With",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string", "const": "fsp-web"},
                            "description": "Проверка same-origin запроса; значение fsp-web.",
                        }
                    )
                if path.endswith("/pdf"):
                    operation["responses"]["200"] = {
                        "description": "PDF по текущим правам получателя. Кириллица: встроенный DejaVu Sans.",
                        "content": {
                            "application/pdf": {
                                "schema": {"type": "string", "format": "binary"}
                            }
                        },
                    }
        app.openapi_schema = schema
        return schema

    app.openapi = public_openapi
    return app


def app_factory():
    return create_app()

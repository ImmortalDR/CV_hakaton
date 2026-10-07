from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from conftest import HEADERS, account, confirmed, employer, finish, profile
from fsp import main
from fsp.main import digest
from fsp.models import (
    Attempt,
    ContactGrant,
    Evidence,
    Invitation,
    Profile,
    Session,
    User,
    Verification,
    now,
)


def need(**changes):
    data = {
        "title": "Разработчик сервиса",
        "description": "Нужен разработчик API для команды",
        "specialization": "python",
        "grades": ["Junior"],
        "required_skills": ["python"],
        "desired_skills": [],
        "min_years": 2,
        "fsp_only": False,
        "confirmed": True,
    }
    return data | changes


def invite(c, candidate_id, **changes):
    data = {
        "candidate_id": candidate_id,
        "request_id": str(uuid4()),
        "description": "Разработка нового сервиса команды",
        "salary_min": 100000,
        "salary_max": 160000,
        "currency": "RUB",
    } | changes
    return c.post("/api/invitations", json=data), data


def test_registration_verification_expiry_hashes_and_logout(app):
    c, token = account(app, verify=False)
    credentials = {"email": "person@example.org", "password": "Only-test-password-43"}
    assert c.post("/api/auth/login", json=credentials).status_code == 403
    assert c.post("/api/auth/verify", json={"token": token}).status_code == 200
    assert c.post("/api/auth/verify", json={"token": token}).status_code == 400
    r = c.post("/api/auth/login", json=credentials)
    assert r.status_code == 200
    assert (
        "HttpOnly" in r.headers["set-cookie"]
        and "SameSite=lax" in r.headers["set-cookie"]
    )
    raw = c.cookies.get("fsp_session")
    with app.state.factory() as db:
        u = db.scalar(select(User))
        assert (
            u.password_hash.startswith("$argon2id$")
            and credentials["password"] not in u.password_hash
        )
        assert db.get(Session, digest(raw)) and not db.get(Session, raw)
        assert db.get(Verification, digest(token)) and not db.get(Verification, token)
    c.post("/api/auth/logout")
    assert c.get("/api/auth/me").status_code == 401
    assert (
        TestClient(app, cookies={"fsp_session": raw}).get("/api/auth/me").status_code
        == 401
    )
    other, expired = account(app, "expired@example.org", verify=False)
    with app.state.factory.begin() as db:
        db.get(Verification, digest(expired)).expires_at = now() - timedelta(seconds=1)
    assert other.post("/api/auth/verify", json={"token": expired}).status_code == 400


def test_roles_csrf_invalid_registration_and_sessions(app):
    anon = TestClient(app)
    assert anon.get("/api/me/profile").status_code == 401
    assert anon.post("/api/auth/register", json={}).status_code == 403
    c, _ = account(app)
    e = employer(app)
    assert c.get("/api/candidates").status_code == 403
    assert c.get("/api/me/company").status_code == 403
    assert e.get("/api/me/profile").status_code == 403
    assert e.post("/api/me/attempts", json={"grade": "Senior"}).status_code == 403
    assert (
        c.post(
            "/api/auth/register",
            json={
                "email": "root@example.org",
                "password": "Good-password-44",
                "role": "admin",
                "processing": True,
            },
        ).status_code
        == 422
    )
    assert (
        c.post(
            "/api/auth/register",
            json={
                "email": "x@example.org",
                "password": "Good-password-44",
                "role": "candidate",
                "processing": False,
            },
        ).status_code
        == 422
    )
    with app.state.factory.begin() as db:
        db.get(Session, digest(c.cookies.get("fsp_session"))).expires_at = (
            now() - timedelta(seconds=1)
        )
    assert c.get("/api/auth/me").status_code == 401


def test_server_grading_no_leaks_no_injection_and_idempotence(app):
    c, _ = account(app)
    p = profile(c, claimed_grade="Senior")
    assert p["verified_grade"] is None
    assert (
        c.post(
            "/api/me/attempts", json={"grade": "Junior", "seed": "chosen"}
        ).status_code
        == 422
    )
    a = c.post("/api/me/attempts", json={"grade": "Junior"}).json()
    assert a["result"] is None
    assert all(set(q) == {"id", "text", "skill"} for q in a["questions"])
    assert "seed" not in a and "variant_hash" not in a
    assert c.post("/api/me/attempts", json={"grade": "Senior"}).json()["id"] == a["id"]
    url = "/api/me/attempts/" + a["id"] + "/submit"
    assert c.post(url, json={"answers": {}, "score": 100}).status_code == 422
    assert (
        c.put("/api/me/profile", json={"verified_grade": "Senior"}).status_code == 422
    )
    r = finish(app, c, a)
    assert r.json()["result"]["score"] == 100
    assert c.post(url, json={"answers": {}}).json() == r.json()
    p = c.get("/api/me/profile").json()
    assert p["verified_grade"] == "Junior"
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Evidence)) == 2
    outsider, _ = account(app, "outsider@example.org")
    assert outsider.post(url, json={"answers": {}}).status_code == 404
    assert outsider.get("/api/profiles/" + p["id"] + "/pdf").status_code == 403


def test_failed_first_attempt_lower_choice_and_failed_retake_keeps_grade(
    app, monkeypatch
):
    c, _ = account(app)
    profile(c, claimed_grade="Senior")
    a = c.post("/api/me/attempts", json={"grade": "Senior"}).json()
    assert not finish(app, c, a, False).json()["result"]["passed"]
    assert c.get("/api/me/profile").json()["verified_grade"] is None
    junior = c.post("/api/me/attempts", json={"grade": "Junior"})
    assert junior.status_code == 201
    finish(app, c, junior.json())
    assert c.post("/api/me/attempts", json={"grade": "Middle"}).status_code == 409
    assert c.post("/api/me/attempts", json={"grade": "Junior"}).status_code == 409
    with app.state.factory.begin() as db:
        db.get(Attempt, junior.json()["id"]).created_at = now() - timedelta(hours=25)
    retake = c.post("/api/me/attempts", json={"grade": "Junior"}).json()
    finish(app, c, retake, False)
    assert c.get("/api/me/profile").json()["verified_grade"] == "Junior"
    assert len(c.get("/api/me/attempts").json()) == 3


def test_cooldown_exact_boundary_voluntary_downgrade_and_expiry(app, monkeypatch):
    c, _ = account(app)
    p = profile(c)
    a = c.post("/api/me/attempts", json={"grade": "Senior"}).json()
    finish(app, c, a)
    with app.state.factory() as db:
        changed = db.get(Profile, p["id"]).grade_changed_at
    with app.state.factory.begin() as db:
        db.get(Session, digest(c.cookies.get("fsp_session"))).expires_at = (
            changed + timedelta(days=100)
        )
    monkeypatch.setattr(
        main, "now", lambda: changed + timedelta(days=90) - timedelta(microseconds=1)
    )
    assert c.post("/api/me/attempts", json={"grade": "Junior"}).status_code == 409
    monkeypatch.setattr(main, "now", lambda: changed + timedelta(days=90))
    down = c.post("/api/me/attempts", json={"grade": "Junior"})
    assert down.status_code == 201
    finish(app, c, down.json())
    assert c.get("/api/me/profile").json()["verified_grade"] == "Junior"
    monkeypatch.setattr(main, "now", lambda: changed + timedelta(days=92))
    expired = c.post("/api/me/attempts", json={"grade": "Junior"}).json()
    monkeypatch.setattr(main, "now", lambda: changed + timedelta(days=92, minutes=30))
    assert finish(app, c, expired).status_code == 409
    assert c.get("/api/me/profile").json()["verified_grade"] == "Junior"


def test_retake_exact_24_hour_boundary_and_specialization_lock(app, monkeypatch):
    c, _ = account(app)
    profile(c)
    a = c.post("/api/me/attempts", json={"grade": "Junior"}).json()
    data = c.get("/api/me/profile").json()
    body = {
        "name": data["name"],
        "specialization": "data",
        "claimed_grade": "Junior",
        "processing": True,
        "published": False,
    }
    assert c.put("/api/me/profile", json=body).status_code == 409
    finish(app, c, a, False)
    with app.state.factory() as db:
        created = db.get(Attempt, a["id"]).created_at
    with app.state.factory.begin() as db:
        db.get(Session, digest(c.cookies.get("fsp_session"))).expires_at = (
            created + timedelta(days=2)
        )
    monkeypatch.setattr(
        main, "now", lambda: created + timedelta(hours=24) - timedelta(microseconds=1)
    )
    assert c.post("/api/me/attempts", json={"grade": "Junior"}).status_code == 409
    monkeypatch.setattr(main, "now", lambda: created + timedelta(hours=24))
    assert c.post("/api/me/attempts", json={"grade": "Junior"}).status_code == 201


@pytest.mark.parametrize(
    "bad",
    [
        {"salary_min": 0},
        {"salary_min": -1},
        {"salary_min": 200000, "salary_max": 100000},
        {"salary_max": None},
        {"salary_min": 1.1},
        {"currency": "USD"},
        {"description": ""},
        {"currency": None},
    ],
)
def test_invitation_salary_contract(app, bad):
    c, cid = confirmed(app)
    e = employer(app)
    assert invite(e, cid, **bad)[0].status_code == 422


def assert_no_contact(response):
    text = response.text if hasattr(response, "text") else str(response)
    for forbidden in (
        "Ирина Тестовая",
        "person@example.org",
        "+7 000 123-45-67",
        "private@example.org",
        "role-secret@example.org",
        "soft-secret@example.org",
    ):
        assert forbidden not in text


def pdf_text(response):
    assert response.status_code == 200
    with pymupdf.open(stream=response.content, filetype="pdf") as doc:
        return "\n".join(p.get_text() for p in doc)


def test_contacts_full_lifecycle_pdf_search_history_and_chat(app):
    c, cid = confirmed(app)
    e, e2 = employer(app), employer(app, "other@example.org")
    outsider, _ = account(app, "outsider@example.org")
    for path in ("/api/candidates", "/api/candidates/" + cid):
        assert_no_contact(e.get(path))
    snapshot = e.post("/api/searches", json=need()).json()
    assert snapshot["items"][0]["match"]["facts"][-1]["state"] == "unknown"
    assert_no_contact(snapshot)
    assert_no_contact(pdf_text(e.get("/api/profiles/" + cid + "/pdf")))
    assert "Ирина Тестовая" in pdf_text(c.get("/api/profiles/" + cid + "/pdf"))
    assert e2.get("/api/searches/" + snapshot["id"]).status_code == 404
    invitation, payload = invite(e, cid)
    assert invitation.status_code == 201
    iid = invitation.json()["id"]
    url = "/api/invitations/" + iid
    assert e.post("/api/invitations", json=payload).json()["id"] == iid
    assert (
        e.post("/api/invitations", json=payload | {"salary_max": 180000}).status_code
        == 409
    )
    assert c.get(url + "/messages").status_code == 403
    assert outsider.patch(url, json={"status": "accepted"}).status_code == 404
    assert e.patch(url, json={"status": "accepted"}).status_code == 403
    assert c.patch(url, json={"status": "viewed"}).json()["status"] == "viewed"
    assert e.get("/api/invitations").json()[0]["status"] == "viewed"
    assert c.patch(url, json={"status": "accepted"}).json()["status"] == "accepted"
    assert c.patch(url, json={"status": "accepted"}).status_code == 200
    assert c.patch(url, json={"status": "rejected"}).status_code == 409
    assert (
        e.get("/api/candidates/" + cid).json()["contacts"]["email"]
        == "person@example.org"
    )
    assert "person@example.org" in pdf_text(e.get("/api/profiles/" + cid + "/pdf"))
    assert_no_contact(e2.get("/api/candidates/" + cid))
    assert_no_contact(pdf_text(e2.get("/api/profiles/" + cid + "/pdf")))
    assert e2.get(url + "/messages").status_code == 404
    assert outsider.get(url + "/messages").status_code == 404
    assert (
        c.post(
            url + "/messages", json={"text": "Добрый день! Обсудим задачи."}
        ).status_code
        == 201
    )
    assert e.get(url + "/messages").json()[0]["text"] == "Добрый день! Обсудим задачи."
    # Hide experience: old evidence must not reveal it in explanation JSON.
    profile(c, show_experience=False)
    restored = e.get("/api/searches/" + snapshot["id"]).json()
    assert restored["items"][0]["experience_years"] is None
    assert restored["items"][0]["match"]["facts"][-1]["claimed_years"] is None
    # Withdraw publication: current and historical projections and chat all close.
    profile(c, published=False)
    assert e.get("/api/candidates/" + cid).status_code == 404
    assert e.get("/api/profiles/" + cid + "/pdf").status_code == 404
    assert e.get("/api/searches/" + snapshot["id"]).json()["hidden_count"] == 1
    assert e.get("/api/invitations").json()[0]["contacts"] is None
    assert e.get(url + "/messages").status_code == 403
    # Republishing does not silently resurrect consent via an idempotent replay.
    profile(c, published=True)
    assert c.patch(url, json={"status": "accepted"}).status_code == 200
    assert e.get("/api/candidates/" + cid).json()["contacts"] is None
    assert e.get(url + "/messages").status_code == 403
    second, _ = invite(e, cid)
    assert (
        c.patch(
            "/api/invitations/" + second.json()["id"], json={"status": "accepted"}
        ).status_code
        == 200
    )
    assert e.get("/api/candidates/" + cid).json()["contacts"] is not None


def test_rejection_never_grants_and_invitation_owner_lists(app):
    c, cid = confirmed(app)
    e = employer(app)
    e2 = employer(app, "other@example.org")
    other, _ = account(app, "outsider@example.org")
    r, _ = invite(e, cid)
    url = "/api/invitations/" + r.json()["id"]
    assert c.patch(url, json={"status": "rejected"}).status_code == 200
    assert c.patch(url, json={"status": "rejected"}).status_code == 200
    assert c.patch(url, json={"status": "accepted"}).status_code == 409
    assert other.get("/api/invitations").json() == []
    assert e2.get("/api/invitations").json() == []
    assert_no_contact(e.get("/api/invitations"))
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(ContactGrant)) == 0


def test_search_unknowns_empty_filters_history_and_fsp(app):
    c, cid = confirmed(app)
    e = employer(app)
    p = profile(c, experience_years=None, skills=["python", "docker"])
    search = e.post("/api/searches", json=need(required_skills=["docker"])).json()
    fact = search["items"][0]["match"]["facts"][0]
    assert fact["state"] == "unknown" and fact["source"] == "self_report"
    assert (
        e.post("/api/searches", json=need(title="", description="")).status_code == 422
    )
    assert e.post("/api/searches", json=need(confirmed=False)).status_code == 422
    assert (
        e.post("/api/searches", json=need(specialization="data")).json()["items"] == []
    )
    assert e.get("/api/candidates?skill=docker").json() == []
    assert (
        len(
            e.get(
                "/api/candidates?skill=python&grade=Junior&specialization=python"
            ).json()
        )
        == 1
    )
    assert e.get("/api/candidates?skill=madeup").status_code == 422
    assert e.get("/api/candidates?fsp_only=true").json() == []
    before = c.get("/api/me/profile").json()
    linked = c.post("/api/me/fsp", json={"identity": "demo-winner"}).json()
    assert linked["verified_grade"] == before["verified_grade"]
    assert linked["next_grade_change"] == before["next_grade_change"]
    assert linked["achievements"][0]["verification"] == "simulated"
    fsp = e.post("/api/searches", json=need(fsp_only=True)).json()
    assert fsp["items"][0]["match"]["breakdown"]["fsp"] == 3
    assert len(e.get("/api/candidates?fsp_only=true").json()) == 1
    assert (
        e.get("/api/searches/" + search["id"]).json()["items"][0]["achievements"] == []
    )
    assert len(e.get("/api/searches").json()) == 3
    c.post("/api/me/fsp", json={"identity": "unlink"})
    assert e.get("/api/candidates?fsp_only=true").json() == []
    profile(c, processing=False, published=False)
    assert c.post("/api/me/fsp", json={"identity": "demo-winner"}).status_code == 409
    assert c.post("/api/me/attempts", json={"grade": "Junior"}).status_code == 409


def test_concurrent_start_submit_invitation_and_accept_are_idempotent(app):
    c, _ = account(app)
    p = profile(c)
    e = employer(app)

    def run(fn):
        with ThreadPoolExecutor(max_workers=6) as pool:
            return list(pool.map(lambda _: fn(), range(6)))

    starts = run(lambda: c.post("/api/me/attempts", json={"grade": "Junior"}))
    assert all(r.status_code == 201 for r in starts)
    assert len({r.json()["id"] for r in starts}) == 1
    results = run(lambda: finish(app, c, starts[0].json()))
    assert all(r.json()["result"]["score"] == 100 for r in results)
    _, payload = invite(e, p["id"])
    offers = run(lambda: e.post("/api/invitations", json=payload))
    assert len({r.json()["id"] for r in offers}) == 1
    url = "/api/invitations/" + offers[0].json()["id"]
    assert all(
        r.status_code == 200
        for r in run(lambda: c.patch(url, json={"status": "accepted"}))
    )
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Attempt)) == 1
        assert db.scalar(select(func.count()).select_from(Evidence)) == 2
        assert db.scalar(select(func.count()).select_from(Invitation)) == 1
        assert db.scalar(select(func.count()).select_from(ContactGrant)) == 1


def test_non_demo_mail_failure_rolls_back_and_demo_disabled(app, monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    live = main.create_app(
        str(app.state.engine.url.render_as_string(hide_password=False)),
        demo=False,
        rate_limit=False,
    )
    c = TestClient(live, headers=HEADERS)
    assert c.post("/api/auth/demo", json={"account": "candidate"}).status_code == 404
    r = c.post(
        "/api/auth/register",
        json={
            "email": "smtp@example.org",
            "password": "Good-password-123",
            "role": "candidate",
            "processing": True,
        },
    )
    assert r.status_code == 503
    with app.state.factory() as db:
        assert db.scalar(select(User).where(User.email == "smtp@example.org")) is None
    live.state.engine.dispose()

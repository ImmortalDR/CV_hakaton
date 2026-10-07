import os
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from fsp.main import create_app
from fsp.models import Base

HEADERS = {"X-Requested-With": "fsp-web"}


@pytest.fixture(scope="session")
def pgapp():
    url = (
        os.getenv("TEST_DATABASE_URL")
        or os.environ["DATABASE_URL"].rsplit("/", 1)[0] + "/fsp_test"
    )
    # Never clear the application database, even if an operator supplies a wrong URL.
    if urlsplit(url).path != "/fsp_test":
        raise RuntimeError(
            "Integration tests require a separate database named fsp_test"
        )
    app = create_app(url, demo=True, rate_limit=False)
    Base.metadata.create_all(app.state.engine)
    yield app
    app.state.engine.dispose()


@pytest.fixture
def app(pgapp):
    with pgapp.state.engine.begin() as db:
        tables = ", ".join('"' + t.name + '"' for t in Base.metadata.sorted_tables)
        db.execute(text("TRUNCATE " + tables + " CASCADE"))
    return pgapp


def account(app, email="person@example.org", role="candidate", verify=True):
    c = TestClient(app, headers=HEADERS)
    r = c.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Only-test-password-43",
            "role": role,
            "processing": True,
        },
    )
    assert r.status_code == 201, r.text
    token = r.json()["demo_verification_url"].split("#verify=")[1]
    if verify:
        assert c.post("/api/auth/verify", json={"token": token}).status_code == 200
        assert (
            c.post(
                "/api/auth/login",
                json={"email": email, "password": "Only-test-password-43"},
            ).status_code
            == 200
        )
    return c, token


def profile(client, **changes):
    data = {
        "name": "Ирина Тестовая",
        "phone": "+7 000 123-45-67",
        "about": "Секретный адрес private@example.org",
        "specialization": "python",
        "claimed_grade": "Junior",
        "skills": ["python"],
        "roles": "Связь role-secret@example.org",
        "soft_skills": "soft-secret@example.org",
        "experience_years": 4,
        "processing": True,
        "published": True,
        "show_experience": True,
    }
    data.update(changes)
    r = client.put("/api/me/profile", json=data)
    assert r.status_code == 200, r.text
    return r.json()


def employer(app, email="employer@example.org"):
    c, _ = account(app, email, "employer")
    r = c.put(
        "/api/me/company",
        json={
            "name": "Компания Тест",
            "description": "Разработка продуктов для команд",
            "sector": "ИТ",
            "contact": "hr@example.org",
        },
    )
    assert r.status_code == 200
    return c


def finish(app, c, attempt, correct=True):
    from fsp.models import Attempt
    from evaluation.oracles import solve

    with app.state.factory() as db:
        a = db.get(Attempt, attempt["id"])
        answers = {
            q["id"]: str(solve(q)) if correct else "нет ответа" for q in a.questions
        }
    return c.post(
        "/api/me/attempts/" + attempt["id"] + "/submit", json={"answers": answers}
    )


def confirmed(app, email="person@example.org"):
    c, _ = account(app, email)
    p = profile(c)
    a = c.post("/api/me/attempts", json={"grade": "Junior"}).json()
    assert finish(app, c, a).json()["result"]["passed"]
    return c, p["id"]

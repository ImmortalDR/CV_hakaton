from datetime import timedelta
import re

import pytest

from conftest import account, profile, employer, finish, confirmed
from fsp import bank, main
from fsp.assessment import configured_rubric
from fsp.models import Attempt, Profile, Session, now
from test_api import pdf_text, invite, assert_no_contact


def levels(client):
    response = client.get('/api/me/assessment-availability')
    assert response.status_code == 200
    return {row['grade']: row for row in response.json()['levels']}


def test_configuration_matches_all_generated_categories():
    for spec, grade in bank.BLUEPRINT:
        qs = bank.generate(spec, grade, 'configuration-check')
        assert configured_rubric(spec, grade)['question_count'] == len(qs) == 8


@pytest.mark.parametrize('version', ['1.0.0', '1.1.0', '1.2.0', '2.0.0'])
def test_stored_attempt_count_rules_scoring_and_history(app, version):
    c, _ = account(app)
    profile(c)
    a = c.post('/api/me/attempts', json={'grade':'Junior'}).json()
    with app.state.factory.begin() as db:
        stored = db.get(Attempt, a['id'])
        stored.version = version
        stored.questions = bank.generate('python', 'Junior', version, version='1.1.0' if version == '1.0.0' else version)
        qs = stored.questions
    expected = 8 if version == '2.0.0' else 4
    row = c.get('/api/me/attempts').json()[0]
    assert row['rubric']['question_count'] == len(row['questions']) == expected
    assert row['rubric']['core_min_correct'] == bank.rubric(version)['core_min_correct']
    # Make the final question wrong: the last item must contribute to the score.
    answers = {q['id']: q['answer'] for q in qs[:-1]}
    result = c.post(f"/api/me/attempts/{a['id']}/submit", json={'answers':answers, 'confirm_incomplete': True})
    assert result.status_code == 200
    data = result.json()
    assert data['result']['score'] == (expected-1)*100/expected
    assert len(data['result']['details']) == expected
    assert data['result']['details'][-1]['correct'] is False
    assert c.get('/api/me/attempts').json()[0] == data


def test_count_uses_stored_questions_even_if_version_size_differs(app):
    c, _ = account(app); profile(c)
    a = c.post('/api/me/attempts', json={'grade':'Junior'}).json()
    with app.state.factory.begin() as db:
        db.get(Attempt, a['id']).version = '1.1.0'
    row = c.get('/api/me/attempts').json()[0]
    assert row['rubric']['question_count'] == len(row['questions']) == 8
    assert row['rubric']['core_min_correct'] == 0  # historical rules retained


def test_availability_agrees_with_start_at_24h_and_90d(app, monkeypatch):
    c, _ = account(app)
    assert not levels(c)['Junior']['available']
    assert levels(c)['Junior']['next_available_at'] is None
    profile(c)
    assert all(l['available'] for l in levels(c).values())
    a = c.post('/api/me/attempts', json={'grade':'Junior'}).json()
    assert all(not l['available'] for l in levels(c).values())
    finish(app, c, a)
    # The simulated clock jumps beyond the normal session lifetime. Keep only
    # this test session valid; production session/cooldown rules are unchanged.
    with app.state.factory.begin() as db:
        db.get(Session, main.digest(c.cookies.get('fsp_session'))).expires_at = now() + timedelta(days=100)
    with app.state.factory() as db:
        started = db.get(Attempt, a['id']).created_at
        changed = db.get(Profile, c.get('/api/auth/me').json()['id']).grade_changed_at
    for hours, allowed in [(24-1/3600, False), (24, True)]:
        monkeypatch.setattr(main, 'now', lambda: started + timedelta(hours=hours))
        access = levels(c)['Junior']
        assert access['available'] == allowed
        if not allowed:
            assert c.post('/api/me/attempts', json={'grade':'Junior'}).status_code == 409
    # Other levels remain blocked by the independently calculated 90-day rule.
    for delta, allowed in [(timedelta(days=90, microseconds=-1),False), (timedelta(days=90),True)]:
        monkeypatch.setattr(main, 'now', lambda: changed+delta)
        access = levels(c)['Middle']
        assert access['available'] == allowed
        r = c.post('/api/me/attempts', json={'grade':'Middle'})
        assert r.status_code == (201 if allowed else 409)


def test_multiple_restrictions_latest_date_and_no_downgrade(app, monkeypatch):
    c, _ = account(app); profile(c)
    a = c.post('/api/me/attempts', json={'grade':'Senior'}).json()
    finish(app, c, a, correct=False)
    assert levels(c)['Junior']['available']
    b = c.post('/api/me/attempts', json={'grade':'Junior'}).json()
    finish(app, c, b)
    access = levels(c)['Senior']
    assert {r['code'] for r in access['reasons']} == {'grade_change','retake'}
    assert access['next_available_at'] == max(r['until'] for r in access['reasons'])
    assert c.get('/api/me/profile').json()['verified_grade'] == 'Junior'


def test_pdf_readable_dates_and_addressed_contacts(app):
    c, cid = confirmed(app)
    e, e2 = employer(app), employer(app, 'other-employer@example.org')
    path = f'/api/profiles/{cid}/pdf'
    closed = pdf_text(e.get(path))
    assert_no_contact(closed)
    assert re.search(r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2} МСК \(UTC\+03:00\)', closed)
    assert not re.search(r'\d{4}-\d{2}-\d{2}T', closed)
    invitation, _ = invite(e, cid)
    c.patch('/api/invitations/'+invitation.json()['id'], json={'status':'accepted'})
    opened = pdf_text(e.get(path))
    assert 'Электронная почта: person@example.org' in opened
    assert 'Телефон:' in opened
    assert 'email:' not in opened and 'phone:' not in opened
    assert_no_contact(pdf_text(e2.get(path)))


def test_availability_is_private_and_salary_error_is_clear(app):
    e = employer(app)
    assert e.get('/api/me/assessment-availability').status_code == 403
    c, cid = confirmed(app)
    from uuid import uuid4
    r = e.post('/api/invitations', json={'candidate_id':cid,'request_id':str(uuid4()),
        'description':'Тестовое предложение','salary_min':200000,'salary_max':100000,'currency':'RUB'})
    assert r.status_code == 422
    assert 'Нижняя граница не должна превышать верхнюю' in r.json()['detail']

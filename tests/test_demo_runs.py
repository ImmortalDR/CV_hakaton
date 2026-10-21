from fastapi.testclient import TestClient
from sqlalchemy import select

from conftest import HEADERS, account, employer
from fsp.main import create_app
from fsp.models import User, Attempt, Profile
from fsp.seed import seed
from test_api import need, invite


def client(app):
    return TestClient(app, headers=HEADERS)


def start(app):
    c = client(app)
    response = c.post('/api/auth/demo-runs', json={})
    assert response.status_code == 201, response.text
    run = response.json()
    actors = []
    for role in ('candidate', 'employer'):
        actor = client(app)
        r = actor.post('/api/auth/demo', json={'account': role, 'run_token': run['token']})
        assert r.status_code == 200, r.text
        assert r.json()['demo_candidate_code'] == run['candidate_code']
        assert actor.get('/api/auth/me').json()['demo_run_id'] == r.json()['demo_run_id']
        actors.append(actor)
    return run, *actors


def test_demo_runs_start_identically_and_isolate_every_projection(app):
    with app.state.factory.begin() as db:
        seed(db)
    other = employer(app)
    first, c1, e1 = start(app)
    own = c1.get('/api/me/profile').json()
    assert own['published'] and own['verified_grade'] == 'Junior'
    assert own['candidate_code'] == first['candidate_code']
    history = c1.get('/api/me/attempts').json()
    assert [a['result']['score'] for a in history] == [50, 100]
    assert all(len(a['questions']) == 8 and len(a['answers']) == 8 for a in history)
    assert not history[0]['result']['passed'] and history[1]['result']['passed']
    assert all(e['state'] == 'met' for e in own['evidence'])
    before = e1.get('/api/candidates/' + own['id']).json()
    assert before['contacts'] is None and first['candidate_code'] in before['display_name']
    snap = e1.post('/api/searches', json=need()).json()
    assert own['id'] in [p['id'] for p in snap['items']]
    invitation, _ = invite(e1, own['id'])
    assert c1.patch('/api/invitations/' + invitation.json()['id'], json={'status':'accepted'}).status_code == 200
    assert e1.get('/api/candidates/' + own['id']).json()['contacts']

    second, c2, e2 = start(app)
    assert second['token'] != first['token'] and second['candidate_code'] != first['candidate_code']
    own2 = c2.get('/api/me/profile').json()
    assert [a['result']['score'] for a in c2.get('/api/me/attempts').json()] == [50, 100]
    for actor in (c2, e2):
        assert actor.get('/api/invitations').json() == []
        assert actor.get('/api/tasks').json()['plans'] == []
    assert e2.get('/api/searches').json() == []
    assert e2.get('/api/candidates/' + own2['id']).json()['contacts'] is None
    for outsider in (e2, other):
        assert outsider.get('/api/candidates', params={'candidate_code': first['candidate_code']}).json() == []
        assert outsider.get('/api/candidates/' + own['id']).status_code == 404
        assert outsider.get('/api/profiles/' + own['id'] + '/pdf').status_code == 404
        assert outsider.get('/api/searches/' + snap['id']).status_code == 404
        assert invite(outsider, own['id'])[0].status_code == 404
    assert own2['id'] not in [p['id'] for p in e1.get('/api/candidates').json()]
    # Rejoining a run preserves its completed work; it does not reset on every login.
    rejoin = client(app)
    assert rejoin.post('/api/auth/demo', json={'account':'employer','run_token':first['token']}).status_code == 200
    assert rejoin.get('/api/invitations').json()[0]['status'] == 'accepted'


def test_seed_provides_history_but_never_resets_existing_accounts(app):
    with app.state.factory.begin() as db:
        seed(db)
        user = db.scalar(select(User).where(User.email == 'candidate@demo.example.org'))
        p = db.get(Profile, user.id)
        original = p.verified_attempt_id
        p.published = False
        before = len(list(db.scalars(select(Attempt).where(Attempt.user_id == user.id))))
    with app.state.factory.begin() as db:
        seed(db)
        p = db.get(Profile, user.id)
        assert p.verified_attempt_id == original and not p.published
        assert len(list(db.scalars(select(Attempt).where(Attempt.user_id == user.id)))) == before == 2


def test_demo_run_invalid_token_and_disabled_production(app):
    c = client(app)
    assert c.post('/api/auth/demo', json={'account':'candidate','run_token':'x'*40}).status_code == 404
    assert c.post('/api/auth/demo', json={'account':'candidate','run_token':'bad'}).status_code == 422
    live = create_app(str(app.state.engine.url.render_as_string(hide_password=False)), demo=False, rate_limit=False)
    try:
        assert client(live).post('/api/auth/demo-runs', json={}).status_code == 404
    finally:
        live.state.engine.dispose()

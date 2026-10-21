from datetime import timedelta
from conftest import account, profile, finish
from fsp.models import Attempt, now


def test_draft_answers_owner_lifecycle(app):
    c, _ = account(app)
    profile(c)
    a = c.post('/api/me/attempts', json={'grade': 'Junior'}).json()
    url = f"/api/me/attempts/{a['id']}/answers"
    assert c.put(url, json={'answers': {'1': '42'}}).status_code == 200
    saved = c.get('/api/me/attempts').json()[0]
    assert saved['answers'] == {'1': '42'}
    assert saved['expires_at'] == a['expires_at']
    assert saved['result'] is None
    assert all(set(q) == {'id', 'text', 'skill'} for q in saved['questions'])
    other, _ = account(app, 'other@example.org')
    assert other.put(url, json={'answers': {'1': '9'}}).status_code == 404
    assert c.put(url, json={'answers': {'9': '9'}}).status_code == 422
    assert c.post('/api/me/attempts', json={'grade': 'Junior'}).json()['id'] == a['id']
    assert finish(app, c, a).status_code == 200
    assert c.put(url, json={'answers': {'1': '9'}}).status_code == 409


def test_draft_expired(app):
    c, _ = account(app)
    profile(c)
    a = c.post('/api/me/attempts', json={'grade': 'Junior'}).json()
    with app.state.factory() as db:
        db.get(Attempt, a['id']).expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert c.put(f"/api/me/attempts/{a['id']}/answers", json={'answers': {'1': '9'}}).status_code == 409

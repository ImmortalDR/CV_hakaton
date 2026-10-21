import pytest

from conftest import account, profile


def test_password_login_and_saved_session_describe_same_account(app):
    client, _ = account(app)
    login = client.post('/api/auth/login', json={
        'email': 'person@example.org', 'password': 'Only-test-password-43',
    }).json()
    restored = client.get('/api/auth/me').json()
    for field in ('id', 'email', 'role', 'demo'):
        assert restored[field] == login[field]
    saved = profile(client)
    assert client.get('/api/me/profile', headers={'X-FSP-User': restored['id']}).json() == saved


@pytest.mark.parametrize('other_role', ['candidate', 'employer'])
def test_stale_tab_cannot_read_or_write_under_replaced_session(app, other_role):
    first, _ = account(app, 'first@example.org')
    original = profile(first)
    old_id = first.get('/api/auth/me').json()['id']
    second, _ = account(app, 'second@example.org', role=other_role)
    second_id = second.get('/api/auth/me').json()['id']
    if other_role == 'candidate':
        second_profile = profile(second, name='Другой кандидат')
    # Browser tabs share cookies; the first tab still has the first user's UI.
    first.cookies.update(second.cookies)
    for path, method, body in [('/me/attempts', 'GET', None),
                                ('/me/profile', 'PUT', {'name': 'Ошибочное сохранение'})]:
        response = first.request(method, '/api' + path, json=body, headers={'X-FSP-User': old_id})
        assert response.status_code == 409
        assert response.headers['X-FSP-Session-Changed'] == 'true'
    assert first.get('/api/auth/me').json()['id'] == second_id
    if other_role == 'candidate':
        assert second.get('/api/me/profile').json() == second_profile
    # Re-login shows the first profile unchanged too.
    first.post('/api/auth/login', json={'email':'first@example.org', 'password':'Only-test-password-43'})
    assert first.get('/api/me/profile').json() == original

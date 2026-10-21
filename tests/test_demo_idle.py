from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from fsp import models as M, demo_idle
from fsp.seed import seed
from conftest import HEADERS, account, profile


def setup(app):
    with app.state.factory.begin() as db:
        seed(db)
        state = demo_idle.workspace(db)
        baseline = state.baseline
    clients = []
    for role in ('candidate', 'employer'):
        c = TestClient(app, headers=HEADERS)
        result = c.post('/api/auth/demo', json={'account': role})
        assert result.status_code == 200, result.text
        assert result.json()['demo_reset_version'] == 0
        clients.append(c)
    return baseline, clients


def expire(app):
    with app.state.factory.begin() as db:
        db.get(M.DemoWorkspace, 'shared').last_activity = M.now() - timedelta(hours=2)


def dirty(app, b):
    with app.state.factory.begin() as db:
        db.get(M.Profile, b['candidate']).name = 'Изменён'
        db.get(M.Profile, b['candidate']).published = False
        db.get(M.Company, b['company']).name = 'Изменена'
        invite = M.Invitation(company_id=b['company'], candidate_id=b['candidate'],
            author_id=b['employer'], request_id=M.uid(), description='test', salary_min=1,
            salary_max=2, company_name='test', employer_contact='test', status='accepted')
        db.add(invite); db.flush()
        db.add(M.Message(invitation_id=invite.id, author_id=b['candidate'], text='test'))
        db.add(M.ContactGrant(company_id=b['company'], candidate_id=b['candidate'], invitation_id=invite.id))
        need = M.Need(company_id=b['company'], criteria={}); db.add(need); db.flush()
        db.add(M.Snapshot(company_id=b['company'], need_id=need.id, items=[]))
        plan = M.TaskPlan(company_id=b['company'], candidate_id=b['candidate'], request_id=M.uid(),
            title='test', prompt='test', rubric='test', interval_days=7, response_days=3)
        db.add(plan); db.flush()
        db.add(M.TaskAssignment(plan_id=plan.id, sequence=1, version=1, title='test', prompt='test',
            rubric='test', due_at=M.now()+timedelta(days=1)))
        db.add(M.Attempt(user_id=b['candidate'], specialization='python', grade='Junior',
            seed='new', version='test', variant_hash=M.uid(), questions=[], expires_at=M.now()))


def test_reset_twice_preserves_baseline_and_other_accounts(app):
    b, clients = setup(app)
    real, _ = account(app, 'ordinary@example.org')
    real_profile = profile(real)
    with app.state.factory() as db:
        user_ids = set(db.scalars(select(M.User.id)))
        others = [demo_idle.encoded(p) for p in db.scalars(select(M.Profile).where(M.Profile.user_id != b['candidate']))]
    for generation in (1, 2):
        dirty(app, b)
        expire(app)
        assert demo_idle.reset_due(app.state.factory)
        assert not demo_idle.reset_due(app.state.factory)
        with app.state.factory() as db:
            assert set(db.scalars(select(M.User.id))) == user_ids
            assert [demo_idle.encoded(p) for p in db.scalars(select(M.Profile).where(M.Profile.user_id != b['candidate']))] == others
            assert db.get(M.Profile, b['candidate']).name == 'Алексей · демо'
            assert db.get(M.Profile, b['candidate']).published
            assert db.get(M.Company, b['company']).name == 'Вымышленная компания'
            assert set(db.scalars(select(M.Attempt.id).where(M.Attempt.user_id == b['candidate']))) == {a['id'] for a in b['attempts']}
            for model in (M.Invitation, M.Message, M.ContactGrant, M.Need, M.Snapshot, M.TaskPlan, M.TaskAssignment):
                assert db.scalar(select(func.count()).select_from(model)) == 0
        for c in clients:
            assert c.get('/api/auth/me').json()['demo_reset_version'] == generation
        assert real.get('/api/me/profile').json()['id'] == real_profile['id']


def test_get_polls_do_not_keep_alive_but_either_role_activity_does(app):
    b, clients = setup(app)
    for c in clients:
        expire(app)
        c.get('/api/auth/me')
        with app.state.factory() as db:
            assert M.now() - db.get(M.DemoWorkspace, 'shared').last_activity > demo_idle.IDLE
        assert c.post('/api/me/demo-activity', json={}).status_code == 200
        assert not demo_idle.reset_due(app.state.factory)


def test_stale_write_rejected_and_fresh_login_restores_expired_workspace(app):
    b, clients = setup(app)
    dirty(app, b); expire(app)
    c = clients[0]
    assert c.post('/api/auth/demo', json={'account': 'candidate'}).json()['demo_reset_version'] == 1
    stale = c.post('/api/me/demo-activity', json={}, headers={'X-FSP-Demo-Version': '0'})
    assert stale.status_code == 409
    assert stale.headers['X-FSP-Session-Changed'] == 'true'
    assert c.post('/api/me/demo-activity', json={}, headers={'X-FSP-Demo-Version': '1'}).status_code == 200


def test_reset_transaction_rollback_and_concurrent_schedulers(app):
    b, _ = setup(app)
    dirty(app, b); expire(app)
    with pytest.raises(RuntimeError):
        with app.state.factory.begin() as db:
            state = demo_idle.workspace(db)
            demo_idle.restore(db, state, M.now())
            raise RuntimeError('simulate failure before commit')
    with app.state.factory() as db:
        assert db.get(M.Profile, b['candidate']).name == 'Изменён'
        assert db.scalar(select(func.count()).select_from(M.Message)) == 1
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: demo_idle.reset_due(app.state.factory), range(2))) == [False, True]


def test_only_exact_shared_accounts_qualify(app):
    b, _ = setup(app)
    with app.state.factory() as db:
        assert sum(demo_idle.shared(u) for u in db.scalars(select(M.User))) == 2


def test_activity_transaction_blocks_reset_and_unrelated_history_survives(app):
    from threading import Event
    b, _ = setup(app)
    with app.state.factory.begin() as db:
        other = db.scalar(select(M.User).where(M.User.email == 'other_employer@demo.example.org'))
        ref = db.scalar(select(M.User).where(M.User.email == 'profile-0@demo.example.org'))
        member = db.get(M.CompanyMember, other.id)
        invite = M.Invitation(company_id=member.company_id, candidate_id=ref.id,
            author_id=other.id, request_id=M.uid(), description='preserve', salary_min=1,
            salary_max=2, company_name='other', employer_contact='other')
        db.add(invite); db.flush()
        invite_id = invite.id
        db.add(M.Message(invitation_id=invite.id, author_id=ref.id, text='preserve'))
    expire(app)
    started = Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with app.state.factory.begin() as db:
            state = demo_idle.workspace(db)
            def reset():
                started.set()
                return demo_idle.reset_due(app.state.factory)
            future = pool.submit(reset)
            assert started.wait(2)
            assert not future.done()
            state.last_activity = M.now()
        assert future.result(timeout=5) is False
    expire(app)
    assert demo_idle.reset_due(app.state.factory)
    with app.state.factory() as db:
        assert db.get(M.Invitation, invite_id).description == 'preserve'
        assert db.scalar(select(M.Message).where(M.Message.invitation_id == invite_id)).text == 'preserve'

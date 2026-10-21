"""One shared demo workspace, restored atomically after an hour without human activity."""
from datetime import datetime, timedelta
from copy import deepcopy
from sqlalchemy import select, delete, or_, text, DateTime
from . import models as M

LOCK = 734210216
IDLE = timedelta(hours=1)


def shared(user):
    return bool(user.demo and user.demo_run_id is None and
                (user.email, user.role) in {('candidate@demo.example.org', 'candidate'),
                                          ('employer@demo.example.org', 'employer')})


def encoded(row):
    return {c.name: (v.isoformat() if isinstance(v := getattr(row, c.name), datetime) else deepcopy(v))
            for c in row.__table__.columns}


def decoded(model, values):
    return {c.name: (datetime.fromisoformat(values[c.name]) if isinstance(c.type, DateTime)
                    and values[c.name] else deepcopy(values[c.name])) for c in model.__table__.columns}


def lock(db):
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': LOCK})


def workspace(db):
    # Same transaction lock is held by authenticated requests and the scheduler.
    lock(db)
    state = db.get(M.DemoWorkspace, 'shared')
    if state:
        return state
    users = list(db.scalars(select(M.User).where(M.User.email.in_(
        ['candidate@demo.example.org', 'employer@demo.example.org']))))
    if len(users) != 2 or not all(shared(u) for u in users):
        return None
    candidate = next(u for u in users if u.role == 'candidate')
    employer = next(u for u in users if u.role == 'employer')
    profile = db.get(M.Profile, candidate.id)
    member = db.get(M.CompanyMember, employer.id)
    if not profile or not member:
        return None
    attempts = list(db.scalars(select(M.Attempt).where(M.Attempt.user_id == candidate.id,
        M.Attempt.status == 'completed').order_by(M.Attempt.created_at)))
    if not attempts or not profile.verified_attempt_id:
        return None  # Never install an empty baseline over a usable demonstration.
    baseline = {'candidate': candidate.id, 'employer': employer.id, 'company': member.company_id,
        'attempts': [encoded(a) for a in attempts],
        'evidence': [encoded(e) for e in db.scalars(select(M.Evidence).where(
            M.Evidence.attempt_id.in_([a.id for a in attempts])))], 'profile': encoded(profile)}
    # Initial presentation is always public, without sporting achievements or trial edits.
    baseline['profile'].update(name='Алексей · демо', phone='+7 000 000-00-00',
        about='Вымышленный кандидат. Результаты тестов созданы для демонстрации.',
        specialization='python', claimed_grade='Junior', verified_grade='Junior',
        skills=['python', 'testing'], roles='Бэкенд-разработчик', soft_skills='',
        experience_years=None, processing=True, published=True, show_experience=True,
        fsp_identity=None, achievements=[])
    state = M.DemoWorkspace(id='shared', baseline=baseline, last_activity=M.now(), generation=0)
    db.add(state)
    db.flush()
    return state


def restore(db, state, at):
    b = state.baseline
    candidate, company = b['candidate'], b['company']
    invites = select(M.Invitation.id).where(or_(M.Invitation.candidate_id == candidate,
                                               M.Invitation.company_id == company))
    plans = select(M.TaskPlan.id).where(or_(M.TaskPlan.candidate_id == candidate,
                                         M.TaskPlan.company_id == company))
    db.execute(delete(M.Message).where(M.Message.invitation_id.in_(invites)))
    db.execute(delete(M.ContactGrant).where(or_(M.ContactGrant.candidate_id == candidate,
                                              M.ContactGrant.company_id == company)))
    db.execute(delete(M.Invitation).where(M.Invitation.id.in_(invites)))
    db.execute(delete(M.TaskAssignment).where(M.TaskAssignment.plan_id.in_(plans)))
    db.execute(delete(M.TaskPlan).where(M.TaskPlan.id.in_(plans)))
    db.execute(delete(M.Snapshot).where(M.Snapshot.company_id == company))
    db.execute(delete(M.Need).where(M.Need.company_id == company))
    db.execute(delete(M.Evidence).where(M.Evidence.user_id == candidate))
    db.execute(delete(M.Attempt).where(M.Attempt.user_id == candidate))
    db.flush()
    for values in b['attempts']:
        db.add(M.Attempt(**decoded(M.Attempt, values)))
    db.flush()
    for values in b['evidence']:
        db.add(M.Evidence(**decoded(M.Evidence, values)))
    profile = db.get(M.Profile, candidate)
    for key, value in decoded(M.Profile, b['profile']).items():
        setattr(profile, key, value)
    c = db.get(M.Company, company)
    c.name = 'Вымышленная компания'
    c.description = 'Создаём сервисы обработки данных и надёжные API. Демонстрационная компания.'
    c.sector = 'Разработка программного обеспечения'
    c.contact = 'team@demo.example.org'
    db.execute(delete(M.Consent).where(M.Consent.user_id.in_([candidate, b['employer']])))
    db.add_all([M.Consent(user_id=candidate, processing=True, publication=True),
                M.Consent(user_id=b['employer'], processing=True, publication=False)])
    state.generation += 1
    state.last_reset = at
    state.last_activity = at
    db.flush()


def reset_due(factory):
    with factory.begin() as db:
        state = workspace(db)
        if state and M.now() - state.last_activity >= IDLE:
            restore(db, state, M.now())
            return True
    return False

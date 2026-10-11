from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from conftest import account, confirmed, employer, profile
from fsp.models import Profile, TaskPlan, TaskAssignment, now
from fsp.tasks import run_due


def setup(app):
    c,cid=confirmed(app)
    e=employer(app)
    invitation=e.post('/api/invitations',json=dict(candidate_id=cid,request_id=str(uuid4()),description='Вымышленное предложение для проверки заданий',salary_min=100000,salary_max=150000,currency='RUB'))
    assert invitation.status_code==201
    assert c.patch('/api/invitations/'+invitation.json()['id'],json={'status':'accepted'}).status_code==200
    payload=dict(candidate_id=cid,request_id=str(uuid4()),title='Проверка API',prompt='Предложите способ повторять запросы безопасно при сетевых сбоях.',rubric='Оцените идемпотентность и ограничение числа повторов.',interval_days=7,response_days=3)
    return c,cid,e,payload


def create(e,payload):
    r=e.post('/api/tasks/plans',json=payload)
    assert r.status_code==201,r.text
    return r.json()


def activate(c,p):
    r=c.patch('/api/tasks/plans/'+p['id'],json={'status':'active'})
    assert r.status_code==200,r.text
    return r.json()


def test_task_complete_lifecycle_grade_and_contact_isolation(app):
    c,cid,e,payload=setup(app);other=employer(app,'other@example.org');outsider,_=account(app,'outsider@example.org')
    p=create(e,payload)
    assert p['status']=='awaiting' and p['assignments']==[]
    run_due(app.state.factory)
    assert c.get('/api/tasks').json()['pending']==1
    assert other.get('/api/tasks').json()['plans']==[]
    assert outsider.patch('/api/tasks/plans/'+p['id'],json={'status':'active'}).status_code==404
    assert e.patch('/api/tasks/plans/'+p['id'],json={'status':'active'}).status_code==403
    active=activate(c,p);a=active['assignments'][0]
    assert len(activate(c,p)['assignments'])==1
    assert other.post('/api/tasks/assignments/'+a['id']+'/review',json={'score':90,'feedback':'Корректный подход к идемпотентности'}).status_code==404
    answer={'answer':'Отдельный ответ с контактами private-task@example.org'}
    url='/api/tasks/assignments/'+a['id']
    assert c.post(url+'/answer',json=answer).status_code==200
    assert c.post(url+'/answer',json=answer).status_code==200
    assert c.post(url+'/answer',json={'answer':'Подмена ответа'}).status_code==409
    assert e.get('/api/tasks').json()['pending']==1
    review={'score':90,'feedback':'Учтены ключ запроса и ограниченные повторы'}
    assert e.post(url+'/review',json=review).status_code==200
    assert e.post(url+'/review',json=review).status_code==200
    assert e.post(url+'/review',json=review|{'score':80}).status_code==409
    assert c.post(url+'/review',json=review).status_code==403
    own=c.get('/api/me/profile').json();assert own['verified_grade']=='Junior' and own['task_last_reviewed_at']
    assert e.get('/api/candidates/'+cid).json()['task_last_reviewed_at']
    assert other.get('/api/candidates/'+cid).json().get('task_last_reviewed_at') is None
    assert 'private-task' not in other.get('/api/tasks').text
    # Revocation hides answers from the employer and pauses the plan; re-publication does not restore it.
    profile(c,published=False)
    item=e.get('/api/tasks').json()['plans'][0]
    assert item['status']=='paused' and item['assignments']==[] and not item['access_available']
    assert e.post(url+'/review',json=review).status_code==403
    profile(c,published=True)
    assert c.patch('/api/tasks/plans/'+p['id'],json={'status':'active'}).status_code==403
    with app.state.factory() as db: assert db.get(Profile,cid).verified_grade=='Junior'


def test_task_plan_idempotency_consent_and_schema(app):
    c,cid,e,payload=setup(app)
    first=create(e,payload);assert create(e,payload)['id']==first['id']
    assert e.post('/api/tasks/plans',json=payload|{'prompt':'Изменённое условие того же запроса'}).status_code==409
    assert e.post('/api/tasks/plans',json=payload|{'request_id':str(uuid4())}).status_code==409
    assert e.post('/api/tasks/plans',json=payload|{'response_days':8}).status_code==422
    assert e.post('/api/tasks/plans',json=payload|{'interval_days':0}).status_code==422
    assert c.post('/api/tasks/plans',json=payload).status_code==403
    assert employer(app,'new@example.org').post('/api/tasks/plans',json=payload).status_code==403
    assert c.patch('/api/tasks/plans/'+first['id'],json={'status':'closed'}).status_code==200
    assert c.patch('/api/tasks/plans/'+first['id'],json={'status':'active'}).status_code==409
    second=create(e,payload|{'request_id':str(uuid4())});assert second['id']!=first['id']


def test_scheduler_periodic_delivery_deduplicates_and_does_not_burst(app):
    c,cid,e,payload=setup(app);p=activate(c,create(e,payload))
    with app.state.factory() as db:
        plan=db.get(TaskPlan,p['id']);next_at=plan.next_issue_at
    run_due(app.state.factory, next_at-timedelta(seconds=1))
    assert len(c.get('/api/tasks').json()['plans'][0]['assignments'])==1
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _:run_due(app.state.factory,next_at),range(4)))
    rows=c.get('/api/tasks').json()['plans'][0]['assignments']
    assert [a['sequence'] for a in rows]==[2,1] and rows[-1]['status']=='expired'
    # A long outage creates one current task, not an accumulated burst.
    run_due(app.state.factory,next_at+timedelta(days=100))
    rows=c.get('/api/tasks').json()['plans'][0]['assignments'];assert len(rows)==3
    assert rows[0]['sequence']==3 and rows[0]['version']==1


def test_submitted_work_waits_for_review_and_pause_cancels_open_tasks(app):
    c,cid,e,payload=setup(app);p=activate(c,create(e,payload));a=p['assignments'][0]
    url='/api/tasks/assignments/'+a['id']+'/answer'
    assert c.post(url,json={'answer':'Проверенный подход с ключом идемпотентности'}).status_code==200
    run_due(app.state.factory,now()+timedelta(days=20))
    assert len(c.get('/api/tasks').json()['plans'][0]['assignments'])==1
    assert c.patch('/api/tasks/plans/'+p['id'],json={'status':'paused'}).status_code==200
    run_due(app.state.factory,now()+timedelta(days=30))
    assert len(c.get('/api/tasks').json()['plans'][0]['assignments'])==1
    assert e.post('/api/tasks/assignments/'+a['id']+'/review',json={'score':0,'feedback':'Ответ не объясняет ограничение числа повторов'}).status_code==200
    p=activate(c,p);assert len(p['assignments'])==2
    new=p['assignments'][0]
    assert c.patch('/api/tasks/plans/'+p['id'],json={'status':'paused'}).status_code==200
    assert c.post('/api/tasks/assignments/'+new['id']+'/answer',json={'answer':'Поздний ответ'}).status_code==409


def test_deadline_and_concurrent_answers(app):
    c,cid,e,payload=setup(app);p=activate(c,create(e,payload));a=p['assignments'][0]
    url='/api/tasks/assignments/'+a['id']+'/answer'
    with ThreadPoolExecutor(max_workers=3) as pool:
        codes=list(pool.map(lambda _:c.post(url,json={'answer':'Один и тот же ответ'}).status_code,range(3)))
    assert codes==[200,200,200]
    assert len(e.get('/api/tasks').json()['plans'][0]['assignments'])==1
    c.patch('/api/tasks/plans/'+p['id'],json={'status':'closed'})
    p=activate(c,create(e,payload|{'request_id':str(uuid4())}));a=p['assignments'][0]
    with app.state.factory.begin() as db: db.get(TaskAssignment,a['id']).due_at=now()-timedelta(seconds=1)
    assert c.post('/api/tasks/assignments/'+a['id']+'/answer',json={'answer':'Просроченный ответ'}).status_code==409
    assert c.get('/api/tasks').json()['plans'][0]['assignments'][0]['status']=='expired'

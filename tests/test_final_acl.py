"""Explicit negative access matrix, beyond UI hiding and happy-path smoke."""
from uuid import uuid4
from fastapi.testclient import TestClient
from conftest import HEADERS, account, confirmed, employer, profile
from test_api import need, invite
from test_employer_tasks import setup, create, activate


def test_anonymous_private_endpoint_matrix(app):
    client=TestClient(app,headers=HEADERS)
    ident=str(uuid4())
    routes=[('GET','/auth/me',None),('GET','/me/profile',None),('PUT','/me/profile',{}),
            ('GET','/me/company',None),('PUT','/me/company',{}),('GET','/me/attempts',None),
            ('GET','/me/assessment-availability',None),('POST','/me/attempts',{'grade':'Junior'}),
            ('PUT',f'/me/attempts/{ident}/answers',{'answers':{}}),
            ('POST',f'/me/attempts/{ident}/submit',{'answers':{}}),('POST','/me/fsp',{'identity':'demo-winner'}),
            ('GET','/candidates',None),('GET',f'/candidates/{ident}',None),('GET',f'/profiles/{ident}/pdf',None),
            ('GET','/searches',None),('POST','/searches',need()),('GET',f'/searches/{ident}',None),
            ('GET','/invitations',None),('POST','/invitations',{}),('PATCH',f'/invitations/{ident}',{'status':'accepted'}),
            ('GET',f'/invitations/{ident}/messages',None),('POST',f'/invitations/{ident}/messages',{'text':'Тест'}),
            ('GET','/tasks',None),('POST','/tasks/plans',{}),('PATCH',f'/tasks/plans/{ident}',{'status':'active'}),
            ('POST',f'/tasks/assignments/{ident}/answer',{'answer':'Тестовый ответ'}),
            ('POST',f'/tasks/assignments/{ident}/review',{'score':80,'feedback':'Тестовая оценка'})]
    for method,path,payload in routes:
        response=client.request(method,'/api'+path,json=payload)
        assert response.status_code==401,(method,path,response.status_code)


def test_foreign_writes_and_trimmed_forms(app):
    c,cid=confirmed(app)
    other,_=account(app,'outside-final@example.org')
    e=employer(app); e2=employer(app,'company-final@example.org')
    invitation,_=invite(e,cid); iid=invitation.json()['id']
    c.patch('/api/invitations/'+iid,json={'status':'accepted'})
    path='/api/invitations/'+iid+'/messages'
    assert c.post(path,json={'text':'   '}).status_code==422
    assert c.post(path,json={'text':'  Сообщение  '}).status_code==201
    assert e.get(path).json()[0]['text']=='Сообщение'
    for actor in [other,e2]:
        assert actor.post(path,json={'text':'Подмена'}).status_code==404
    for route in ['/me/profile','/me/attempts','/me/assessment-availability']:
        assert e.get('/api'+route).status_code==403
    for route in ['/me/company','/candidates','/searches']:
        assert c.get('/api'+route).status_code==403
    assert other.get('/api/profiles/'+cid+'/pdf').status_code==403
    before=e.get('/api/me/company').json()
    assert e.put('/api/me/company',json={k:before[k] for k in ['name','description','sector','contact']}|{'name':'  '}).status_code==422
    assert e.get('/api/me/company').json()==before
    profile(c,published=False)
    for actor in [c,e]:
        assert actor.post(path,json={'text':'После отзыва'}).status_code==403


def test_task_foreign_answer_and_plan_writes(app):
    c,cid,e,payload=setup(app)
    other,_=account(app,'outside-task-final@example.org')
    e2=employer(app,'company-task-final@example.org')
    plan=activate(c,create(e,payload)); assignment=plan['assignments'][0]
    assert other.post('/api/tasks/assignments/'+assignment['id']+'/answer',json={'answer':'Чужой ответ'}).status_code==404
    assert e2.patch('/api/tasks/plans/'+plan['id'],json={'status':'closed'}).status_code==404


def test_bulk_projection_preserves_privacy_and_constant_query_count(app):
    from sqlalchemy import event, select
    from fsp.models import Profile, User, Snapshot
    c,cid=confirmed(app)
    e=employer(app); other=employer(app,'bulk-other@example.org')
    invitation,_=invite(e,cid)
    c.patch('/api/invitations/'+invitation.json()['id'],json={'status':'accepted'})
    def queries(client):
        statements=[]
        def capture(conn,cursor,statement,parameters,context,executemany): statements.append(statement)
        event.listen(app.state.engine,'before_cursor_execute',capture)
        try: response=client.get('/api/candidates')
        finally: event.remove(app.state.engine,'before_cursor_execute',capture)
        assert response.status_code==200
        return response.json(),len(statements)
    _,small=queries(e)
    with app.state.factory.begin() as db:
        source=db.get(Profile,cid)
        for i in range(40):
            user=User(email=f'bulk-{i}@example.org',role='candidate',verified=True,demo=True,password_hash='unused')
            db.add(user);db.flush()
            db.add(Profile(user_id=user.id,published=True,processing=True,name='Не раскрывать',phone='private-phone',verified_grade='Junior',verified_attempt_id=source.verified_attempt_id))
    rows,large=queries(e)
    assert large <= small+1,(small,large)
    assert len(rows)==41
    assert next(p for p in rows if p['id']==cid)['contacts'] is not None
    assert all(p['contacts'] is None for p in rows if p['id']!=cid)
    foreign,_=queries(other)
    assert all(p['contacts'] is None for p in foreign)
    snapshot=e.post('/api/searches',json=need()).json()
    # An old snapshot retains its version, even after current ranking changed.
    with app.state.factory.begin() as db:
        old=db.get(Snapshot,snapshot['id'])
        import copy
        items=copy.deepcopy(old.items)
        for item in items: item['match']['methodology']='matching-1.1.0'
        old.items=items
        db.get(User,cid).verified=False
    saved=e.get('/api/searches/'+snapshot['id'])
    assert saved.status_code==200
    assert saved.json()['hidden_count']==1
    assert all(p['match']['methodology']=='matching-1.1.0' for p in saved.json()['items'])

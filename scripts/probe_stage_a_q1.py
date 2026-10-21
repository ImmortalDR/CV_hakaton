"""Additional Q1 adversarial probe on deployed HTTPS, independent of smoke assertions.

Exercises HTTP503, multi-question retry, reload cancellation and delayed PUT ACK.
Uses isolated fictional accounts; never resets application data. Run with
scripts/run_local.py .venv/bin/python scripts/probe_stage_a_q1.py.
"""
import argparse
import json
import os
import secrets
import re
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
import pymupdf
from playwright.sync_api import sync_playwright, expect
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session
from fsp.main import PASSWORDS
from fsp.models import User, Profile, Company, CompanyMember, Consent, Attempt, ContactGrant
from evaluation.oracles import solve

parser=argparse.ArgumentParser()
parser.add_argument('--base-url', default='https://85-137-26-131.sslip.io')
parser.add_argument('--out', default='docs/delivery/stage-a-smoke.json')
a=parser.parse_args(); engine=create_engine(os.environ['DATABASE_URL'])
checks=[]; errors=[]; run=uuid4().hex[:12]; accounts=[]
with Session(engine) as db:
    for role in ['candidate','employer','employer','candidate']:
        password=secrets.token_urlsafe(24)
        u=User(email=f'stage-a-{run}-{len(accounts)}@example.org',password_hash=PASSWORDS.hash(password),role=role,verified=True,demo=True)
        db.add(u);db.flush();db.add(Consent(user_id=u.id,processing=True,publication=role=='candidate'))
        if role=='candidate':
            db.add(Profile(user_id=u.id,name='' if len(accounts)==3 else 'Проверка этапа A · демо',processing=True,published=True,specialization='data',claimed_grade='Middle',skills=['sql','statistics'],phone='+7 000 000-00-00'))
        else:
            co=Company(name='Этап A · демо '+str(len(accounts)),description='Вымышленная компания для smoke этапа A',sector='ИТ',contact='smoke@example.org')
            db.add(co);db.flush();db.add(CompanyMember(user_id=u.id,company_id=co.id))
        accounts.append(dict(email=u.email,password=password,id=u.id))
    db.commit()

def pdf(response):
    assert response.status==200
    with pymupdf.open(stream=response.body(),filetype='pdf') as d: return ''.join(p.get_text() for p in d)

try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        actors=[]
        for creds in accounts:
            ctx=browser.new_context(base_url=a.base_url,locale='ru-RU',viewport={'width':1365,'height':1000},extra_http_headers={'X-Requested-With':'fsp-web'})
            r=ctx.request.post('/api/auth/login',data={k:creds[k] for k in ['email','password']});assert r.status==200
            page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));actors.append((ctx,page))
        (c,page),(e,hr),(other,_),(outsider,new_page)=actors
        def call(ctx,path,data=None,method=None):
            r=ctx.request.fetch('/api'+path,method=method or ('GET' if data is None else 'POST'),data=data)
            assert r.ok, (path,r.status,r.text()[:250])
            return r.json()
        def nav(p,name): p.locator('nav').get_by_role('button',name=name,exact=True).click()
        assert call(c,'/health')['status']=='ok'
        live=call(c,'/openapi.json'); assert live==json.loads(Path('docs/delivery/openapi.json').read_text())
        checks += ['https_health_ok','openapi_exact']
        page.goto(a.base_url);nav(page,'Подтверждение навыков')
        page.get_by_label('Уровень теста').select_option('Middle')
        page.get_by_role('button',name='Начать тест',exact=True).click()
        answer=page.get_by_label('Ответ на задание 1',exact=True)
        expect(answer).to_be_visible()
        answer.fill('11');expect(page.get_by_role('status')).to_have_text('Ответы сохранены')
        original=call(c,'/me/attempts')[0]
        # Different fault model: HTTP 503, not connection abort.
        c.route('**/api/me/attempts/*/answers', lambda r:r.fulfill(status=503,json={'detail':'Probe outage'}))
        answer.fill('22')
        expect(page.get_by_role('status')).to_contain_text('Не удалось сохранить')
        second=page.get_by_label('Ответ на задание 2',exact=True);second.fill('33')
        expect(page.get_by_role('status')).to_contain_text('Не удалось сохранить')
        assert call(c,'/me/attempts')[0]['answers']=={'1':'11'}
        dialogs=[]
        page.once('dialog',lambda d:(dialogs.append(d.type),d.dismiss()))
        page.evaluate('window.location.reload()')
        assert dialogs==['beforeunload']
        expect(answer).to_have_value('22');expect(second).to_have_value('33')
        c.unroute('**/api/me/attempts/*/answers')
        page.get_by_role('button',name='Повторить сохранение',exact=True).click()
        expect(page.get_by_role('status')).to_have_text('Ответы сохранены')
        assert call(c,'/me/attempts')[0]['answers']=={'1':'22','2':'33'}
        print('PASS independent HTTP503 / two dirty answers / cancel reload / manual flush',flush=True)
        # Delay the first successful PUT, then edit while it is in flight.
        held=[]
        def hold(r): held.append(r)
        c.route('**/api/me/attempts/*/answers',hold)
        answer.fill('44')
        for _ in range(30):
            if held:break
            page.wait_for_timeout(100)
        assert len(held)==1
        answer.fill('55');held[0].continue_()
        for _ in range(30):
            if len(held)>1:break
            page.wait_for_timeout(100)
        assert len(held)==2
        expect(answer).to_have_value('55')
        expect(page.get_by_role('status')).to_contain_text('несохранённые')
        assert call(c,'/me/attempts')[0]['answers']['1']=='44'
        held[1].continue_()
        expect(page.get_by_role('status')).to_have_text('Ответы сохранены')
        final=call(c,'/me/attempts')[0]
        assert final['answers']=={'1':'55','2':'33'}
        assert final['id']==original['id'] and final['expires_at']==original['expires_at']
        assert page.evaluate('(id)=>localStorage.getItem("fsp-attempt-"+id)',original['id']) is None
        print('PASS independent delayed ACK / newer edit retained / ordered flush / stable id and expiry',flush=True)
        browser.close()
finally:
    # Hide only the candidates created by this invocation, even on smoke failure.
    from fsp.tasks import suspend
    with Session(engine) as db:
        for item in accounts:
            profile=db.get(Profile,item['id'])
            if profile:
                profile.published=False
                db.add(Consent(user_id=item['id'],processing=True,publication=False))
                db.execute(delete(ContactGrant).where(ContactGrant.candidate_id==item['id']))
                suspend(db,item['id'])
        db.commit()
assert not errors, errors

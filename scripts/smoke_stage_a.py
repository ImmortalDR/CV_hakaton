"""Live Stage A smoke. Adds isolated fictional users; never resets existing data.

Run through scripts/run_local.py for the deployment's DATABASE_URL. Credentials
stay in memory. Bootstrap verified demo users directly (SMTP is not tested),
then exercise deployed HTTPS API and browser. Only own smoke profile is hidden.
"""
import argparse
import json
import os
import secrets
import re
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone, timedelta
import pymupdf
from playwright.sync_api import sync_playwright, expect
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session
from fsp.main import PASSWORDS
from fsp.models import User, Profile, Company, CompanyMember, Consent, Attempt, ContactGrant
from evaluation.oracles import solve
from fsp.bank import VERSION
from fsp import bank

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
        def nav(p,name):
            menu=p.get_by_role('button',name=re.compile('^Все разделы'))
            if menu.is_visible(): menu.click()
            p.locator('nav').get_by_role('button',name=name,exact=True).click()
        assert call(c,'/health')['status']=='ok'
        live=call(c,'/openapi.json'); assert live==json.loads(Path('docs/delivery/openapi.json').read_text())
        checks += ['https_health_ok','openapi_exact']
        # Published review credentials: read-only login check, no mutations.
        review=browser.new_context(base_url=a.base_url,extra_http_headers={'X-Requested-With':'fsp-web'})
        for email,password in [('review.candidate.fsp@example.org','Review-Cand-2026!'),('review.employer.fsp@example.org','Review-Emp-2026!'),('review.employer2.fsp@example.org','Review-Emp2-2026!')]:
            r=review.request.post('/api/auth/login',data=dict(email=email,password=password));assert r.status==200
        review.close();checks.append('three_review_logins_ok')
        new_page.goto(a.base_url);nav(new_page,'Приглашения')
        expect(new_page.get_by_text('Заполните профиль, чтобы начать путь',exact=False)).to_be_visible()
        nav(new_page,'Обзор');expect(new_page.get_by_role('button',name='Заполнить профиль',exact=True)).to_be_visible()
        page.goto(a.base_url);nav(page,'Приглашения')
        expect(page.get_by_text('Подтвердите навыки тестом',exact=False)).to_be_visible()
        nav(page,'Подтверждение навыков')
        page.get_by_label('Уровень теста').select_option('Middle')
        page.get_by_role('button',name='Начать тест',exact=True).click()
        answer=page.get_by_label('Ответ на задание 1',exact=True);expect(answer).to_be_visible()
        answer.fill('90,63');expect(page.get_by_role('status').filter(has_text='Ответы сохранены')).to_be_visible()
        started=call(c,'/me/attempts')[0];assert started['version']==VERSION
        assert any('90,625 → 90,63' in q['text'] for q in started['questions'])
        assert started['answers']['1']=='90,63' and started['result'] is None
        nav(page,'Обзор');nav(page,'Подтверждение навыков');expect(answer).to_have_value('90,63')
        page.reload();expect(answer).to_have_value('90,63')
        assert call(c,'/me/attempts')[0]['expires_at']==started['expires_at']
        assert outsider.request.put('/api/me/attempts/'+started['id']+'/answers',data={'answers':{'1':'999'}}).status==404
        checks+=['Q1_navigation_reload_server_draft_owner_expiry','Q2_live_bank_2_1_rounding_hint']
        # B01 negative acceptance: actual failed PUT, leave cancel/accept,
        # reload and tab recreation while offline, then automatic queue flush.
        c.route('**/api/me/attempts/*/answers', lambda route: route.abort())
        answer.fill('UNSAVED-123')
        expect(page.get_by_role('alert')).to_contain_text('Не удалось сохранить на сервере')
        assert call(c,'/me/attempts')[0]['answers']['1']=='90,63'
        leave=[]
        def cancel_leave(d): leave.append(d.type); d.dismiss()
        page.once('dialog',cancel_leave)
        nav(page,'Обзор')
        expect(answer).to_be_visible()
        assert leave==['confirm']
        page.once('dialog',lambda d:d.accept())
        nav(page,'Обзор');nav(page,'Подтверждение навыков')
        expect(answer).to_have_value('UNSAVED-123')
        expect(page.get_by_role('alert')).to_contain_text('Не удалось сохранить на сервере')
        unload=[]
        def accept_unload(d): unload.append(d.type);d.accept()
        page.once('dialog',accept_unload);page.reload()
        expect(answer).to_have_value('UNSAVED-123')
        expect(page.get_by_role('alert')).to_contain_text('Не удалось сохранить на сервере')
        assert unload==['beforeunload']
        answer.click()  # browser requires interaction before its unload dialog
        page.once('dialog',accept_unload)
        page.close(run_before_unload=True)
        page=c.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(a.base_url);nav(page,'Подтверждение навыков')
        answer=page.get_by_label('Ответ на задание 1',exact=True)
        expect(answer).to_have_value('UNSAVED-123')
        expect(page.get_by_role('alert')).to_contain_text('Не удалось сохранить на сервере')
        assert unload==['beforeunload','beforeunload']
        c.unroute('**/api/me/attempts/*/answers')
        page.once('dialog',lambda d:d.accept())
        nav(page,'Обзор');nav(page,'Подтверждение навыков')
        expect(page.get_by_role('status')).to_have_text('Ответы сохранены')
        recovered=call(c,'/me/attempts')[0]
        assert recovered['answers']['1']=='UNSAVED-123'
        assert recovered['id']==started['id'] and recovered['expires_at']==started['expires_at']
        assert page.evaluate('(id) => localStorage.getItem("fsp-attempt-"+id)',started['id']) is None
        page.reload();expect(answer).to_have_value('UNSAVED-123')
        answer.fill('90,63');expect(page.get_by_role('status')).to_have_text('Ответы сохранены')
        checks.append('Q1_failed_PUT_leave_cancel_accept_reload_close_reopen_retry_server_ack')
        rejected=c.request.post('/api/me/attempts/'+started['id']+'/submit',data={'answers':{'1':'90,63'}})
        assert rejected.status==409 and 'Подтвердите' in rejected.json()['detail']
        unchanged=call(c,'/me/attempts')[0]
        assert unchanged['status']=='active' and unchanged['answers']==started['answers'] and unchanged['expires_at']==started['expires_at']
        checks.append('Q3_direct_API_without_confirm_409_active_draft_unchanged')
        dialogs=[]
        def dismiss(d): dialogs.append(d.message);d.dismiss()
        page.once('dialog',dismiss);page.get_by_role('button',name='Завершить и узнать результат').click()
        assert '7 из 8' in dialogs[0]
        assert call(c,'/me/attempts')[0]['status']=='active'
        page.once('dialog',lambda d:d.accept());page.get_by_role('button',name='Завершить и узнать результат').click()
        expect(page.get_by_role('button',name='К выбору уровня')).to_be_visible()
        assert call(c,'/me/attempts')[0]['status']=='completed'
        checks.append('Q3_cancel_keeps_active_accept_completes')
        # New lower-level attempt, answers from an independent solver (not human skill).
        attempt=call(c,'/me/attempts',{'grade':'Junior'})
        with Session(engine) as db: qs=db.get(Attempt,attempt['id']).questions
        result=call(c,'/me/attempts/'+attempt['id']+'/submit',{'answers':{q['id']:str(solve(q)) for q in qs}})
        assert result['result']['passed']
        before=call(c,'/me/profile');cid=accounts[0]['id']
        fields=['name','phone','about','specialization','claimed_grade','skills','roles','soft_skills','experience_years','processing','published','show_experience']
        for published, text in [(True,'Ваш профиль опубликован, уровень подтверждён.'),(False,'Ваш уровень подтверждён. Включите публикацию')]:
            call(c,'/me/profile',{**{k:before[k] for k in fields},'published':published},'PUT')
            page.reload();nav(page,'Приглашения')
            expect(page.get_by_text(text,exact=False)).to_be_visible()
            expect(page.get_by_text('Подтвердите навыки и опубликуйте профиль',exact=False)).to_have_count(0)
            nav(page,'Обзор')
            expect(page.get_by_role('button',name='Посмотреть приглашения' if published else 'Настроить видимость',exact=True)).to_be_visible()
        nav(page,'Мой профиль')
        page.get_by_label('Публиковать профиль в банке кандидатов').check()
        page.get_by_role('button',name='Сохранить профиль',exact=True).click()
        expect(page.get_by_text('Профиль сохранён',exact=True)).to_be_visible()
        nav(page,'Обзор');expect(page.get_by_role('button',name='Посмотреть приглашения',exact=True)).to_be_visible()
        nav(page,'Приглашения');expect(page.get_by_text('Ваш профиль опубликован, уровень подтверждён.',exact=False)).to_be_visible()
        checks.append('Q4_verified_published_hidden_empty_invitations_and_overview_CTA')
        need=dict(title='Проверка аналитика',description='Вымышленные задачи аналитики для проверки',specialization='data',grades=['Junior'],required_skills=['sql'],desired_skills=['statistics'],min_years=None,fsp_only=False,confirmed=True)
        snap=call(e,'/searches',need)
        base_item=next(p for p in snap['items'] if p['id']==cid)
        assert base_item['contacts'] is None and base_item['match']['methodology']=='matching-1.2.0'
        linked=call(c,'/me/fsp',{'identity':'demo-winner'})
        assert linked['verified_grade']==before['verified_grade']
        new=call(e,'/searches',need);with_fsp=next(p for p in new['items'] if p['id']==cid)
        assert with_fsp['match']['score']-base_item['match']['score']==6
        assert call(e,'/searches/'+snap['id'])['id']==snap['id']
        closed_pdf=e.request.get('/api/profiles/'+cid+'/pdf')
        assert accounts[0]['email'] not in pdf(closed_pdf)
        (Path(a.out).parent/'closed-contacts.pdf').write_bytes(closed_pdf.body())
        inv=call(e,'/invitations',dict(candidate_id=cid,request_id=str(uuid4()),description='Предложение для smoke этапа A',salary_min=100000,salary_max=150000,currency='RUB'))
        assert inv['contacts'] is None
        assert inv['candidate_name']==base_item['display_name']
        assert base_item['display_name'] in pdf(e.request.get('/api/profiles/'+cid+'/pdf'))
        hr.goto(a.base_url);nav(hr,'Приглашения')
        expect(hr.get_by_role('heading',name=base_item['display_name'],exact=True)).to_be_visible()
        checks.append('Q5_anonymous_label_selection_invitation_PDF_UI')
        nav(hr,'Подбор кандидатов')
        card=hr.locator('.candidate-card').filter(has=hr.get_by_role('heading',name=base_item['display_name'],exact=True))
        expect(card.locator('.invitation-status')).to_contain_text('Отправлено')
        card.get_by_role('button',name='Открыть приглашения',exact=True).click()
        expect(hr.get_by_role('heading',name=base_item['display_name'],exact=True)).to_be_visible()
        call(c,'/invitations/'+inv['id'],{'status':'accepted'},'PATCH')
        assert call(e,'/candidates/'+cid)['contacts']['email']==accounts[0]['email']
        assert call(other,'/candidates/'+cid)['contacts'] is None
        open_pdf=e.request.get('/api/profiles/'+cid+'/pdf')
        assert accounts[0]['email'] in pdf(open_pdf)
        (Path(a.out).parent/'open-contacts.pdf').write_bytes(open_pdf.body())
        assert accounts[0]['email'] not in pdf(other.request.get('/api/profiles/'+cid+'/pdf'))
        assert outsider.request.get('/api/profiles/'+cid+'/pdf').status==403
        checks+=['invite_accept_addressed_contacts_PDF_isolation','FSP_does_not_change_grade_zero_without_FSP','old_snapshot_preserved']
        # Q5 browser persistence and score components.
        hr.goto(a.base_url);nav(hr,'Подбор кандидатов')
        hr.get_by_label('Специализация').select_option('data')
        hr.get_by_role('button',name='Применить фильтры').click()
        nav(hr,'Обзор');nav(hr,'Подбор кандидатов');expect(hr.get_by_label('Специализация')).to_have_value('data')
        hr.reload();expect(hr.get_by_label('Специализация')).to_have_value('data')
        hr.get_by_role('button',name='По потребности',exact=True).click()
        hr.get_by_label('Специализация').select_option('data')
        hr.get_by_role('button',name='Сформировать подборку',exact=True).click()
        expect(hr.get_by_text('Сохранённая подборка на',exact=False)).to_be_visible()
        lines=hr.locator('.candidate-card .evidence > small')
        expect(lines.first).to_be_visible()
        expect(hr.locator('.search-form label.field').filter(has=hr.get_by_text('SQL',exact=True)).locator('select')).to_have_count(1)
        context=hr.locator('details').filter(has=hr.get_by_text('Контекст для обсуждения · не влияет на баллы',exact=True))
        expect(context).not_to_have_attribute('open','')
        expect(hr.locator('.candidate-card').filter(has=hr.get_by_role('heading',name=before['name'],exact=True)).locator('.invitation-status')).to_contain_text('Принято')
        assert lines.count()>=2
        for line in lines.all_text_contents()[:2]:
            values=[float(x) for x in re.findall(r'\d+\.\d{2}',line)]
            assert len(values)==4 and abs(values[0]-sum(values[1:]))<=0.02,line
        labels=hr.locator('.candidate-card h3').all_text_contents()
        assert len(labels)==len(set(labels))
        latest=call(e,'/searches')[0]['id']
        expected_order=[p['display_name'] for p in call(e,'/searches/'+latest)['items']]
        assert labels==expected_order, 'UI must keep server score order within categories'
        checks.append('matching_UI_order_equals_server')
        hr.get_by_label('Специализация').select_option('python')
        expect(hr.get_by_text('Параметры изменены',exact=False)).to_be_visible()
        hr.evaluate('window.scrollTo(0, 400)');hr.wait_for_timeout(200)
        scroll=hr.evaluate('window.scrollY');assert scroll>0
        nav(hr,'Обзор');nav(hr,'Подбор кандидатов')
        hr.wait_for_timeout(500)
        assert abs(hr.evaluate('window.scrollY')-scroll)<5
        checks.append('Q5_two_visible_score_sums_unique_labels_changed_banner_scroll')
        nav(hr,'Обзор');nav(hr,'Подбор кандидатов');expect(hr.get_by_text('Сохранённая подборка на',exact=False)).to_be_visible()
        checks.append('Q5_filters_snapshot_and_score_UI')
        # Q6 actual HTTP pause/resume after review.
        plan=call(e,'/tasks/plans',dict(candidate_id=cid,request_id=str(uuid4()),title='Проверка периода',prompt='Опишите безопасный повтор операции при сбое соединения.',rubric='Проверить идемпотентность и ограничение повторов.',interval_days=7,response_days=3))
        active=call(c,'/tasks/plans/'+plan['id'],{'status':'active'},'PATCH');task=active['assignments'][0]
        call(c,'/tasks/assignments/'+task['id']+'/answer',{'answer':'Ключ идемпотентности и ограничение повторов.'})
        nav(hr,'Задания от компаний')
        grade=hr.get_by_label('Оценка от 0 до 100',exact=True)
        expect(grade).to_be_visible();grade.fill('0');grade.fill('');expect(grade).to_have_value('')
        grade.fill('85')
        call(e,'/tasks/assignments/'+task['id']+'/review',{'score':85,'feedback':'Проверены ключ и ограничение числа попыток.'})
        checks.append('numeric_grade_can_clear_zero')
        call(c,'/tasks/plans/'+plan['id'],{'status':'paused'},'PATCH')
        resumed=call(c,'/tasks/plans/'+plan['id'],{'status':'active'},'PATCH')
        assert len(resumed['assignments'])==1 and resumed['next_issue_at']==active['next_issue_at']
        page.reload();nav(page,'Задания от компаний')
        expected_date=page.evaluate('(value) => new Date(value).toLocaleString("ru-RU", {timeZone:"Europe/Moscow", dateStyle:"medium", timeStyle:"short"})',resumed['next_issue_at'])
        date_line=page.get_by_text('Следующая выдача не ранее',exact=False)
        expect(date_line).to_contain_text(expected_date+' МСК (UTC+03:00)')
        call(c,'/tasks/plans/'+plan['id'],{'status':'closed'},'PATCH');checks.append('Q6_live_7day_resume_no_duplicate_UI_date_equals_API')
        # Extended audit: whitespace, salary, focus trap and real error recovery.
        nav(hr,'Моя компания')
        company_name=hr.get_by_label('Название компании',exact=True)
        original=company_name.input_value()
        company_name.fill('   ')
        hr.get_by_role('button',name='Сохранить компанию',exact=True).click()
        expect(hr.get_by_text('Заполните поле «Название компании».',exact=True)).to_be_visible()
        expect(company_name).to_be_focused()
        company_name.fill(original)
        expect(hr.get_by_text('Заполните поле «Название компании».',exact=True)).to_have_count(0)
        nav(hr,'Подбор кандидатов')
        hr.get_by_role('button',name='Банк кандидатов',exact=True).click()
        expect(hr.get_by_role('heading',name='Банк кандидатов',exact=True)).to_be_visible()
        expect(hr.get_by_text('Сохранённая подборка на',exact=False)).to_have_count(0)
        trigger=hr.locator('.candidate-card').first.get_by_role('button',name='Пригласить',exact=True)
        trigger.click()
        modal=hr.get_by_role('dialog')
        expect(modal.get_by_label('Предложение и задачи')).to_be_focused()
        lower=modal.get_by_label('Зарплата от, ₽ / месяц',exact=True)
        upper=modal.get_by_label('Зарплата до, ₽ / месяц',exact=True)
        lower.fill('');expect(lower).to_have_value('')
        lower.fill('0');lower.fill('');expect(lower).to_have_value('')
        lower.fill('200000')
        expect(upper).to_have_value('160000')
        modal.get_by_role('button',name='Отправить приглашение',exact=True).click()
        expect(modal.get_by_role('alert')).to_contain_text('Нижняя граница')
        expect(lower).to_be_focused()
        upper.fill('250000')
        expect(modal.get_by_role('alert')).to_have_count(0)
        expect(modal.locator('.invitation-preview')).to_contain_text('250')
        modal.get_by_role('button',name='Закрыть приглашение').focus()
        hr.keyboard.press('Shift+Tab')
        expect(modal.get_by_role('button',name='Отправить приглашение',exact=True)).to_be_focused()
        hr.keyboard.press('Tab')
        expect(modal.get_by_role('button',name='Закрыть приглашение')).to_be_focused()
        hr.once('dialog',lambda d:d.dismiss());hr.keyboard.press('Escape')
        expect(modal).to_be_visible()
        hr.screenshot(path=str(Path(a.out).parent/'invitation-salary.png'))
        hr.set_viewport_size({'width':360,'height':740})
        assert hr.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        expect(modal.get_by_role('button',name='Отправить приглашение',exact=True)).to_be_visible()
        hr.screenshot(path=str(Path(a.out).parent/'invitation-mobile.png'))
        hr.set_viewport_size({'width':1365,'height':1000})
        hr.once('dialog',lambda d:d.accept());hr.keyboard.press('Escape')
        expect(modal).to_have_count(0);expect(trigger).to_be_focused()
        checks.append('B07_trimmed_company_B08_focus_escape_restore_U05_no_salary_mutation')
        nav(hr,'Приглашения');hr.get_by_role('button',name='Открыть диалог').click()
        message=hr.get_by_label('Сообщение',exact=True)
        message.fill('Первая проверка сохранения переписки')
        hr.get_by_role('button',name='Отправить',exact=True).click()
        expect(hr.locator('.message').filter(has_text='Первая проверка')).to_be_visible()
        message.fill('   ')
        expect(hr.get_by_role('button',name='Отправить',exact=True)).to_be_disabled()
        for status in [422,503]:
            message.fill('Черновик после ошибки '+str(status))
            def fail_post(route):
                if route.request.method=='POST': route.fulfill(status=status,json={'detail':'Исправимая ошибка'})
                else: route.continue_()
            hr.route('**/api/invitations/*/messages',fail_post)
            hr.get_by_role('button',name='Отправить',exact=True).click()
            expect(hr.locator('.chat [role="alert"]')).to_be_visible()
            expect(message).to_have_value('Черновик после ошибки '+str(status))
            expect(hr.locator('.message').filter(has_text='Первая проверка')).to_be_visible()
            hr.unroute('**/api/invitations/*/messages',fail_post)
        hr.screenshot(path=str(Path(a.out).parent/'chat-recovery.png'),full_page=True)
        hr.get_by_role('button',name='Отправить',exact=True).click()
        expect(message).to_have_value('')
        expect(hr.locator('.message').filter(has_text='Черновик после ошибки 503')).to_be_visible()
        checks.append('B07_chat_whitespace_422_503_preserves_messages_draft_retry')
        # Q4 hide with an open employer chat: poll must close input.
        expect(hr.get_by_label('Сообщение',exact=True)).to_be_visible()
        own=call(c,'/me/profile')
        fields=['name','phone','about','specialization','claimed_grade','skills','roles','soft_skills','experience_years','processing','published','show_experience']
        payload={k:own[k] for k in fields};payload['published']=False
        call(c,'/me/profile',payload,'PUT')
        expect(hr.get_by_label('Сообщение',exact=True)).to_have_count(0,timeout=20000)
        expect(hr.get_by_text(accounts[0]['email'],exact=False)).to_have_count(0,timeout=20000)
        checks.append('revoked_contacts_disappear_without_reload')
        assert e.request.get('/api/profiles/'+cid+'/pdf').status==404
        assert not next(i for i in call(e,'/invitations') if i['id']==inv['id'])['chat_available']
        assert cid not in [p['id'] for p in call(e,'/searches/'+snap['id'])['items']]
        page.reload();nav(page,'Обзор');expect(page.get_by_text('Ваш уровень подтверждён, но профиль скрыт.',exact=False)).to_be_visible()
        checks.append('Q4_hidden_overview_revoked_chat_snapshot_PDF')
        for width in [360,390,768,1365]:
            hr.set_viewport_size({'width':width,'height':900})
            nav(hr,'Моя компания');nav(hr,'Приглашения')
            assert hr.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
            if width<850:
                hr.get_by_role('button',name=re.compile('^Все разделы')).click()
                expect(hr.locator('nav')).to_be_visible()
                hr.screenshot(path=str(Path(a.out).parent/f'mobile-{width}.png'),full_page=True)
                hr.get_by_role('button',name=re.compile('^Свернуть меню')).click()
        checks.append('mobile_no_horizontal_overflow')
        # Historical stored attempt: no rewrite, visible rounding policy note.
        seed='historical-final-'+run
        qs=bank.generate('data','Middle',seed,version='2.0.0')
        answers={q['id']:q['answer'] for q in qs}
        with Session(engine) as db:
            db.add(Attempt(user_id=accounts[3]['id'],specialization='data',grade='Middle',seed=seed,version='2.0.0',variant_hash=bank.fingerprint(qs),questions=qs,answers=answers,result=bank.grade_answers(qs,answers,version='2.0.0'),status='completed',created_at=datetime.now(timezone.utc)-timedelta(days=10),expires_at=datetime.now(timezone.utc)-timedelta(days=10)+timedelta(minutes=30)))
            db.commit()
        new_page.reload();nav(new_page,'Подтверждение навыков')
        new_page.get_by_role('button',name='Посмотреть',exact=True).click()
        expect(new_page.get_by_text('Историческая попытка:',exact=False)).to_be_visible()
        expect(new_page.get_by_text('Задание 8 из 8',exact=False)).to_be_visible()
        new_page.screenshot(path=str(Path(a.out).parent/'historical-attempt.png'),full_page=True)
        checks.append('historical_2_0_count_and_explicit_rounding_note')
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
assert not errors,errors
report=dict(status='pass',checked_at=datetime.now(timezone.utc).isoformat(),base_url=a.base_url,checks=checks,page_errors=errors,
            scope='Live HTTPS API and Chromium; 4 newly bootstrapped fictional accounts, review logins read-only; no SMTP or real-person testing; own smoke candidate hidden, own plan closed.')
Path(a.out).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))

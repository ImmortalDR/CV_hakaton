"""Browser history regression against built UI + real API + isolated PostgreSQL.
Run: npm run build --prefix apps/web
     .venv/bin/python scripts/run_local.py .venv/bin/python tests/browser_navigation.py
No production data changes or external mail. Fixture database is removed on exit.
"""
import json
import os
import secrets
import subprocess
import threading
import time
from pathlib import Path
from uuid import uuid4

import uvicorn
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from playwright.sync_api import sync_playwright, expect
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from fsp.main import create_app
from fsp.seed import seed
from fsp.models import Attempt, Consent, Profile

out = Path('audit/current/navigation')
out.mkdir(parents=True, exist_ok=True)
name = 'fsp_navigation_' + secrets.token_hex(4)
base = os.environ['DATABASE_URL'].rsplit('/', 1)[0]
admin = create_engine(base + '/postgres', isolation_level='AUTOCOMMIT')
with admin.connect() as db:
    db.execute(text('CREATE DATABASE ' + name))
os.environ.update(DATABASE_URL=base + '/' + name, COOKIE_SECURE='false',
                  SMTP_HOST='', SMTP_USER='', SMTP_PASSWORD='', PUBLIC_URL='http://127.0.0.1:18084')
subprocess.run(['.venv/bin/alembic', '-c', 'apps/api/alembic.ini', 'upgrade', 'head'], check=True)
app = create_app(demo=True, rate_limit=False)
with Session(app.state.engine) as db:
    seed(db)
    db.commit()

class SPA(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or path.startswith('api/'):
                raise
            return await super().get_response('index.html', scope)

app.mount('/', SPA(directory='apps/web/dist', html=True))
server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=18084, access_log=False, log_level='warning'))
thread = threading.Thread(target=server.run, daemon=True)
thread.start()
checks, errors = [], []

def checked(message):
    checks.append(message)
    print('PASS ' + message, flush=True)

try:
    for _ in range(100):
        if server.started:
            break
        time.sleep(.1)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        def context(mobile=False):
            ctx = browser.new_context(base_url=os.environ['PUBLIC_URL'], locale='ru-RU',
                viewport={'width': 390 if mobile else 1365, 'height': 844 if mobile else 1000},
                extra_http_headers={'X-Requested-With': 'fsp-web'})
            ctx.on('page', lambda p: p.on('pageerror', lambda e: errors.append(str(e))))
            return ctx
        def call(ctx, path, data=None, method=None):
            response = ctx.request.fetch('/api' + path, method=method or ('GET' if data is None else 'POST'), data=data)
            assert response.ok, (path, response.status, response.text())
            return response.json()
        def at(page, path):
            expect(page).to_have_url(os.environ['PUBLIC_URL'] + path)
        def nav(page, label):
            page.locator('nav').get_by_role('button', name=label, exact=True).click()
        def back(page):
            page.evaluate('history.back()')
        def forward(page):
            page.evaluate('history.forward()')

        c = context(); page = c.new_page(); page.goto('/invitations')
        at(page, '/login?next=%2Finvitations')
        page.get_by_role('button', name='Регистрация', exact=True).click()
        at(page, '/register?next=%2Finvitations')
        back(page); at(page, '/login?next=%2Finvitations')
        forward(page); expect(page.get_by_label('Повторите пароль', exact=True)).to_be_visible()
        page.reload(); expect(page.get_by_role('heading', name='Создать аккаунт')).to_be_visible()
        page.get_by_role('button', name='Вход', exact=True).click()
        page.get_by_role('button', name='Забыли пароль?', exact=True).click()
        at(page, '/forgot-password?next=%2Finvitations')
        back(page); expect(page.get_by_role('heading', name='Добро пожаловать')).to_be_visible()
        page.get_by_role('button', name='Я кандидат', exact=True).click()
        at(page, '/invitations'); expect(page.locator('nav')).to_be_visible()
        checked('auth modes, refresh, protected deep link resumes after login')

        candidate_sections = [('Обзор','overview'),('Мой профиль','profile'),('Подтверждение навыков','assessment'),
                              ('Приглашения','invitations'),('Задания от компаний','tasks'),('Достижения ФСП','fsp')]
        for label, path in candidate_sections:
            nav(page, label); at(page, '/' + path)
            expect(page.locator('nav button.active')).to_contain_text(label)
        for label, path in reversed(candidate_sections[:-1]):
            back(page); at(page, '/' + path); expect(page.locator('nav button.active')).to_contain_text(label)
        for label, path in candidate_sections[1:]:
            forward(page); at(page, '/' + path); expect(page.locator('nav button.active')).to_contain_text(label)
        page.reload(); at(page, '/fsp'); expect(page.get_by_role('heading', name='Достижения ФСП', exact=True)).to_be_visible()
        page.goto('/company'); at(page, '/overview')
        page.goto('/does-not-exist'); at(page, '/overview')
        checked('all candidate sections back/forward, refresh, unknown and wrong-role routes')

        nav(page, 'Подтверждение навыков')
        page.get_by_role('button', name='Начать тест', exact=True).click()
        expect(page.get_by_label('Ответ на задание 1', exact=True)).to_be_visible()
        attempt = call(c, '/me/attempts')[0]
        test_url = '/assessment?attempt=' + attempt['id']; at(page, test_url)
        c.route('**/api/me/attempts/*/answers', lambda route: route.abort())
        page.get_by_label('Ответ на задание 1', exact=True).fill('12345')
        expect(page.get_by_role('alert')).to_contain_text('Не удалось сохранить')
        dialogs = []
        def dismiss(dialog):
            dialogs.append(dialog.message); dialog.dismiss()
        page.on('dialog', dismiss)
        back(page)
        page.wait_for_function('location.search.includes("attempt=")')
        page.wait_for_timeout(150)
        at(page, test_url); expect(page.get_by_label('Ответ на задание 1', exact=True)).to_have_value('12345')
        nav(page, 'Обзор'); at(page, test_url)
        page.evaluate('history.go(-2)'); page.wait_for_timeout(200); at(page, test_url)
        assert len(dialogs) == 3, dialogs
        page.remove_listener('dialog', dismiss)
        page.once('dialog', lambda d: d.accept()); back(page); at(page, '/assessment')
        forward(page); at(page, test_url)
        expect(page.get_by_label('Ответ на задание 1', exact=True)).to_have_value('12345')
        page.once('dialog', lambda d: d.accept()); nav(page, 'Обзор'); at(page, '/overview')
        back(page); at(page, test_url)
        page.once('dialog', lambda d: d.dismiss()); forward(page)
        page.wait_for_timeout(200); at(page, test_url)
        page.once('dialog', lambda d: d.accept()); forward(page); at(page, '/overview')
        back(page); at(page, test_url)
        c.unroute('**/api/me/attempts/*/answers')
        page.get_by_role('button', name='Повторить сохранение').click()
        expect(page.get_by_text('Ответы сохранены', exact=True)).to_be_visible()
        page.reload(); at(page, test_url)
        expect(page.get_by_label('Ответ на задание 1', exact=True)).to_have_value('12345')
        checked('unsaved assessment: cancel browser/menu leave, accept, forward, recovery, reload')
        with Session(app.state.engine) as db:
            questions = db.get(Attempt, attempt['id']).questions
        for index, question in enumerate(questions):
            page.get_by_label(f'Ответ на задание {index+1}', exact=True).fill(str(question['answer']))
        page.get_by_role('button', name='Завершить и узнать результат').click()
        expect(page.get_by_role('heading', name='Уровень подтверждён', exact=True)).to_be_visible()
        page.get_by_role('button', name='К выбору уровня').click(); at(page, '/assessment')
        back(page); at(page, test_url)
        expect(page.get_by_role('heading', name='Уровень подтверждён', exact=True)).to_be_visible()
        page.reload(); expect(page.get_by_role('heading', name='Уровень подтверждён', exact=True)).to_be_visible()
        assert len(call(c, '/me/attempts')) == 1
        checked('completed result deep link/back/reload, no attempt resubmission')

        e = context(); hr = e.new_page(); hr.goto('/'); hr.get_by_role('button', name='Я работодатель', exact=True).click()
        at(hr, '/overview')
        employer_sections = [('Подбор кандидатов','search'),('Приглашения','invitations'),('Задания от компаний','tasks'),('Моя компания','company')]
        for label, path in employer_sections:
            nav(hr, label); at(hr, '/' + path)
        for label, path in reversed(employer_sections[:-1]):
            back(hr); at(hr, '/' + path); expect(hr.locator('nav button.active')).to_contain_text(label)
        hr.reload(); at(hr, '/search')
        hr.get_by_role('button', name='По потребности', exact=True).click(); at(hr, '/search?mode=need')
        hr.get_by_role('button', name='Сформировать подборку', exact=True).click()
        expect(hr).to_have_url(__import__('re').compile(r'/search\?mode=need&snapshot='))
        snap_url = hr.url.removeprefix(os.environ['PUBLIC_URL'])
        expect(hr.locator('.candidate-card').first).to_be_visible()
        back(hr); at(hr, '/search?mode=need')
        forward(hr); at(hr, snap_url)
        expect(hr.get_by_text('Сохранённая подборка на', exact=False)).to_be_visible()
        hr.reload(); expect(hr.get_by_text('Сохранённая подборка на', exact=False)).to_be_visible()
        assert len(call(e, '/searches')) == 1
        hr.get_by_role('button', name='Банк кандидатов', exact=True).click(); at(hr, '/search')
        hr.get_by_label('Подтверждённый уровень', exact=True).select_option('Junior')
        hr.get_by_role('button', name='Применить фильтры', exact=True).click(); at(hr, '/search?grade=Junior')
        back(hr); at(hr, '/search'); expect(hr.get_by_label('Подтверждённый уровень', exact=True)).to_have_value('')
        forward(hr); at(hr, '/search?grade=Junior'); expect(hr.get_by_label('Подтверждённый уровень', exact=True)).to_have_value('Junior')
        expect(hr.locator('.candidate-card').first).to_be_visible()
        hr.evaluate('scrollTo(0, 800)'); hr.wait_for_timeout(150)
        scroll = hr.evaluate('scrollY')
        nav(hr, 'Моя компания'); at(hr, '/company')
        back(hr); at(hr, '/search?grade=Junior')
        hr.wait_for_function('(y) => Math.abs(scrollY-y)<5', arg=scroll)
        hr.reload(); expect(hr.locator('.candidate-card').first).to_be_visible()
        hr.wait_for_function('(y) => Math.abs(scrollY-y)<5', arg=scroll)
        checked('scroll position restored after Back and page reload')
        hr.get_by_role('button', name='Пригласить', exact=True).first.click()
        expect(hr.get_by_role('dialog')).to_be_visible()
        modal_url = hr.url.removeprefix(os.environ['PUBLIC_URL'])
        hr.get_by_label('Предложение и задачи', exact=True).fill('Изменённое предложение для проверки защиты')
        hr.once('dialog', lambda d: d.dismiss()); back(hr)
        hr.wait_for_timeout(200); at(hr, modal_url); expect(hr.get_by_role('dialog')).to_be_visible()
        hr.once('dialog', lambda d: d.accept())
        back(hr); at(hr, '/search?grade=Junior'); expect(hr.get_by_role('dialog')).not_to_be_visible()
        forward(hr); at(hr, modal_url); expect(hr.get_by_role('dialog')).to_be_visible()
        hr.reload(); expect(hr.get_by_role('dialog')).to_be_visible()
        assert not call(e, '/invitations')
        checked('all employer sections, saved search, bank filters, invite modal, no repeated POST')

        own = call(c, '/me/profile')
        with Session(app.state.engine) as db:
            profile = db.get(Profile, own['id']); profile.published = True
            db.scalar(select(Consent).where(Consent.user_id == profile.user_id)).publication = True
            db.commit()
        invite = call(e, '/invitations', dict(candidate_id=own['id'], request_id=str(uuid4()), description='Navigation test invitation', salary_min=100000, salary_max=150000, currency='RUB'))
        call(c, '/invitations/' + invite['id'], {'status': 'accepted'}, 'PATCH')
        hr.goto('/search')
        hr.get_by_label('Номер кандидата', exact=True).fill(own['candidate_code'].lower())
        hr.get_by_role('button', name='Применить фильтры', exact=True).click()
        expect(hr).to_have_url(os.environ['PUBLIC_URL'] + '/search?candidate_code=' + own['candidate_code'])
        expect(hr.locator('.candidate-card')).to_have_count(1)
        expect(hr.locator('.candidate-card')).to_contain_text('Кандидат №' + own['candidate_code'])
        expect(hr.locator('.candidate-card h3')).to_have_text(own['display_name'])
        hr.reload(); expect(hr.locator('.candidate-card')).to_have_count(1)
        expect(hr.get_by_label('Номер кандидата', exact=True)).to_have_value(own['candidate_code'])
        hr.get_by_role('button', name='Сбросить фильтры', exact=True).click(); at(hr, '/search')
        expect(hr.get_by_label('Номер кандидата', exact=True)).to_have_value('')
        back(hr); expect(hr.locator('.candidate-card')).to_have_count(1)
        expect(hr.locator('.candidate-card')).to_contain_text(own['candidate_code'])
        checked('candidate code search after consent: visible alongside name, refresh, reset and Back')
        hr.goto('/invitations'); hr.get_by_role('button', name='Открыть диалог', exact=True).click()
        chat_url = '/invitations?chat=' + invite['id']; at(hr, chat_url)
        hr.get_by_label('Сообщение', exact=True).fill('Проверка навигации')
        hr.get_by_role('button', name='Отправить', exact=True).click()
        expect(hr.get_by_text('Проверка навигации', exact=True)).to_be_visible()
        back(hr); at(hr, '/invitations'); expect(hr.get_by_label('Сообщение', exact=True)).not_to_be_visible()
        forward(hr); at(hr, chat_url); expect(hr.get_by_text('Проверка навигации', exact=True)).to_be_visible()
        hr.reload(); expect(hr.get_by_text('Проверка навигации', exact=True)).to_be_visible()
        assert len(call(e, '/invitations/' + invite['id'] + '/messages')) == 1
        checked('chat open/back/forward/reload, message sent exactly once')

        hr.get_by_role('button', name='Выйти', exact=True).click(); at(hr, '/login')
        back(hr); expect(hr.get_by_role('heading', name='Добро пожаловать')).to_be_visible()
        expect(hr.locator('.account')).not_to_be_visible()
        assert e.request.get('/api/auth/me').status == 401
        checked('logout followed by Back does not reopen private workspace')
        mail = context(); email_page = mail.new_page(); email_page.goto('/login')
        registration = call(mail, '/auth/register', {'email': 'navigation-mail@example.org', 'password': 'Synthetic-navigation-7529', 'role': 'candidate', 'processing': True})
        token = registration['demo_verification_url'].split('#verify=')[1]
        email_page.evaluate('(token) => { location.hash = "verify=" + token; }', token)
        expect(email_page.get_by_text('Почта подтверждена. Войдите в кабинет.', exact=True)).to_be_visible()
        assert token not in email_page.url
        email_page.get_by_role('button', name='Регистрация', exact=True).click()
        back(email_page); at(email_page, '/login')
        email_page.goto('/reset-password')
        expect(email_page.get_by_text('Ссылка для смены пароля отсутствует.', exact=False)).to_be_visible()
        checked('email hash after mount, consumed token removed, reset without token explained')
        mobile = context(mobile=True); mp = mobile.new_page(); mp.goto('/tasks')
        mp.get_by_role('button', name='Я кандидат', exact=True).click(); at(mp, '/tasks')
        mp.locator('.mobile-menu').click(); nav(mp, 'Мой профиль'); at(mp, '/profile')
        back(mp); at(mp, '/tasks'); expect(mp.locator('.mobile-menu')).to_contain_text('Задания от компаний')
        forward(mp); at(mp, '/profile'); expect(mp.locator('.mobile-menu')).to_contain_text('Мой профиль')
        assert mp.evaluate('document.documentElement.scrollWidth <= innerWidth')
        checked('mobile menu/back/forward, no horizontal overflow')
        assert not errors, errors
        browser.close()
finally:
    server.should_exit = True; thread.join(timeout=10); app.state.engine.dispose()
    with admin.connect() as db:
        db.execute(text('DROP DATABASE ' + name + ' WITH (FORCE)'))
    admin.dispose()
    (out / 'result.json').write_text(json.dumps({'checks': checks, 'page_errors': errors, 'scope': 'isolated database, synthetic seed, no external mail'}, ensure_ascii=False, indent=2) + '\n')

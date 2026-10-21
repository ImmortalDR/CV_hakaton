"""Isolated PostgreSQL + built web + real API, in-memory SMTP, Chromium.
No external mail; no changes to production accounts. Run via run_local.py.
"""
import json, os, re, secrets, subprocess, threading, time
from pathlib import Path
from sqlalchemy import create_engine, text
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import sync_playwright, expect
import uvicorn
from fsp import main

out=Path('docs/delivery/evidence/human_followup_2026-10-21');out.mkdir(parents=True,exist_ok=True)
name='fsp_authui_'+secrets.token_hex(4)
base=os.environ['DATABASE_URL'].rsplit('/',1)[0]
admin=create_engine(base+'/postgres',isolation_level='AUTOCOMMIT')
with admin.connect() as db:db.execute(text('CREATE DATABASE '+name))
admin.dispose()
os.environ.update(DATABASE_URL=base+'/'+name,COOKIE_SECURE='false',SMTP_HOST='smtp.test.invalid',SMTP_USER='',SMTP_PASSWORD='',PUBLIC_URL='http://127.0.0.1:18083')
subprocess.run(['.venv/bin/alembic','-c','apps/api/alembic.ini','upgrade','head'],check=True)
sent=[];reject=[False]
class SMTP:
 def __init__(self,*a,**kw):pass
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def ehlo(self):pass
 def starttls(self,**kw):pass
 def send_message(self,msg):
  if reject[0]:raise main.smtplib.SMTPException('simulated SMTP failure')
  sent.append(msg)
main.smtplib.SMTP=SMTP
app=main.create_app(demo=True,rate_limit=False)
app.mount('/',StaticFiles(directory='apps/web/dist',html=True))
server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=18083,access_log=False,log_level='warning'))
thread=threading.Thread(target=server.run,daemon=True);thread.start()
for _ in range(80):
 if server.started:break
 time.sleep(.1)
checks=[];errors=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch()
  ctx=browser.new_context(base_url=os.environ['PUBLIC_URL'],locale='ru-RU',viewport={'width':1365,'height':1000},extra_http_headers={'X-Requested-With':'fsp-web'})
  page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('/');page.get_by_role('button',name='Регистрация',exact=True).click()
  page.get_by_role('button',name='Создать аккаунт',exact=True).click()
  expect(page.get_by_role('alert')).to_contain_text('запрос ещё не отправлен');assert not sent
  page.get_by_label('Электронная почта',exact=True).fill('auth-browser@example.org')
  password='Browser-test-89472';new='Changed-browser-4839'
  page.get_by_label('Пароль',exact=True).fill(password)
  page.get_by_label('Повторите пароль',exact=True).fill('Mismatch-89472')
  page.get_by_role('checkbox').check();page.get_by_role('button',name='Создать аккаунт',exact=True).click()
  expect(page.get_by_text('Пароли не совпадают.',exact=False)).to_be_visible();assert not sent
  page.screenshot(path=str(out/'registration-validation.png'),full_page=True)
  page.get_by_role('button',name='Показать пароль',exact=True).click();expect(page.get_by_label('Пароль',exact=True)).to_have_attribute('type','text')
  page.get_by_role('button',name='Скрыть пароль',exact=True).click();page.get_by_label('Повторите пароль',exact=True).fill(password)
  checks+=['required_fields_and_mismatch_block_requests','password_visibility_toggle']
  reject[0]=True;page.get_by_role('button',name='Создать аккаунт',exact=True).click()
  expect(page.get_by_role('alert')).to_contain_text('Не удалось отправить письмо')
  expect(page.get_by_label('Пароль',exact=True)).to_have_value(password)
  checks.append('smtp_failure_visible_fields_preserved')
  reject[0]=False;page.get_by_role('button',name='Создать аккаунт',exact=True).click()
  expect(page.get_by_role('heading',name='Подтвердите почту',exact=True)).to_be_visible()
  assert len(sent)==1
  page.screenshot(path=str(out/'registration-sent.png'),full_page=True)
  verify=sent[-1].get_content().split('#verify=')[1].strip()
  page.goto('/#verify='+verify);expect(page.get_by_text('Почта подтверждена. Войдите в кабинет.',exact=True)).to_be_visible()
  assert '#verify=' not in page.url
  page.get_by_label('Электронная почта',exact=True).fill('auth-browser@example.org');page.get_by_label('Пароль',exact=True).fill(password);page.get_by_role('button',name='Войти в кабинет',exact=True).click()
  expect(page.locator('nav')).to_be_visible();expect(page.locator('.orb')).to_contain_text('к проверке')
  checks+=['registration_email_link_verify_login','unconfirmed_grade_not_claimed']
  other=browser.new_context(base_url=os.environ['PUBLIC_URL'],locale='ru-RU',viewport={'width':390,'height':844})
  mobile=other.new_page();mobile.on('pageerror',lambda e:errors.append(str(e)));mobile.goto('/')
  mobile.screenshot(path=str(out/'mobile-landing.png'),full_page=True)
  assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
  mobile.get_by_role('button',name='Забыли пароль?',exact=True).click();mobile.get_by_label('Электронная почта',exact=True).fill('auth-browser@example.org')
  mobile.get_by_role('button',name='Отправить ссылку для смены пароля',exact=True).click()
  expect(mobile.get_by_role('status')).to_contain_text('Если адрес зарегистрирован')
  reset=sent[-1].get_content().split('#reset=')[1].strip()
  mobile.goto('/#reset='+reset);expect(mobile.get_by_role('heading',name='Задайте новый пароль')).to_be_visible()
  assert '#reset=' not in mobile.url
  mobile.get_by_label('Новый пароль',exact=True).fill(new);mobile.get_by_label('Повторите пароль',exact=True).fill(new)
  mobile.screenshot(path=str(out/'mobile-password-reset.png'),full_page=True)
  mobile.get_by_role('button',name='Сохранить новый пароль',exact=True).click();expect(mobile.get_by_role('status')).to_contain_text('Пароль изменён')
  assert ctx.request.get('/api/auth/me').status==401
  mobile.get_by_label('Электронная почта',exact=True).fill('auth-browser@example.org');mobile.get_by_label('Пароль',exact=True).fill(new);mobile.get_by_role('button',name='Войти в кабинет',exact=True).click()
  expect(mobile.locator('.mobile-menu')).to_be_visible();assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
  mobile.screenshot(path=str(out/'mobile-candidate.png'),full_page=True)
  checks+=['mobile_recovery_email_reset_login','old_session_revoked','mobile_no_horizontal_overflow']
  assert not errors,errors
  browser.close()
finally:
 server.should_exit=True;thread.join(timeout=10)
 (out/'auth-browser.json').write_text(json.dumps({'checks':checks,'page_errors':errors,'database':name,'mail':'in-memory SMTP, no real delivery'},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'checks':checks,'page_errors':errors},ensure_ascii=False))

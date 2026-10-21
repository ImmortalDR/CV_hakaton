"""Explicit real-mail acceptance for a controlled Gmail mailbox.

Run only when its owner authorized sending/reading these verification messages.
Uses plus-addresses, reads only matching messages with BODY.PEEK, never deletes
mail, publishes no mailbox address, password, cookie or verification token.
Credentials come from environment; output contains aggregate checks only.
"""
import argparse
import email
import imaplib
import json
import os
import re
import secrets
import ssl
import time
from datetime import datetime, timezone
from email import policy
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base-url',required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--recipient',required=True,help='Controlled Gmail mailbox owned by the authorizing user')
    args=parser.parse_args();base=args.base_url.rstrip('/')
    if urlsplit(base).scheme!='https':parser.error('Real-mail check requires HTTPS')
    if args.recipient.lower()!=os.environ.get('SMTP_USER','').lower():parser.error('Recipient must equal the configured controlled SMTP mailbox')
    if args.recipient.split('@')[-1].lower()!='gmail.com':parser.error('This acceptance script implements Gmail plus-addressing and IMAP only')
    args.out.mkdir(parents=True,exist_ok=True)
    report={'status':'running','checked_at':datetime.now(timezone.utc).isoformat(),'base_url':base,
            'scope':'Real SMTP registration and IMAP receipt in one authorized Gmail mailbox; UI verification/login for both roles',
            'roles':[],'messages_sent':0,'messages_received':0,'secrets_recorded':False}
    phase='imap_login'
    try:
        with imaplib.IMAP4_SSL('imap.gmail.com',993,ssl_context=ssl.create_default_context(),timeout=15) as mailbox, sync_playwright() as pw:
            mailbox.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
            mailbox.select('INBOX',readonly=True)
            browser=pw.chromium.launch()
            for role in ['candidate','employer']:
                phase='registration_'+role
                local,domain=args.recipient.split('@');recipient=local+'+fsp-check-'+secrets.token_hex(6)+'@'+domain
                password='Fsp-test-'+secrets.token_urlsafe(18)
                context=browser.new_context(locale='ru-RU');page=context.new_page();errors=[]
                page.on('pageerror',lambda error:errors.append(type(error).__name__))
                page.goto(base)
                page.get_by_role('button',name='Регистрация',exact=True).click()
                page.get_by_label('Я на платформе как').select_option(role)
                page.get_by_label('Электронная почта',exact=True).fill(recipient)
                page.get_by_label('Пароль',exact=True).fill(password)
                page.get_by_label('Повторите пароль',exact=True).fill(password)
                page.get_by_role('checkbox').check()
                with page.expect_response(lambda r:r.url.endswith('/api/auth/register') and r.request.method=='POST',timeout=30000) as response:
                    page.get_by_role('button',name='Создать аккаунт',exact=True).click()
                r=response.value
                assert r.status==201,'Registration failed (HTTP '+str(r.status)+')'
                data=r.json();assert data['delivery']=='smtp' and not data.get('demo_verification_url')
                report['messages_sent']+=1
                assert page.locator('.demo-letter').count()==0
                headers={'X-Requested-With':'fsp-web'}
                credentials={'email':recipient,'password':password}
                assert context.request.post(base+'/api/auth/login',data=credentials,headers=headers).status==403
                phase='receive_'+role;start=time.monotonic();token=None;authentication={}
                while time.monotonic()-start<120:
                    mailbox.noop()
                    status,matches=mailbox.uid('search',None,'HEADER','To','"'+recipient+'"')
                    assert status=='OK','Mailbox search failed'
                    for uid in matches[0].split()[-5:]:
                        status,parts=mailbox.uid('fetch',uid,'(BODY.PEEK[])')
                        if status!='OK':continue
                        raw=next((part[1] for part in parts if isinstance(part,tuple)),None)
                        if not raw:continue
                        message=email.message_from_bytes(raw,policy=policy.default)
                        if recipient.lower() not in str(message.get('To','')).lower():continue
                        body=message.get_body(preferencelist=('plain',))
                        content=body.get_content() if body else message.get_payload(decode=True).decode('utf-8')
                        found=re.search(re.escape(base)+r'/#verify=([A-Za-z0-9_-]+)',content)
                        if found:
                            token=found.group(1)
                            auth=' '.join(message.get_all('Authentication-Results',[])).lower()
                            authentication={k:('pass' if k+'=pass' in auth else 'not_observed') for k in ['spf','dkim','dmarc']}
                            break
                    if token:break
                    time.sleep(3)
                assert token,'Verification message not found in INBOX within 120 seconds'
                report['messages_received']+=1
                phase='verify_'+role
                page.goto(base+'/#verify='+token)
                expect(page.get_by_text('Почта подтверждена. Войдите в кабинет.',exact=True)).to_be_visible(timeout=15000)
                phase='token_removed_'+role
                assert '#verify=' not in page.url
                phase='single_use_'+role
                assert context.request.post(base+'/api/auth/verify',data={'token':token},headers=headers).status==400
                phase='login_'+role
                page.get_by_role('button',name='Вход',exact=True).click()
                page.get_by_label('Электронная почта',exact=True).fill(recipient)
                page.get_by_label('Пароль',exact=True).fill(password)
                page.get_by_role('button',name='Войти в кабинет',exact=True).click()
                page.locator('.sidebar').wait_for()
                me=context.request.get(base+'/api/auth/me').json();assert me['role']==role
                assert not errors,'Browser errors'
                context.request.post(base+'/api/auth/logout',headers=headers)
                report['roles'].append({'role':role,'status':'pass','receipt_and_login_seconds':round(time.monotonic()-start,2),
                    'checks':['smtp_response_without_token','no_demo_letter','unverified_login_denied','imap_receipt','ui_link_verification','url_token_removed','single_use_link','ui_login','role_correct','no_js_errors'],
                    'authentication_headers':authentication})
                context.close()
            browser.close()
        report['status']='pass'
    except Exception as error:
        report.update(status='fail',failed_phase=phase,error_type=type(error).__name__)
        # Exception text/trace may contain credentials, addresses or URL fragments.
    finally:
        (args.out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False))
    raise SystemExit(0 if report['status']=='pass' else 1)


if __name__=='__main__':main()

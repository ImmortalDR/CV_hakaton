"""One authorized real registration to the owner's controlled Gmail plus alias.
Uses existing SMTP app credentials also for read-only IMAP of ONLY this message.
Never prints credentials, verification links, message bodies, or mailbox contents.
"""
import email
import imaplib
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx

out=Path('docs/delivery/evidence/final_2026-10-21/mail.json')
result=dict(checked_at=datetime.now(timezone.utc).isoformat(),status='not_run',mailbox='owner_controlled_gmail',checks=[])
try:
    user=os.environ.get('SMTP_USER','')
    controlled=os.environ.get('CONTROLLED_MAILBOX','').strip().lower()
    if not controlled or user.lower()!=controlled or not controlled.endswith('@gmail.com'):
        raise RuntimeError('controlled_mailbox_not_configured')
    password=os.environ.get('SMTP_PASSWORD','')
    if not password: raise RuntimeError('smtp_password_missing')
    # Check mailbox access before triggering a real registration email.
    with imaplib.IMAP4_SSL('imap.gmail.com',timeout=15) as mailbox:
        mailbox.login(user,password)
        mailbox.select('INBOX',readonly=True)
        alias=user.split('@')[0]+'+fsp-final-'+secrets.token_hex(4)+'@gmail.com'
        credentials=dict(email=alias,password=secrets.token_urlsafe(25))
        with httpx.Client(base_url=os.environ['PUBLIC_URL'].rstrip('/'),headers={'X-Requested-With':'fsp-web'},timeout=20) as c:
            response=c.post('/api/auth/register',json=credentials|dict(role='candidate',processing=True))
            assert response.status_code==201, f'registration_http_{response.status_code}'
            assert response.json()['delivery']=='smtp' and response.json()['demo_verification_url'] is None
            result['checks'].append('registration_smtp_no_token_in_response')
            assert c.post('/api/auth/login',json=credentials).status_code==403
            token=None
            for _ in range(12):
                mailbox.noop()
                status, ids=mailbox.search(None,'TO',f'"{alias}"')
                for ident in ids[0].split():
                    status, parts=mailbox.fetch(ident,'(BODY.PEEK[])')
                    raw=next(x[1] for x in parts if isinstance(x,tuple))
                    message=email.message_from_bytes(raw)
                    for part in message.walk():
                        if part.get_content_type()=='text/plain':
                            body=part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
                            match=re.search(r'#verify=([A-Za-z0-9_-]+)',body)
                            if match: token=match[1]
                if token: break
                time.sleep(3)
            assert token, 'mail_not_received_in_36_seconds'
            result['checks'].append('real_message_received_in_inbox')
            assert c.post('/api/auth/verify',json={'token':token}).status_code==200
            assert c.post('/api/auth/verify',json={'token':token}).status_code==400
            assert c.post('/api/auth/login',json=credentials).status_code==200
            assert c.post('/api/auth/register',json=credentials|dict(role='candidate',processing=True)).status_code==409
            profile=c.get('/api/me/profile').json()
            assert not profile['published']
            result['checks']+=['verify','token_single_use','login','duplicate_registration_409','new_profile_private']
            result['status']='pass'
except Exception as exc:
    result['status']='blocked_or_failed'
    # Exception strings from network/auth can contain secrets. Only expose type.
    result['error_type']=type(exc).__name__
finally:
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))

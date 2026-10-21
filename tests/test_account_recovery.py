"""Recovery authorization, mail failures, replay and expiry; no real emails."""
from datetime import timedelta
import smtplib
from sqlalchemy import select
from fastapi.testclient import TestClient
from fsp import main
from fsp.models import PasswordReset, Verification, now
from conftest import account, HEADERS

def token(mail,kind): return mail.get_content().split('#'+kind+'=')[1].split()[0]

def test_reset_single_use_invalidates_sessions_and_old_password(app,monkeypatch):
    client,_=account(app)
    sent=[]
    monkeypatch.setattr(main.smtplib,'SMTP',FakeSMTP(sent))
    monkeypatch.setenv('SMTP_HOST','smtp.test.invalid')
    anon=TestClient(app,headers=HEADERS)
    r=anon.post('/api/auth/forgot-password',json={'email':'person@example.org'})
    assert r.status_code==200 and len(sent)==1
    t=token(sent[0],'reset');assert t not in r.text
    unknown=anon.post('/api/auth/forgot-password',json={'email':'unknown@example.org'})
    assert unknown.json()==r.json() and len(sent)==1
    assert anon.post('/api/auth/forgot-password',json={'email':'person@example.org'}).status_code==200
    assert len(sent)==1  # durable per-account cooldown
    assert anon.post('/api/auth/reset-password',json={'token':t,'password':'short'}).status_code==422
    assert anon.post('/api/auth/verify',json={'token':t}).status_code==400
    new='Updated-password-923'
    assert anon.post('/api/auth/reset-password',json={'token':t,'password':new}).status_code==200
    assert client.get('/api/auth/me').status_code==401
    assert anon.post('/api/auth/reset-password',json={'token':t,'password':'Other-password-984'}).status_code==400
    assert anon.post('/api/auth/login',json={'email':'person@example.org','password':'Only-test-password-43'}).status_code==401
    assert anon.post('/api/auth/login',json={'email':'person@example.org','password':new}).status_code==200

def FakeSMTP(sent,fail=False):
    class SMTP:
        def __init__(self,*a,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def ehlo(self):pass
        def starttls(self,**kw):pass
        def send_message(self,msg):
            if fail:raise smtplib.SMTPException('private-details')
            sent.append(msg)
    return SMTP

def test_reset_expiry_failure_rollback_and_verification(app,monkeypatch):
    client,verify=account(app,verify=False)
    sent=[];monkeypatch.setenv('SMTP_HOST','smtp.test.invalid')
    monkeypatch.setattr(main.smtplib,'SMTP',FakeSMTP(sent,fail=True))
    r=client.post('/api/auth/forgot-password',json={'email':'person@example.org'})
    assert r.status_code==503 and 'private-details' not in r.text
    with app.state.factory() as db:assert db.scalar(select(PasswordReset)) is None
    monkeypatch.setattr(main.smtplib,'SMTP',FakeSMTP(sent))
    assert client.post('/api/auth/forgot-password',json={'email':'person@example.org'}).status_code==200
    old=token(sent[-1],'reset')
    with app.state.factory() as db:
        db.scalar(select(PasswordReset)).expires_at=now()-timedelta(seconds=1);db.commit()
    assert client.post('/api/auth/reset-password',json={'token':old,'password':'New-password-876'}).status_code==400
    client.post('/api/auth/forgot-password',json={'email':'person@example.org'})
    assert client.post('/api/auth/reset-password',json={'token':token(sent[-1],'reset'),'password':'New-password-876'}).status_code==200
    assert client.post('/api/auth/verify',json={'token':verify}).status_code==400
    assert client.post('/api/auth/login',json={'email':'person@example.org','password':'New-password-876'}).status_code==200

def test_resend_expired_verification_without_changing_password(app,monkeypatch):
    client,old=account(app,verify=False)
    with app.state.factory() as db:
        db.scalar(select(Verification)).expires_at=now()-timedelta(seconds=1);db.commit()
    sent=[];monkeypatch.setenv('SMTP_HOST','smtp.test.invalid');monkeypatch.setattr(main.smtplib,'SMTP',FakeSMTP(sent))
    r=client.post('/api/auth/resend-verification',json={'email':'person@example.org'})
    assert r.status_code==200 and len(sent)==1
    t=token(sent[-1],'verify');assert t not in r.text
    assert client.post('/api/auth/reset-password',json={'token':t,'password':'New-password-876'}).status_code==400
    client.post('/api/auth/resend-verification',json={'email':'person@example.org'});assert len(sent)==1
    assert client.post('/api/auth/verify',json={'token':t}).status_code==200
    assert client.post('/api/auth/login',json={'email':'person@example.org','password':'Only-test-password-43'}).status_code==200
    client.post('/api/auth/resend-verification',json={'email':'person@example.org'});assert len(sent)==1

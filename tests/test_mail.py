"""SMTP security and transaction tests. No external delivery in pytest."""
import smtplib
import ssl

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from fsp import main
from fsp.models import User, Verification, Profile, Company, CompanyMember, Consent
from conftest import HEADERS


def configure(monkeypatch):
    for k,v in {'SMTP_HOST':'smtp.test.invalid','SMTP_PORT':'587','SMTP_TLS':'true',
                'SMTP_USER':'sender@example.org','SMTP_PASSWORD':'synthetic-password',
                'SMTP_FROM':'sender@example.org','PUBLIC_URL':'https://test.example.org'}.items():
        monkeypatch.setenv(k,v)


def register(client):
    return client.post('/api/auth/register',json={'email':'controlled@example.org',
        'password':'Synthetic-password-325','role':'candidate','processing':True})


@pytest.mark.parametrize('demo',[True,False])
def test_real_smtp_hides_token_and_verification_is_single_use(app,monkeypatch,demo):
    configure(monkeypatch);sent=[];calls=[]
    class SMTP:
        def __init__(self,host,port,timeout):assert (host,port,timeout)==('smtp.test.invalid',587,10)
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def ehlo(self):calls.append('ehlo')
        def starttls(self,context):
            assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
            calls.append('tls')
        def login(self,user,password):assert user=='sender@example.org';calls.append('login')
        def send_message(self,msg):sent.append(msg);calls.append('send');return {}
    monkeypatch.setattr(main.smtplib,'SMTP',SMTP)
    live=main.create_app(app.state.engine.url.render_as_string(hide_password=False),demo=demo,rate_limit=False)
    try:
        with TestClient(live,headers=HEADERS) as client:
            r=register(client);assert r.status_code==201
            assert r.json()['delivery']=='smtp' and r.json()['demo_verification_url'] is None
            assert calls==['ehlo','tls','ehlo','login','send']
            assert sent[0]['Date'] and sent[0]['Message-ID']
            body=sent[0].get_content();token=body.split('#verify=')[1].strip()
            assert token not in r.text and body.count('https://test.example.org/#verify=')==1
            credentials={'email':'controlled@example.org','password':'Synthetic-password-325'}
            assert client.post('/api/auth/login',json=credentials).status_code==403
            assert client.post('/api/auth/verify',json={'token':token}).status_code==200
            assert client.post('/api/auth/verify',json={'token':token}).status_code==400
            assert client.post('/api/auth/login',json=credentials).status_code==200
    finally:live.state.engine.dispose()


@pytest.mark.parametrize('failure',['tls','auth','send','timeout','bad_port','missing_password'])
def test_delivery_failure_returns_503_and_rolls_back_all_rows(app,monkeypatch,failure):
    configure(monkeypatch)
    class SMTP:
        def __init__(self,*args,**kwargs):
            if failure=='timeout':raise TimeoutError('private-details')
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def ehlo(self):pass
        def starttls(self,context):
            if failure=='tls':raise ssl.SSLCertVerificationError('private-details')
        def login(self,*args):
            if failure=='auth':raise smtplib.SMTPAuthenticationError(535,b'private-details')
        def send_message(self,*args):raise smtplib.SMTPRecipientsRefused({'controlled@example.org':(550,b'private-details')})
    if failure=='bad_port':monkeypatch.setenv('SMTP_PORT','wrong')
    if failure=='missing_password':monkeypatch.delenv('SMTP_PASSWORD')
    monkeypatch.setattr(main.smtplib,'SMTP',SMTP)
    with TestClient(app,headers=HEADERS) as client:
        r=register(client);assert r.status_code==503
        assert 'private-details' not in r.text and 'synthetic-password' not in r.text
    with app.state.factory() as db:
        for model in [User,Verification,Profile,Company,CompanyMember,Consent]:
            assert db.scalar(select(func.count()).select_from(model))==0

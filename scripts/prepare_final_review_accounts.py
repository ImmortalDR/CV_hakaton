"""Create isolated fictional review fixtures without resetting any user history.
Passwords are saved only in an owner-only local file, never printed or committed.
"""
import json
import os
import secrets
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import httpx
from fsp.main import PASSWORDS
from fsp.models import User, Profile, Company, CompanyMember, Consent, Attempt
from evaluation.oracles import solve

engine=create_engine(os.environ['DATABASE_URL'])
suffix=secrets.token_hex(3)
accounts=[]
specs=[('fresh_python','candidate','python'),('fresh_sql_middle','candidate','data'),('ready_candidate','candidate','python'),('inviting_company','employer',None),('other_company','employer',None)]
with Session(engine) as db:
 for label,role,spec in specs:
  password=secrets.token_urlsafe(20)
  user=User(email=f'final-review-{label}-{suffix}@example.org',password_hash=PASSWORDS.hash(password),role=role,verified=True,demo=True)
  db.add(user);db.flush();db.add(Consent(user_id=user.id,processing=True,publication=role=='candidate'))
  if spec:
   db.add(Profile(user_id=user.id,name='Финальная проверка · '+label,phone='+7 000 000-00-00',published=True,processing=True,specialization=spec,skills=['python'] if spec=='python' else ['sql']))
  else:
   company=Company(name='Финальная проверка · '+label,description='Вымышленная компания для ручной проверки сервиса.',sector='ИТ',contact='review@example.org')
   db.add(company);db.flush();db.add(CompanyMember(user_id=user.id,company_id=company.id))
  accounts.append(dict(scenario=label,email=user.email,password=password,id=user.id))
 db.commit()
root=Path('/root/.local/share/fsp-demo-accounts');root.mkdir(parents=True,exist_ok=True,mode=0o700)
private=root/f'final-review-20261021-{suffix}.json'
private.write_text(json.dumps(accounts,ensure_ascii=False,indent=2)+'\n');private.chmod(0o600)
checks=[]
for account in accounts:
 with httpx.Client(base_url=os.environ['PUBLIC_URL'],headers={'X-Requested-With':'fsp-web'},timeout=20) as client:
  response=client.post('/api/auth/login',json={k:account[k] for k in ['email','password']});assert response.status_code==200
  if account['scenario']=='ready_candidate':
   a=client.post('/api/me/attempts',json={'grade':'Junior'});assert a.status_code==201
   with Session(engine) as db: qs=db.get(Attempt,a.json()['id']).questions
   result=client.post('/api/me/attempts/'+a.json()['id']+'/submit',json={'answers':{q['id']:str(solve(q)) for q in qs}})
   assert result.status_code==200 and result.json()['result']['passed']
  if account['scenario'].startswith('fresh_'):
   assert client.get('/api/me/attempts').json()==[]
  checks.append(dict(scenario=account['scenario'],email=account['email'],login='pass',state='synthetic_confirmed_Junior' if account['scenario']=='ready_candidate' else 'unused_no_attempts' if account['scenario'].startswith('fresh') else 'new_company_no_grants'))
report=dict(status='pass',checked_at=datetime.now(timezone.utc).isoformat(),credentials_location=str(private),accounts=checks,scope='Demo bootstrap, not email verification or human pilot. No history reset. Each login checked.')
Path('docs/delivery/evidence/final_2026-10-21/review-accounts.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='pass',accounts=len(accounts),credentials_location=str(private))))

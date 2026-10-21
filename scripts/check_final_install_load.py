"""Fresh private DB, migrations, additive seed, bounded local read load.
No production requests or schema/data changes; random test DB retained for audit.
"""
import json
import os
import secrets
import subprocess
import time
from pathlib import Path
from sqlalchemy import create_engine, text

out=Path('docs/delivery/evidence/final_2026-10-21')
name='fsp_finalcheck_'+secrets.token_hex(4)
base=os.environ['DATABASE_URL'].rsplit('/',1)[0]
admin=create_engine(base+'/postgres',isolation_level='AUTOCOMMIT')
with admin.connect() as c: c.execute(text('CREATE DATABASE '+name))
admin.dispose()
env=dict(os.environ,DATABASE_URL=base+'/'+name,DEMO_MODE='true',COOKIE_SECURE='false',SMTP_HOST='',SMTP_USER='',SMTP_PASSWORD='',LOAD_BASE_URL='http://127.0.0.1:18081',LOAD_OUTPUT=str(out/'load.json'))
for args in [['.venv/bin/alembic','-c','apps/api/alembic.ini','upgrade','head'],['.venv/bin/python','-m','fsp.seed'],['.venv/bin/python','-m','fsp.seed'],['.venv/bin/alembic','-c','apps/api/alembic.ini','check']]:
 subprocess.run(args,env=env,check=True)
engine=create_engine(env['DATABASE_URL'])
with engine.connect() as db:
 count=db.scalar(text('select count(*) from users'))
 migration=db.scalar(text('select version_num from alembic_version'))
assert count==15
(out/'install.json').write_text(json.dumps(dict(status='pass',database=name,initial_database='new_empty',migration=migration,users_after_two_seeds=count,schema_drift=False,limitations='Fresh PostgreSQL DB; built runtime images reuse cached pinned dependencies; no offline archive install.'),indent=2)+'\n')
# Duplicate the seeded synthetic profiles, attempts and evidence for a 130-profile bank.
from sqlalchemy.orm import Session
from fsp.models import User, Profile, Attempt, Evidence
from sqlalchemy import select
from uuid import uuid4
with Session(engine) as db:
 originals=list(db.scalars(select(Profile).where(Profile.published.is_(True))))
 for copy in range(9):
  for original in originals:
   u=User(email=f'load-copy-{copy}-{original.user_id}@example.org',password_hash='unused-no-login',role='candidate',verified=True,demo=True)
   db.add(u);db.flush()
   fields={col.name:getattr(original,col.name) for col in Profile.__table__.columns if col.name not in ['user_id','verified_attempt_id','fsp_identity']}
   p=Profile(user_id=u.id,**fields)
   if original.verified_attempt_id:
    old=db.get(Attempt,original.verified_attempt_id)
    vals={col.name:getattr(old,col.name) for col in Attempt.__table__.columns if col.name not in ['id','user_id','variant_hash']}
    a=Attempt(user_id=u.id,variant_hash=secrets.token_hex(32),**vals);db.add(a);db.flush();p.verified_attempt_id=a.id
    for old_e in db.scalars(select(Evidence).where(Evidence.attempt_id==old.id)):
     vals={col.name:getattr(old_e,col.name) for col in Evidence.__table__.columns if col.name not in ['id','attempt_id','user_id']}
     db.add(Evidence(attempt_id=a.id,user_id=u.id,**vals))
   db.add(p)
 db.commit()
engine.dispose()
log=(out/'load-server.log').open('w')
server=subprocess.Popen(['.venv/bin/uvicorn','fsp.main:app_factory','--factory','--host','127.0.0.1','--port','18081','--no-access-log'],env=env,stdout=log,stderr=log)
try:
 import httpx
 for _ in range(40):
  try:
   if httpx.get(env['LOAD_BASE_URL']+'/api/health',timeout=1).status_code==200: break
  except httpx.HTTPError: pass
  time.sleep(.25)
 else: raise RuntimeError('isolated server not ready')
 subprocess.run(['.venv/bin/python','tests/load_probe.py'],env=env,check=True)
finally:
 server.terminate();server.wait(timeout=15);log.close()
print(json.dumps(dict(install='pass',load='completed',database=name)))

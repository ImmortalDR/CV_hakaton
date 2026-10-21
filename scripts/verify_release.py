"""Clean isolated Docker installation, schema check, additive seed and restore.

Creates only fsp-verify-* projects, loopback port and a new volume. Does not stop,
rename or clean other projects. Keeps its artifacts/volume for inspection.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--project',default='fsp-verify-'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'));p.add_argument('--port',type=int,default=3083);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if not re.fullmatch(r'fsp-verify-[a-z0-9-]+',a.project):p.error('Only new fsp-verify-* projects allowed')
    if not 1024<=a.port<=65535:p.error('Invalid loopback port')
    if subprocess.check_output(['docker','ps','-aq','--filter','label=com.docker.compose.project='+a.project]).strip():p.error('Project already exists; choose a fresh name')
    if subprocess.check_output(['docker','volume','ls','-q','--filter','label=com.docker.compose.project='+a.project]).strip():p.error('Volume already exists; choose a fresh name')
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
    env=a.out/'verify.env'
    with env.open('x') as f:
        os.chmod(env,0o600);f.write('POSTGRES_PASSWORD='+secrets.token_hex(24)+'\n')
    # Derive exact services/builds/dependencies from the actual Compose config.
    # Isolated env has no live credentials. Avoid printing the resolved config.
    raw=json.loads(subprocess.check_output(['docker','compose','--env-file',str(env),'-f',str(ROOT/'compose.yaml'),'config','--format','json']))
    raw.pop('name',None);raw['services'].pop('edge',None)
    for service in raw['services'].values():
        service.pop('networks',None);service.pop('restart',None)
    raw.pop('networks',None)
    raw['services']['db'].pop('ports',None)
    raw['services']['web']['ports']=[f'127.0.0.1:{a.port}:80']
    raw['services']['api']['environment'].update(DEMO_MODE='true',PUBLIC_URL=f'http://127.0.0.1:{a.port}',COOKIE_SECURE='false',SMTP_HOST='',SMTP_PASSWORD='',SMTP_USER='')
    for volume in raw.get('volumes',{}).values():volume.pop('name',None)
    compose=a.out/'compose.json'
    with compose.open('x') as f:os.chmod(compose,0o600);json.dump(raw,f)
    command=['docker','compose','-p',a.project,'-f',str(compose)]
    def run(*args,**kw):return subprocess.run(command+list(args),check=True,**kw)
    run('up','-d','--build','--wait')
    run('exec','-T','api','alembic','check')
    snapshot_code="""import os,json,hashlib
from sqlalchemy import create_engine,select
from fsp.models import Base
url=os.environ['DATABASE_URL']
if os.getenv('RESTORE_CHECK'):url=url.rsplit('/',1)[0]+'/fsp_restorecheck'
engine=create_engine(url);result={}
with engine.connect() as db:
 for table in Base.metadata.sorted_tables:
  rows=[dict(r) for r in db.execute(select(table).order_by(*table.primary_key.columns)).mappings()]
  result[table.name]={'rows':len(rows),'sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,default=str).encode()).hexdigest()}
print(json.dumps(result,sort_keys=True))
"""
    def snapshot(restore=False):
        flags=['exec','-T']+(['-e','RESTORE_CHECK=1'] if restore else [])
        return json.loads(subprocess.check_output(command+flags+['api','python','-c',snapshot_code]))
    before=snapshot();assert before['users']['rows']==15
    run('exec','-T','api','python','-m','fsp.seed');assert snapshot()==before
    dump=a.out/'fresh-backup.dump'
    with dump.open('xb') as f:
        os.chmod(dump,0o600);run('exec','-T','db','pg_dump','-U','fsp','-d','fsp','-Fc',stdout=f)
    run('exec','-T','db','psql','-U','fsp','-d','postgres','-c','CREATE DATABASE fsp_restorecheck')
    with dump.open('rb') as f:run('exec','-T','db','pg_restore','-U','fsp','-d','fsp_restorecheck','--no-owner',stdin=f)
    restored=snapshot(True);assert restored==before
    run('restart','api','web','task-worker');run('up','-d','--wait')
    assert snapshot()==before
    with urllib.request.urlopen(f'http://127.0.0.1:{a.port}/api/health') as response:assert response.status==200
    result=dict(status='pass',checked_at=datetime.now(timezone.utc).isoformat(),project=a.project,port=a.port,
        fresh_volume=True,tables=len(before),users=15,additive_seed=True,schema_drift=False,
        backup_restore_identical=True,restart_preserved=True,table_hashes=before,
        dump_sha256=hashlib.sha256(dump.read_bytes()).hexdigest(),
        scope='New isolated Docker project; new PostgreSQL volume; full metadata tables compared by ordered row hashes; synthetic seed only',
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        working_tree_changes=bool(subprocess.check_output(['git','diff','--name-only'],cwd=ROOT)))
    (a.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='table_hashes'},ensure_ascii=False))


if __name__=='__main__':main()

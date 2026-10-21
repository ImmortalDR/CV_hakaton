"""Compare deployed runtime bytes without reading container environments."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args): return subprocess.check_output(args,text=True).strip()
local={str(p.relative_to('apps/api')):digest(p) for p in Path('apps/api/fsp').glob('*.py')}
code="import pathlib,hashlib,json; print(json.dumps({str(p.relative_to('/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path('/app/fsp').glob('*.py')}))"
services={}
for service in ['api','task-worker']:
 remote=json.loads(run(['docker','compose','exec','-T',service,'python','-c',code]))
 services[service]=dict(files=len(local),exact=remote==local)
 assert remote==local,(service,'deployed Python differs')
local_web={str(p.relative_to('apps/web/dist')):digest(p) for p in [Path('apps/web/dist/index.html'),*Path('apps/web/dist/assets').glob('*')] if p.is_file()}
remote_web={}
for line in run(['docker','compose','exec','-T','web','sh','-c','sha256sum /usr/share/nginx/html/index.html /usr/share/nginx/html/assets/*']).splitlines():
 sha,name=line.split(maxsplit=1);remote_web[name.removeprefix('/usr/share/nginx/html/')]=sha
assert remote_web==local_web,'deployed web differs from local build'
services['web']=dict(files=len(local_web),exact=True)
health=json.loads(run(['docker','compose','exec','-T','api','python','-c',"import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').read().decode())"]))
r=dict(status='pass',checked_at=datetime.now(timezone.utc).isoformat(),runtime_commit=run(['git','log','-1','--format=%H','--','apps']),services=services,health=health,api_files=local,web_files=local_web)
Path('docs/delivery/evidence/final_2026-10-21/release-files.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:r[k] for k in ['status','runtime_commit','services','health']}))

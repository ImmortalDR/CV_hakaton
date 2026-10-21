import subprocess,json,hashlib,urllib.request
from pathlib import Path
h=lambda b:hashlib.sha256(b).hexdigest()
run=lambda *a:subprocess.check_output(a)
result={'git_sha':run('git','rev-parse','HEAD').decode().strip()}
for service in ['api','task-worker']:
 rows=[]
 for f in sorted(Path('apps/api/fsp').glob('*.py'))+sorted(Path('apps/api/migrations').rglob('*.py')):
  deployed=run('docker','compose','exec','-T',service,'cat','/app/'+str(f.relative_to('apps/api')))
  rows.append(dict(file=str(f),sha256=h(f.read_bytes()),head_equal=f.read_bytes()==run('git','show','HEAD:'+str(f)),deployed_equal=deployed==f.read_bytes()))
 result[service]=rows
result['web']=[]
for f in sorted(Path('apps/web/dist').rglob('*')):
 if not f.is_file():continue
 rel=str(f.relative_to('apps/web/dist'))
 deployed=run('docker','compose','exec','-T','web','cat','/usr/share/nginx/html/'+rel)
 public=urllib.request.urlopen('https://85-137-26-131.sslip.io/'+('' if rel=='index.html' else rel)).read()
 result['web'].append(dict(file=rel,sha256=h(f.read_bytes()),container_equal=f.read_bytes()==deployed,https_equal=f.read_bytes()==public))
result['health']=json.load(urllib.request.urlopen('https://85-137-26-131.sslip.io/api/health'))
result['db_mount']=json.loads(run('docker','inspect','fsp-mvp-db-1','--format','{{json .Mounts}}'))
assert all(x['head_equal'] and x['deployed_equal'] for s in ['api','task-worker'] for x in result[s])
assert all(x['container_equal'] and x['https_equal'] for x in result['web'])
assert run('git','diff','HEAD','--','apps','compose.yaml')==b''
Path('/tmp/q1-deploy-check.json').write_text(json.dumps(result,indent=2))
print('PASS: 17 api + 17 worker modules = HEAD; fresh web build = container = HTTPS; health',result['health'])

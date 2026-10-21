"""One command for non-mail platform acceptance; records actual commands/results."""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--base-url',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--skip-backend',action='store_true');p.add_argument('--read-only',action='store_true',help='Use existing demo accounts; no registrations or mail');a=p.parse_args()
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,COOKIE_SECURE='false',SMTP_HOST='',SMTP_USER='',SMTP_PASSWORD='');steps=[]
    commands=[] if a.skip_backend else [('backend',[sys.executable,str(ROOT/'scripts/run_local.py'),sys.executable,'-m','pytest','-q','tests'])]
    commands += [('numerals',['node','apps/web/tests/formatting.test.mjs']),
        ('requirements',[sys.executable,'tests/browser_requirements.py','--base-url',a.base_url,'--expect-core-rule','--output',str(a.out/'requirements')]),
        ('employer_tasks',[sys.executable,'tests/browser_tasks.py','--base-url',a.base_url,'--out',str(a.out/'tasks')])]
    if a.read_only:
        commands=[c for c in commands if c[0] in ('backend','numerals')]+[('live_smoke',[sys.executable,'tests/browser_live_smoke.py','--base-url',a.base_url,'--out',str(a.out/'live-smoke')])]
    for name,command in commands:
        started=time.monotonic()
        with (a.out/(name+'.log')).open('w') as f:
            result=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        steps.append(dict(name=name,command=command,status='pass' if result.returncode==0 else 'fail',exit_code=result.returncode,seconds=round(time.monotonic()-started,2)))
        if result.returncode:break
    try:
        with urllib.request.urlopen(a.base_url+'/api/openapi.json') as r:live=json.load(r)
        stored=json.loads((ROOT/'docs/delivery/openapi.json').read_text())
        steps.append(dict(name='published_openapi',status='pass' if live==stored else 'fail'))
    except Exception as error:steps.append(dict(name='published_openapi',status='fail',error_type=type(error).__name__))
    report=dict(status='pass' if all(s['status']=='pass' for s in steps) else 'fail',checked_at=datetime.now(timezone.utc).isoformat(),base_url=a.base_url,
        scope=('Read-only smoke; no registration, mail or business mutations' if a.read_only else 'Non-mail engineering acceptance; does not certify real email or human/model validity'),steps=steps,
        backend='not_run' if a.skip_backend else next((s['status'] for s in steps if s['name']=='backend'),'not_run'),
        external_gates={'real_email':'not_run_separate_explicit_check','human_pilot':'not_run_requires_people','independent_ranking_labels':'not_run_requires_labels'})
    (a.out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
    raise SystemExit(0 if report['status']=='pass' else 1)


if __name__=='__main__':main()

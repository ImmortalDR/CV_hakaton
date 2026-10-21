"""Public HTTPS smoke check without registrations, emails or business mutations."""
import argparse,json,urllib.request
from pathlib import Path
from datetime import datetime,timezone
from playwright.sync_api import sync_playwright,expect
parser=argparse.ArgumentParser();parser.add_argument('--base-url',required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
root=Path(__file__).resolve().parents[1];out=args.out;out.mkdir(parents=True,exist_ok=True)
base=args.base_url.rstrip('/')
with urllib.request.urlopen(base+'/api/openapi.json') as r:live=json.load(r)
assert live==json.loads((root/'docs/delivery/openapi.json').read_text())
errors=[]
with sync_playwright() as p:
 b=p.chromium.launch();context=b.new_context(viewport={'width':1440,'height':1000},locale='ru-RU');page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
 for role in ['candidate','employer']:
  response=context.request.post(base+'/api/auth/demo',data={'account':role},headers={'X-Requested-With':'fsp-web'});assert response.status==200
  page.goto(base);page.locator('.sidebar').wait_for()
  page.get_by_role('button',name='Задания от компаний',exact=False).first.click()
  expect(page.get_by_role('heading',name='Задания от компаний')).to_be_visible()
  assert context.request.get(base+'/api/tasks').status==200
  page.screenshot(path=str(out/(role+'.png')),full_page=True)
  for width in [360,390,768]:
   page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
  page.screenshot(path=str(out/(role+'-mobile.png')),full_page=True)
  page.set_viewport_size({'width':1440,'height':1000})
  context.request.post(base+'/api/auth/logout',headers={'X-Requested-With':'fsp-web'})
 b.close()
assert not errors
result=dict(status='pass',checked_at=datetime.now(timezone.utc).isoformat(),base_url=base,checks=['valid_tls','openapi_exact','demo_login_both_roles','tasks_ui_both_roles','tasks_api','mobile_360_390_768','no_js_errors'],scope='Existing demo accounts, read-only business operations. No registration, SMTP send, profile or task mutations.',page_errors=errors)
(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))

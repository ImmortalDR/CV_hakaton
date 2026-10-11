"""Regression: verification hash arriving after mount; isolated simulated mail only."""
import argparse,json,secrets
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

parser=argparse.ArgumentParser();parser.add_argument('--base-url',required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
args.out.mkdir(parents=True,exist_ok=True);base=args.base_url.rstrip('/')
with sync_playwright() as pw:
    browser=pw.chromium.launch();context=browser.new_context();page=context.new_page();page.goto(base)
    # Only the isolated test host is allowed; never create a mailbox recipient publicly.
    assert base.startswith('http://127.0.0.1:'),'Isolated loopback demo only'
    response=context.request.post(base+'/api/auth/register',headers={'X-Requested-With':'fsp-web'},data={
        'email':'navigation-'+secrets.token_hex(6)+'@example.org','password':'Synthetic-test-'+secrets.token_hex(8),'role':'candidate','processing':True})
    assert response.status==201
    data=response.json();assert data['delivery']=='simulated'
    token=data['demo_verification_url'].split('#verify=')[1]
    page.evaluate('(token)=>{location.hash="verify="+token}',token)
    expect(page.get_by_text('Почта подтверждена. Войдите в кабинет.',exact=True)).to_be_visible()
    assert not page.url.endswith(token)
    page.evaluate('(token)=>{location.hash="verify="+token}',token)
    expect(page.get_by_text('Ссылка недействительна или уже использована',exact=True)).to_be_visible()
    assert '#verify=' not in page.url
    browser.close()
report={'status':'pass','checks':['same_document_hash_verifies','token_removed','reused_hash_rejected'],'scope':'Isolated synthetic account and simulated delivery; no external mail'}
(args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

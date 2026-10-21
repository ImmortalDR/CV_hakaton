"""Visual PDF artifacts on fictional isolated test data, no production mutation."""
import os
import sys
import secrets
from pathlib import Path
sys.path.insert(0,'tests')
os.environ['SMTP_HOST']=''
os.environ['COOKIE_SECURE']='false'
from fsp.main import create_app
from conftest import confirmed, employer
from test_api import invite
import pymupdf

app=create_app(os.environ['DATABASE_URL'].rsplit('/',1)[0]+'/fsp_test',demo=True,rate_limit=False)
run=secrets.token_hex(4)
c,cid=confirmed(app,'pdf-'+run+'@example.org');e=employer(app,'pdf-hr-'+run+'@example.org')
out=Path('docs/delivery/evidence/final_2026-10-21')
closed=e.get('/api/profiles/'+cid+'/pdf');assert closed.status_code==200
inv,_=invite(e,cid);assert c.patch('/api/invitations/'+inv.json()['id'],json={'status':'accepted'}).status_code==200
opened=e.get('/api/profiles/'+cid+'/pdf');assert opened.status_code==200
for name,response in [('closed-contacts',closed),('open-contacts',opened)]:
 (out/(name+'.pdf')).write_bytes(response.content)
 with pymupdf.open(stream=response.content,filetype='pdf') as doc:
  text=''.join(page.get_text() for page in doc)
  assert ('pdf-'+run+'@example.org' in text)==(name=='open-contacts')
  doc[0].get_pixmap(matrix=pymupdf.Matrix(1,1)).save(str(out/(name+'.png')))
app.state.engine.dispose()
print('Two PDF artifacts rendered; isolated fsp_test, fictional data; consent isolation verified')

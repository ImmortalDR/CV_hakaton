"""Run the complete browser walkthrough against an isolated PostgreSQL database."""
import os
import sys
import secrets
import subprocess
import threading
import time

import uvicorn
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from fsp.main import create_app
from fsp.seed import seed

name = 'fsp_jury_' + secrets.token_hex(4)
base = os.environ['DATABASE_URL'].rsplit('/', 1)[0]
admin = create_engine(base + '/postgres', isolation_level='AUTOCOMMIT')
with admin.connect() as db:
    db.execute(text('CREATE DATABASE ' + name))
os.environ.update(DATABASE_URL=base + '/' + name, COOKIE_SECURE='false',
    SMTP_HOST='', SMTP_USER='', SMTP_PASSWORD='', PUBLIC_URL='http://127.0.0.1:18085')
app = None
server = None
try:
    subprocess.run(['.venv/bin/alembic', '-c', 'apps/api/alembic.ini', 'upgrade', 'head'], check=True)
    app = create_app(demo=True, rate_limit=False)
    with Session(app.state.engine) as db:
        seed(db)
        db.commit()
    class SPA(StaticFiles):
        async def get_response(self, path, scope):
            try:
                return await super().get_response(path, scope)
            except HTTPException as exc:
                if exc.status_code != 404 or path.startswith('api/'):
                    raise
                return await super().get_response('index.html', scope)
    app.mount('/', SPA(directory='apps/web/dist', html=True))
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=18085, access_log=False, log_level='warning'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(.1)
    if '--sessions-only' not in sys.argv:
        subprocess.run(['.venv/bin/python','tests/browser_jury.py','--base-url',os.environ['PUBLIC_URL'],
            '--runs','2','--out','audit/current/jury-local'], check=True)
    subprocess.run(['.venv/bin/python','tests/browser_sessions.py','--base-url',os.environ['PUBLIC_URL'],
        '--out','audit/current/sessions-local'], check=True)
finally:
    if server:
        server.should_exit = True
        thread.join(timeout=10)
    if app:
        app.state.engine.dispose()
    with admin.connect() as db:
        db.execute(text('DROP DATABASE ' + name + ' WITH (FORCE)'))
    admin.dispose()

"""Browser history regression against built UI + real API + isolated PostgreSQL.
Run: npm run build --prefix apps/web
     .venv/bin/python scripts/run_local.py .venv/bin/python tests/browser_navigation.py
No production data changes or external mail. Fixture database is removed on exit.
"""
import json
import os
import secrets
import subprocess
import threading
import time
from pathlib import Path
from uuid import uuid4

import pymupdf
import uvicorn
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from playwright.sync_api import sync_playwright, expect
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from fsp.main import create_app
from fsp.seed import seed
from fsp.models import Attempt, Consent, Profile

out = Path('audit/current/demo-idle')
out.mkdir(parents=True, exist_ok=True)
name = 'fsp_idle_' + secrets.token_hex(4)
base = os.environ['DATABASE_URL'].rsplit('/', 1)[0]
admin = create_engine(base + '/postgres', isolation_level='AUTOCOMMIT')
with admin.connect() as db:
    db.execute(text('CREATE DATABASE ' + name))
os.environ.update(DATABASE_URL=base + '/' + name, COOKIE_SECURE='false',
                  SMTP_HOST='', SMTP_USER='', SMTP_PASSWORD='', PUBLIC_URL='http://127.0.0.1:18086')
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
server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=18086, access_log=False, log_level='warning'))
thread = threading.Thread(target=server.run, daemon=True)
thread.start()
checks = []
from datetime import timedelta
from fsp import models as M, demo_idle
try:
    for _ in range(100):
        if server.started: break
        time.sleep(.1)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(base_url=os.environ['PUBLIC_URL'])
        page = ctx.new_page()
        page.goto('/login')
        page.get_by_role('button', name='Я кандидат', exact=True).click()
        expect(page.locator('.shell')).to_be_visible()
        expect(page.locator('.notice')).to_contain_text('после часа без действий')
        page.wait_for_timeout(16000)
        with app.state.factory.begin() as db:
            state = db.get(M.DemoWorkspace, 'shared')
            old = M.now() - timedelta(minutes=2)
            state.last_activity = old
            baseline_count = len(state.baseline['attempts'])
        page.evaluate("window.dispatchEvent(new Event('focus'))")
        page.wait_for_timeout(1000)
        with app.state.factory() as db:
            assert db.get(M.DemoWorkspace, 'shared').last_activity == old
        page.mouse.wheel(0, 400)
        page.wait_for_timeout(500)
        with app.state.factory() as db:
            assert db.get(M.DemoWorkspace, 'shared').last_activity > old
        checks.append('background session polling does not extend idle clock; real scrolling does')
        for generation in (1, 2):
            page.goto('/assessment')
            expect(page.get_by_text('История тестирования', exact=True)).to_be_visible()
            with app.state.factory.begin() as db:
                state = db.get(M.DemoWorkspace, 'shared')
                state.last_activity = M.now() - timedelta(hours=2)
            assert demo_idle.reset_due(app.state.factory)
            # Existing tab still holds the old version. A stale write must be rejected,
            # then normal session synchronization must remount the clean account.
            page.evaluate("window.dispatchEvent(new Event('fsp:session-changed'))")
            expect(page).to_have_url(os.environ['PUBLIC_URL'] + '/overview')
            page.goto('/assessment')
            expect(page.get_by_text('История тестирования', exact=True)).to_be_visible()
            expect(page.get_by_text('Не удалось загрузить историю.', exact=False)).to_have_count(0)
            with app.state.factory() as db:
                state = db.get(M.DemoWorkspace, 'shared')
                assert state.generation == generation
                assert len(list(db.scalars(select(M.Attempt).where(M.Attempt.user_id == state.baseline['candidate'])))) == baseline_count
            checks.append(f'reset {generation}: retained browser session recovers and initial test history survives')
        page.screenshot(path=str(out/'restored-history.png'), full_page=True)
        browser.close()
        print(json.dumps(checks, ensure_ascii=False), flush=True)
finally:
    server.should_exit = True; thread.join(timeout=10); app.state.engine.dispose()
    with admin.connect() as db:
        db.execute(text('DROP DATABASE ' + name + ' WITH (FORCE)'))
    admin.dispose()
    (out / 'result.json').write_text(json.dumps({'checks': checks, 'scope': 'isolated database, synthetic seed, no external mail'}, ensure_ascii=False, indent=2) + '\n')

"""Verify migrations and additive seed against a separately created empty DB."""

import json
import os
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from fsp.models import Base, User


url = os.environ["DATABASE_URL"].rsplit("/", 1)[0] + "/fsp_installcheck"
engine = create_engine(url)
env = dict(os.environ, DATABASE_URL=url, DEMO_MODE="true")
subprocess.run(
    [".venv/bin/alembic", "-c", "apps/api/alembic.ini", "upgrade", "head"],
    env=env,
    check=True,
)
subprocess.run([".venv/bin/python", "-m", "fsp.seed"], env=env, check=True)
with Session(engine) as db:
    count1 = db.scalar(select(func.count()).select_from(User))
subprocess.run([".venv/bin/python", "-m", "fsp.seed"], env=env, check=True)
with Session(engine) as db:
    count2 = db.scalar(select(func.count()).select_from(User))
assert count1 == count2 == 15
subprocess.run(
    [".venv/bin/alembic", "-c", "apps/api/alembic.ini", "check"], env=env, check=True
)
result = {
    "status": "pass",
    "database": "fsp_installcheck",
    "migration": "f8a2ba6fc338",
    "tables": len(Base.metadata.tables),
    "users_after_first_seed": count1,
    "users_after_second_seed": count2,
    "schema_drift": False,
    "scope": "Separate empty PostgreSQL DB; existing application DB unchanged",
}
Path("docs/delivery/install-results.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
engine.dispose()
print(json.dumps(result))

"""Check only the named fsp-mvp Compose project, preserving its volume."""

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from fsp.models import Attempt, Invitation, Profile, Snapshot, User


def snapshot():
    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as db:
        rows = {
            model.__tablename__: [
                dict(row) for row in db.execute(select(model.__table__)).mappings()
            ]
            for model in [User, Profile, Attempt, Invitation, Snapshot]
        }
    # Hash complete business rows; never emit passwords, answers or personal fields.
    payload = json.dumps(rows, sort_keys=True, default=str).encode()
    result = {
        "counts": {name: len(values) for name, values in rows.items()},
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    engine.dispose()
    return result


before = snapshot()
subprocess.run(["docker", "compose", "restart"], check=True)
for _ in range(60):
    try:
        if httpx.get("http://127.0.0.1:3080/api/health", timeout=2).status_code == 200:
            break
    except httpx.HTTPError:
        pass
    time.sleep(0.5)
else:
    raise RuntimeError("Demo did not become healthy after restart")
after = snapshot()
assert before == after, "Business data changed after restart"
result = {
    "status": "pass",
    "project": "fsp-mvp",
    "before": before,
    "after": after,
    "volume_removed": False,
}
Path("docs/delivery/restart-results.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(json.dumps(result))

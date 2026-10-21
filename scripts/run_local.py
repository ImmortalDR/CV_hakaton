"""Run a command with local project settings without exposing credentials."""

import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for line in (root / ".env").read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://fsp:"
    + os.environ["POSTGRES_PASSWORD"]
    + "@127.0.0.1:5547/fsp",
)
os.environ["PYTHONPATH"] = str(root / "apps/api") + os.pathsep + str(root)
raise SystemExit(subprocess.call(sys.argv[1:], cwd=root, env=os.environ))

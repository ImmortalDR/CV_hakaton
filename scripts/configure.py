"""Create only missing local settings; never replace existing secrets."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if path.exists():
    print(".env already exists; preserved")
else:
    with path.open("x") as f:
        os.chmod(path, 0o600)
        f.write(
            "POSTGRES_PASSWORD="
            + secrets.token_hex(24)
            + "\nDEMO_MODE=true\nPUBLIC_URL=http://localhost:3080\nBIND_ADDRESS=127.0.0.1\nCOOKIE_SECURE=false\n"
        )
    print("Local .env created; credentials are not printed")

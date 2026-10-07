"""Bounded demo load probe: 30 distinct synthetic authenticated employers."""

import asyncio
import json
import os
import platform
import secrets
import statistics
import time
from datetime import timedelta
from pathlib import Path

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as DBSession

from fsp.main import PASSWORDS, digest
from fsp.models import Company, CompanyMember, Profile, Session, User, now


async def main():
    base = os.getenv("LOAD_BASE_URL", "http://127.0.0.1:3080")
    async with httpx.AsyncClient(base_url=base) as probe:
        assert (await probe.get("/api/health")).json()[
            "demo"
        ], "Only demo environments allowed"
    engine = create_engine(os.environ["DATABASE_URL"])
    tokens = []
    with DBSession(engine) as db:
        company = Company(
            name="Нагрузочный стенд · демо",
            description="Вымышленная компания ограниченного нагрузочного прогона",
            sector="ИТ",
            contact="load@example.org",
        )
        db.add(company)
        db.flush()
        password_hash = PASSWORDS.hash(secrets.token_urlsafe(32))
        for i in range(30):
            u = User(
                email=f"load-{secrets.token_hex(6)}@example.org",
                password_hash=password_hash,
                role="employer",
                verified=True,
                demo=True,
            )
            db.add(u)
            db.flush()
            db.add(CompanyMember(user_id=u.id, company_id=company.id))
            token = secrets.token_urlsafe(32)
            tokens.append(token)
            db.add(
                Session(
                    token_hash=digest(token),
                    user_id=u.id,
                    expires_at=now() + timedelta(minutes=10),
                )
            )
        candidate = db.scalar(
            select(Profile).where(
                Profile.published.is_(True), Profile.processing.is_(True)
            )
        )
        assert candidate is not None
        cid = candidate.user_id
        profiles = len(
            list(
                db.scalars(
                    select(Profile).where(
                        Profile.published.is_(True), Profile.processing.is_(True)
                    )
                )
            )
        )
        db.commit()
    records = []

    async def worker(token):
        async with httpx.AsyncClient(
            base_url=base, cookies={"fsp_session": token}, timeout=60
        ) as client:
            for round in range(3):
                for name, path in [
                    ("bank", "/api/candidates"),
                    ("profile", "/api/candidates/" + cid),
                    ("pdf", "/api/profiles/" + cid + "/pdf"),
                ]:
                    start = time.perf_counter()
                    r = await client.get(path)
                    records.append(
                        {
                            "operation": name,
                            "milliseconds": round_float(
                                (time.perf_counter() - start) * 1000
                            ),
                            "status": r.status_code,
                        }
                    )

    start = time.perf_counter()
    await asyncio.gather(*(worker(t) for t in tokens))
    duration = time.perf_counter() - start

    def summarize(rows):
        values = sorted(r["milliseconds"] for r in rows)
        return {
            "requests": len(rows),
            "errors": sum(r["status"] != 200 for r in rows),
            "median_ms": round_float(statistics.median(values)),
            "p95_ms": values[max(0, int(len(values) * 0.95) - 1)],
            "max_ms": max(values),
        }

    result = {
        "concurrency": 30,
        "distinct_authenticated_users": 30,
        "profiles": profiles,
        "duration_seconds": round_float(duration),
        "throughput_rps": round_float(len(records) / duration),
        "all": summarize(records),
        "by_operation": {
            name: summarize([r for r in records if r["operation"] == name])
            for name in ("bank", "profile", "pdf")
        },
        "environment": {
            "system": platform.platform(),
            "logical_cpus": os.cpu_count(),
            "memory_total_kib": next(
                line.split()[1]
                for line in Path("/proc/meminfo").read_text().splitlines()
                if line.startswith("MemTotal:")
            ),
        },
        "limitations": "270 read requests; 30 synthetic sessions; no login/write load, no long soak, small candidate bank; no claim of production capacity",
    }
    Path("docs/delivery/load-results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    engine.dispose()
    assert result["all"]["errors"] == 0


def round_float(value):
    return round(value, 2)


if __name__ == "__main__":
    asyncio.run(main())

"""Explicit optional import into a dedicated evaluation database, never app tables."""

import os
from pathlib import Path
from urllib.parse import urlsplit, unquote, parse_qs

from .common import read_json, records, sha256
from .validate import validate


def check_dsn(dsn):
    parsed = urlsplit(dsn)
    if (
        parsed.scheme not in ["postgresql", "postgres"]
        or unquote(parsed.path) != "/fsp_dataset_eval"
    ):
        raise ValueError("Only the dedicated database fsp_dataset_eval is allowed")
    if parsed.query or parsed.fragment:
        raise ValueError("DSN query overrides are not allowed")


def import_package(root, apply=False, dsn_env="FSP_DATASET_EVAL_DSN"):
    root = Path(root)
    result = validate(root)
    if result["status"] != "passed":
        raise ValueError("Validation failed")
    manifest = read_json(root / "manifest.json")
    release_id = sha256(root / "manifest.json")
    report = {
        "dry_run": not apply,
        "records": result["records"],
        "release_sha256": release_id,
        "target_schema": "fsp_evaluation",
        "application_tables_touched": False,
    }
    if not apply:
        return report
    dsn = os.environ.get(dsn_env, "")
    check_dsn(dsn)
    import psycopg
    from psycopg.types.json import Jsonb

    # A single transaction makes retry safe; a release digest is immutable.
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            if cur.fetchone()[0] != "fsp_dataset_eval":
                raise ValueError("Unexpected connected database")
            cur.execute("CREATE SCHEMA IF NOT EXISTS fsp_evaluation")
            cur.execute(
                "CREATE TABLE IF NOT EXISTS fsp_evaluation.releases (sha256 text PRIMARY KEY, manifest jsonb NOT NULL)"
            )
            cur.execute(
                "CREATE TABLE IF NOT EXISTS fsp_evaluation.records (release_sha256 text REFERENCES fsp_evaluation.releases(sha256), record_id text, kind text NOT NULL, split text NOT NULL, document jsonb NOT NULL, PRIMARY KEY(release_sha256,record_id))"
            )
            cur.execute(
                "INSERT INTO fsp_evaluation.releases VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (release_id, Jsonb(manifest)),
            )
            for entry in manifest["files"]:
                if entry["records"] is None:
                    continue
                batch = []
                for row in records(root / entry["path"]):
                    batch.append(
                        (
                            release_id,
                            row["record_id"],
                            row["kind"],
                            row["split"],
                            Jsonb(row),
                        )
                    )
                    if len(batch) == 500:
                        cur.executemany(
                            "INSERT INTO fsp_evaluation.records VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                            batch,
                        )
                        batch.clear()
                if batch:
                    cur.executemany(
                        "INSERT INTO fsp_evaluation.records VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        batch,
                    )
    return report

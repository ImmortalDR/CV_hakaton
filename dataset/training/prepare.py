"""Offline, streaming Trudvsem extraction. Never touches the application's DB."""

from __future__ import annotations
import argparse
from collections import Counter
import csv
from datetime import date
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sqlite3
import time

VERSION = "trudvsem-observed-events-v1"
IT_TITLE = re.compile(
    r"программист|разработчик|тестировщик|системн\w*\s+администратор|администратор\s+баз|инженер\w*\s+программ|аналитик\w*\s+данных|data\s+(?:engineer|scientist|analyst)|software|backend|frontend|fullstack|devops|python|java\b",
    re.I,
)
FIELDS = {
    "job": ("title", "requirements_qualifications", "responsibilities"),
    "cv": ("position_name", "skills"),
}
SOURCE_URL = "https://data.rcsi.science/data-catalog/datasets/186/"


def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()


def clean(s):
    s = html.unescape(re.sub(r"<[^>]*>", " ", s or ""))
    s = re.sub(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", " ", s)
    s = re.sub(r"(?:https?://|www\.)\S+", " ", s)
    s = re.sub(r"(?<!\w)\+?\d[\d ()-]{8,}\d(?!\w)", " ", s)
    return " ".join(s.casefold().split())[:16000]


def technology_mentioned(text, term):
    return bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text.casefold()))


def valid_date(s):
    try:
        return date.fromisoformat(s).isoformat()
    except (ValueError, TypeError):
        return ""


def event_date(r):
    # A changed status is observed at modification, never backdated to creation.
    key = "date_modify" if r.get("date_modify") else "date_creation"
    if r.get(key + "_mistake") not in ("", "0", None):
        return ""
    return valid_date(r.get(key))


def csv_rows(path, report):
    before = path.stat()
    sha = hashlib.sha256()
    count = 0

    def lines(f):
        first = True
        for line in f:
            sha.update(line)
            yield line.decode("utf-8-sig" if first else "utf-8")
            first = False

    csv.field_size_limit(50_000_000)
    with path.open("rb") as f:
        reader = csv.reader(lines(f), delimiter=";")
        header = next(reader)
        if len(set(header)) != len(header):
            raise ValueError("Duplicate CSV columns")
        for count, values in enumerate(reader, 1):
            if len(values) != len(header):
                raise ValueError(f"Malformed CSV: {path.name}, record {count}")
            yield count, header, values
            if count % 500000 == 0:
                print(json.dumps({"file": path.name, "rows": count}), flush=True)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f"Input changed: {path.name}")
    report[path.name] = {
        "rows": count,
        "bytes": before.st_size,
        "sha256": sha.hexdigest(),
    }


def stream(path, report):
    for count, header, values in csv_rows(path, report):
        yield count, dict(zip(header, values))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def build(source, out, resume=False):
    os.umask(0o077)
    if resume:
        if not (out / "index.sqlite").is_file() or (out / "scan.json").exists():
            raise ValueError("Resume requires an interrupted, incomplete index")
    else:
        out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    db = sqlite3.connect(out / "index.sqlite")
    db.execute("PRAGMA cache_size=-32000")
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(
        """
    CREATE TABLE IF NOT EXISTS events(eid TEXT, reply TEXT, cv TEXT, person TEXT, job TEXT, org TEXT,
      kind TEXT, day TEXT, published TEXT, rownum INTEGER);
    CREATE TABLE IF NOT EXISTS jobs(id TEXT, org TEXT, day TEXT, text TEXT, is_it INTEGER, rownum INTEGER);
    CREATE TABLE IF NOT EXISTS cvs(id TEXT, person TEXT, day TEXT, text TEXT, rownum INTEGER);
    CREATE TABLE IF NOT EXISTS applications(eid TEXT, reply TEXT, cv TEXT, person TEXT, job TEXT,
      org TEXT, kind TEXT, day TEXT, published TEXT, rownum INTEGER);
    CREATE TABLE IF NOT EXISTS scan_checkpoints(file TEXT PRIMARY KEY, metadata TEXT);
    """
    )
    inputs, counts = {}, {}

    def checkpoint(table, filename, index_sql, extract):
        index_names = re.findall(r"CREATE INDEX (\w+)", index_sql)
        existing = {
            r[0]
            for r in db.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
        completed = all(name in existing for name in index_names)
        if completed:
            print(json.dumps({"resume_stage_check": table}), flush=True)
            saved = db.execute(
                "SELECT metadata FROM scan_checkpoints WHERE file=?", (filename,)
            ).fetchone()
            if saved:
                expected = json.loads(saved[0])
                path = source / filename
                before = path.stat()
                sha = hashlib.sha256()
                with path.open("rb") as f:
                    for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
                        sha.update(block)
                after = path.stat()
                if (
                    (before.st_size, before.st_mtime_ns)
                    != (after.st_size, after.st_mtime_ns)
                    or sha.hexdigest() != expected["sha256"]
                    or before.st_size != expected["bytes"]
                ):
                    raise ValueError(f"Completed stage input changed: {filename}")
                # Identical bytes imply identical record count; no need to parse again.
                inputs[filename] = expected
            else:
                # Recover counts from the interrupted pre-checkpoint implementation.
                for _ in csv_rows(source / filename, inputs):
                    pass
        else:
            # Only derived incomplete tables are rebuilt; raw sources are read-only.
            for name in index_names:
                db.execute(f"DROP INDEX IF EXISTS {name}")
            db.execute(f"DELETE FROM {table}")
            for n, r in stream(source / filename, inputs):
                values = extract(n, r)
                if values is not None:
                    marks = ",".join("?" for _ in values)
                    db.execute(f"INSERT INTO {table} VALUES({marks})", values)
                if n % 50000 == 0:
                    db.commit()
            db.commit()
            db.executescript(index_sql)
        db.execute(
            "INSERT OR REPLACE INTO scan_checkpoints VALUES(?,?)",
            (filename, json.dumps(inputs[filename], sort_keys=True)),
        )
        db.commit()
        write_json(
            out / "scan-progress.json",
            {"inputs": inputs, "last_completed_stage": table},
        )

    def event(n, r, id_column):
        return (
            r[id_column],
            r["id_reply"],
            r["id_cv"],
            r["id_candidate"],
            r["id_vacancy"],
            r["id_hiring_organization"],
            r["response_type"],
            event_date(r),
            valid_date(r["date_last_updated"]),
            n,
        )

    checkpoint(
        "events",
        "responses.csv",
        "CREATE INDEX event_job ON events(job); CREATE INDEX event_eid ON events(eid);",
        lambda n, r: event(n, r, "id_response"),
    )
    counts["response_types_all"] = dict(
        db.execute("SELECT kind,COUNT(*) FROM events GROUP BY kind")
    )
    wanted_jobs = {r[0] for r in db.execute("SELECT DISTINCT job FROM events") if r[0]}
    print(json.dumps({"wanted_job_ids": len(wanted_jobs)}), flush=True)

    def job(n, r):
        if r["identifier"] not in wanted_jobs:
            return None
        return (
            r["identifier"],
            r["id_hiring_organization"],
            valid_date(r["date_last_updated"]),
            clean("\n".join(r[k] for k in FIELDS["job"])),
            int(bool(IT_TITLE.search(r["title"]))),
            n,
        )

    checkpoint("jobs", "vacancies.csv", "CREATE INDEX job_id ON jobs(id, day);", job)
    del wanted_jobs
    it_jobs = {r[0] for r in db.execute("SELECT DISTINCT id FROM jobs WHERE is_it=1")}
    cv_ids = {
        r[0]
        for r in db.execute(
            "SELECT DISTINCT e.cv FROM events e JOIN (SELECT DISTINCT id FROM jobs WHERE is_it=1) j ON e.job=j.id"
        )
        if r[0]
    }
    counts["jobs_with_it_title"] = len(it_jobs)
    counts["candidate_cv_ids_for_it_events"] = len(cv_ids)
    print(json.dumps(counts, ensure_ascii=False), flush=True)

    def cv(n, r):
        if r["id_cv"] not in cv_ids:
            return None
        return (
            r["id_cv"],
            r["id_candidate"],
            valid_date(r["date_last_updated"]),
            clean("\n".join(r[k] for k in FIELDS["cv"])),
            n,
        )

    checkpoint("cvs", "curricula_vitae.csv", "CREATE INDEX cv_id ON cvs(id, day);", cv)
    statuses = Counter()

    def application(n, r):
        statuses[r["response_type"]] += 1
        if r["id_vacancy"] not in it_jobs:
            return None
        return event(n, r, "id_invitation")

    # On completed-stage resume, recount all statuses as this table holds only the IT subset.
    app_complete = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name='app_pair'"
    ).fetchone()
    checkpoint(
        "applications",
        "invitations.csv",
        "CREATE INDEX app_eid ON applications(eid); CREATE INDEX app_reply ON applications(reply); CREATE INDEX app_pair ON applications(cv,job);",
        application,
    )
    if app_complete:
        for _, r in stream(source / "invitations.csv", {}):
            statuses[r["response_type"]] += 1
    counts["invitation_types_all"] = dict(statuses)
    counts["stored"] = {
        t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("events", "jobs", "cvs", "applications")
    }
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db.close()
    write_json(
        out / "scan.json",
        {
            "version": VERSION,
            "source_url": SOURCE_URL,
            "inputs": inputs,
            "counts": counts,
            "resumed": resume,
            "seconds_this_invocation": time.monotonic() - start,
        },
    )
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--resume", action="store_true")
    a = p.parse_args()
    build(a.source, a.out, a.resume)

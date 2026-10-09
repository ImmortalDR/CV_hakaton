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


def stream(path, report):
    before = path.stat()
    sha = hashlib.sha256()
    count = 0

    def lines(f):
        for line in f:
            sha.update(line)
            yield line.decode("utf-8-sig" if f.tell() == len(line) else "utf-8")

    csv.field_size_limit(50_000_000)
    with path.open("rb") as f:
        reader = csv.DictReader(lines(f), delimiter=";")
        for count, row in enumerate(reader, 1):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Malformed CSV: {path.name}, record {count}")
            yield count, row
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


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def build(source, out):
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    db = sqlite3.connect(out / "index.sqlite")
    db.execute("PRAGMA cache_size=-32000")
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(
        """
    CREATE TABLE events(eid TEXT, reply TEXT, cv TEXT, person TEXT, job TEXT, org TEXT,
      kind TEXT, day TEXT, published TEXT, rownum INTEGER);
    CREATE TABLE jobs(id TEXT, org TEXT, day TEXT, text TEXT, is_it INTEGER, rownum INTEGER);
    CREATE TABLE cvs(id TEXT, person TEXT, day TEXT, text TEXT, rownum INTEGER);
    CREATE TABLE applications(eid TEXT, reply TEXT, cv TEXT, person TEXT, job TEXT,
      org TEXT, kind TEXT, day TEXT, published TEXT, rownum INTEGER);
    """
    )
    inputs, counts = {}, {}
    statuses = Counter()
    for n, r in stream(source / "responses.csv", inputs):
        statuses[r["response_type"]] += 1
        db.execute(
            "INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                r["id_response"],
                r["id_reply"],
                r["id_cv"],
                r["id_candidate"],
                r["id_vacancy"],
                r["id_hiring_organization"],
                r["response_type"],
                event_date(r),
                valid_date(r["date_last_updated"]),
                n,
            ),
        )
        if n % 50000 == 0:
            db.commit()
    db.commit()
    db.executescript(
        "CREATE INDEX event_job ON events(job); CREATE INDEX event_eid ON events(eid);"
    )
    counts["response_types_all"] = dict(statuses)
    wanted_jobs = {r[0] for r in db.execute("SELECT DISTINCT job FROM events") if r[0]}
    print(json.dumps({"wanted_job_ids": len(wanted_jobs)}), flush=True)
    for n, r in stream(source / "vacancies.csv", inputs):
        if r["identifier"] not in wanted_jobs:
            continue
        text = clean("\n".join(r[k] for k in FIELDS["job"]))
        db.execute(
            "INSERT INTO jobs VALUES(?,?,?,?,?,?)",
            (
                r["identifier"],
                r["id_hiring_organization"],
                valid_date(r["date_last_updated"]),
                text,
                int(bool(IT_TITLE.search(r["title"]))),
                n,
            ),
        )
        if n % 50000 == 0:
            db.commit()
    db.commit()
    db.executescript("CREATE INDEX job_id ON jobs(id, day);")
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
    for n, r in stream(source / "curricula_vitae.csv", inputs):
        if r["id_cv"] not in cv_ids:
            continue
        text = clean("\n".join(r[k] for k in FIELDS["cv"]))
        db.execute(
            "INSERT INTO cvs VALUES(?,?,?,?,?)",
            (
                r["id_cv"],
                r["id_candidate"],
                valid_date(r["date_last_updated"]),
                text,
                n,
            ),
        )
        if n % 50000 == 0:
            db.commit()
    db.commit()
    db.executescript("CREATE INDEX cv_id ON cvs(id, day);")
    statuses = Counter()
    for n, r in stream(source / "invitations.csv", inputs):
        statuses[r["response_type"]] += 1
        if r["id_vacancy"] not in it_jobs:
            continue
        db.execute(
            "INSERT INTO applications VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                r["id_invitation"],
                r["id_reply"],
                r["id_cv"],
                r["id_candidate"],
                r["id_vacancy"],
                r["id_hiring_organization"],
                r["response_type"],
                event_date(r),
                valid_date(r["date_last_updated"]),
                n,
            ),
        )
        if n % 50000 == 0:
            db.commit()
    db.commit()
    db.executescript(
        "CREATE INDEX app_eid ON applications(eid); CREATE INDEX app_reply ON applications(reply); CREATE INDEX app_pair ON applications(cv,job);"
    )
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
            "seconds": time.monotonic() - start,
        },
    )
    print(json.dumps(counts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    build(args.source, args.out)

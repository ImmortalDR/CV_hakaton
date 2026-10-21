"""Version 2: explicit replies to candidate applications, with pre-application features."""

from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from pairs import asof, split_pairs
from prepare import csv_rows, digest, technology_mentioned, valid_date, write_json

LABELS = {"Принятие": 1, "Отказ": 0}
WINDOW_DAYS = 30


def decision_reason(e, a, created):
    if a["kind"] != "Отклик соискателя" or e["kind"] not in LABELS:
        return "not_an_application_decision"
    if (
        not a["eid"]
        or a["reply"] != e["eid"]
        or not all(e[k] for k in ("cv", "person", "job", "org"))
    ):
        return "missing_identity"
    if any(e[k] != a[k] for k in ("cv", "person", "job", "org")):
        return "identity_mismatch"
    if not created or not e["day"] or not a["published"] or not e["published"]:
        return "invalid_date"
    if created > a["published"] or e["day"] > e["published"]:
        return "date_after_snapshot"
    days = (date.fromisoformat(e["day"]) - date.fromisoformat(created)).days
    if days < 0:
        return "reply_precedes_application"
    if days > WINDOW_DAYS:
        return "outside_30_day_window"
    return None


def build(root, source, out):
    os.umask(0o077)
    scan = json.loads((root / "scan.json").read_text())
    out.mkdir(parents=True, exist_ok=False)
    db = sqlite3.connect(f'file:{root / "index.sqlite"}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    apps = {r["rownum"]: dict(r) for r in db.execute("SELECT * FROM applications")}
    created = {}
    inputs = {}
    # The source modification date can be AFTER the reply. Recover creation instead.
    for n, header, values in csv_rows(source / "invitations.csv", inputs):
        if n not in apps:
            continue
        r = dict(zip(header, values))
        a = apps[n]
        if r["id_invitation"] != a["eid"] or r["id_reply"] != a["reply"]:
            raise ValueError("Application source reference no longer matches index")
        created[n] = (
            valid_date(r["date_creation"])
            if r["date_creation_mistake"] in ("", "0")
            else ""
        )
    if inputs["invitations.csv"] != scan["inputs"]["invitations.csv"]:
        raise ValueError("Raw source differs from frozen scan")
    jobs = defaultdict(list)
    cvs = defaultdict(list)
    for r in db.execute(
        "SELECT j.* FROM jobs j JOIN (SELECT DISTINCT id FROM jobs WHERE is_it=1) i ON j.id=i.id"
    ):
        jobs[r["id"]].append(dict(r))
    for r in db.execute("SELECT * FROM cvs"):
        cvs[r["id"]].append(dict(r))
    counts = Counter()
    linked = []
    for a in apps.values():
        counts["stored_it_applications"] += 1
        if not a["reply"]:
            counts["no_reply_unknown"] += 1
            continue
        es = [
            dict(r)
            for r in db.execute("SELECT * FROM events WHERE eid=?", (a["reply"],))
        ]
        if len(es) != 1:
            counts["reply_missing_or_ambiguous"] += 1
            continue
        e = es[0]
        reason = decision_reason(e, a, created[a["rownum"]])
        if reason:
            counts[reason] += 1
            continue
        linked.append((e, a, created[a["rownum"]]))
    histories = defaultdict(set)
    for e, a, day in linked:
        histories[(e["cv"], e["job"])].add(LABELS[e["kind"]])
    grouped = defaultdict(list)
    for e, a, day in linked:
        if len(histories[(e["cv"], e["job"])]) > 1:
            counts["conflicting_closed_pair_histories"] += 1
            continue
        j, reason = asof(jobs[e["job"]], day)
        if reason:
            counts["job_" + reason] += 1
            continue
        c, reason = asof(cvs[e["cv"]], day)
        if reason:
            counts["cv_" + reason] += 1
            continue
        if not j["is_it"]:
            counts["not_it_at_application"] += 1
            continue
        if j["org"] != e["org"] or c["person"] != e["person"]:
            counts["document_identity_mismatch"] += 1
            continue
        if len(c["text"]) < 30 or len(j["text"]) < 60:
            counts["insufficient_professional_text"] += 1
            continue
        p = {
            "pair_id": digest(e["cv"] + "|" + e["job"]),
            "cv_id": digest(e["cv"]),
            "person_id": digest(e["person"]),
            "job_id": digest(e["job"]),
            "candidate_text": c["text"],
            "need_text": j["text"],
            "label": LABELS[e["kind"]],
            "label_origin": "source_reply_to_application",
            "source_status": e["kind"],
            "application_day": day,
            "event_day": e["day"],
            "cv_snapshot_day": c["day"],
            "job_snapshot_day": j["day"],
            "source_refs": {
                "invitations.csv": a["rownum"],
                "responses.csv": e["rownum"],
                "curricula_vitae.csv": c["rownum"],
                "vacancies.csv": j["rownum"],
            },
            "target_scope": "recorded_application_acceptance_vs_refusal_within_30_days",
            "direction_basis": "explicit_id_reply_to_candidate_application; not independently certified",
        }
        grouped[p["pair_id"]].append(p)
    pairs = []
    for key, rows in sorted(grouped.items()):
        pairs.append(
            min(
                rows,
                key=lambda p: (
                    p["application_day"],
                    p["event_day"],
                    p["source_refs"]["invitations.csv"],
                ),
            )
        )
        counts["repeat_closed_pair_observations_removed"] += len(rows) - 1
    groups = split_pairs(pairs)
    with (out / "pairs.jsonl").open("x") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n")
    old = [json.loads(line) for line in (root / "pairs.jsonl").read_text().splitlines()]
    test = [p for p in pairs if p["split"] == "test"]
    overlap = {
        key: sum(p[key] in {x[key] for x in old} for p in test)
        for key in (
            "pair_id",
            "cv_id",
            "person_id",
            "job_id",
            "candidate_text",
            "need_text",
        )
    }
    report = {
        "version": "application-decisions-v2",
        "target": "recorded_application_acceptance_vs_refusal_within_30_days",
        "features_as_of": "strictly_before_application_creation",
        "label_window_days": WINDOW_DAYS,
        "direction_basis": "explicit reply link, same CV/person/job/organization, chronological consistency",
        "actor_semantics_verified_by_publisher": False,
        "verified_professional_suitability_labels": 0,
        "pairs": len(pairs),
        "counts": dict(counts),
        "split": {
            s: dict(Counter(str(p["label"]) for p in pairs if p["split"] == s))
            for s in ("train", "validation", "test")
        },
        **groups,
        "vacancy_technology_mentions": {
            term: sum(technology_mentioned(p["need_text"], term) for p in pairs)
            for term in ("python", "sql")
        },
        "test_rows_overlapping_v1_by_field": overlap,
        "test_pristine_relative_to_v1": not any(overlap.values()),
        "pairs_sha256": hashlib.sha256((out / "pairs.jsonl").read_bytes()).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "production_promotion_allowed": False,
        "limitations": [
            "Recorded reply outcome is not a hiring result or verified skill.",
            "Only closed observed applications within 30 days; missing/delayed responses are unknown.",
            "Historical and selected cohort, heuristic broad IT titles, short CV fields.",
            "V2 is exploratory after V1; overlapping records are disclosed and are not a fresh external test.",
        ],
    }
    shutil.copyfile(root / "scan.json", out / "scan.json")
    write_json(out / "pairs-report.json", report)
    db.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    build(a.root, a.source, a.out)

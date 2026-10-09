"""Reconstruct dated, source-labelled pairs; freeze splits before fitting."""

from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
import hashlib
import os
from pathlib import Path
import sqlite3
from prepare import digest, write_json, technology_mentioned

SEED = "fsp-trudvsem-20261009-v1"
# Literal source events, deliberately NOT labels of competence or suitability.
LABELS = {"Приглашение": 1, "Отказ": 0}


def asof(rows, day):
    """Daily snapshots must precede the decision. Ambiguous same-day versions fail."""
    eligible = [r for r in rows if r["day"] and r["day"] < day]
    if not eligible:
        return None, "no_pre_event_version"
    latest = max(r["day"] for r in eligible)
    versions = [r for r in eligible if r["day"] == latest]
    if (
        len(
            {
                (r["text"], r.get("org"), r.get("person"), r.get("is_it"))
                for r in versions
            }
        )
        != 1
    ):
        return None, "ambiguous_pre_event_version"
    return min(versions, key=lambda r: r["rownum"]), None


class Union:
    def __init__(self):
        self.parent = {}

    def root(self, a):
        self.parent.setdefault(a, a)
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def join(self, a, b):
        a, b = self.root(a), self.root(b)
        self.parent[max(a, b)] = min(a, b)


def split_pairs(pairs):
    """Connected components isolate people, CVs, jobs and exact document copies."""
    u = Union()
    for p in pairs:
        keys = [
            "person:" + p["person_id"],
            "cv:" + p["cv_id"],
            "job:" + p["job_id"],
            "ct:" + digest(p["candidate_text"]),
            "jt:" + digest(p["need_text"]),
        ]
        for key in keys[1:]:
            u.join(keys[0], key)
    counts = Counter()
    for p in pairs:
        group = u.root("person:" + p["person_id"])
        bucket = int(digest(SEED + group)[:8], 16) / 2**32
        p["split"] = (
            "train" if bucket < 0.7 else "validation" if bucket < 0.85 else "test"
        )
        p["group_id"] = digest(group)
        counts[p["group_id"]] += 1
    return {
        "connected_components": len(counts),
        "largest_component_pairs": max(counts.values(), default=0),
    }


def build(root):
    os.umask(0o077)
    if not (root / "scan.json").is_file():
        raise ValueError("Incomplete scan: scan.json is required before freezing pairs")
    if (root / "pairs.jsonl").exists():
        raise FileExistsError("Pairs are frozen; use another build directory")
    db = sqlite3.connect(f'file:{root / "index.sqlite"}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    jobs, cvs = defaultdict(list), defaultdict(list)
    for row in db.execute(
        "SELECT j.* FROM jobs j JOIN (SELECT DISTINCT id FROM jobs WHERE is_it=1) i ON j.id=i.id"
    ):
        jobs[row["id"]].append(dict(row))
    for row in db.execute("SELECT * FROM cvs"):
        cvs[row["id"]].append(dict(row))
    it_jobs = {j for j, rows in jobs.items() if any(r["is_it"] for r in rows)}
    events = defaultdict(list)
    for row in db.execute("SELECT * FROM events"):
        if row["job"] in it_jobs:
            events[row["eid"]].append(dict(row))
    historical_labels = defaultdict(set)
    for versions in events.values():
        for e in versions:
            if e["kind"] in LABELS:
                historical_labels[(e["cv"], e["job"])].add(LABELS[e["kind"]])
    counts = Counter()
    links = Counter()
    preliminary = []
    for eid, versions in sorted(events.items()):
        counts["it_event_ids"] += 1
        if (
            not eid
            or len(
                {
                    (v["kind"], v["cv"], v["person"], v["job"], v["org"], v["day"])
                    for v in versions
                }
            )
            != 1
        ):
            counts["ambiguous_event"] += 1
            continue
        e = min(versions, key=lambda v: (v["published"], v["rownum"]))
        if e["kind"] not in LABELS:
            counts["other_status_not_negative"] += 1
            continue
        if len(historical_labels[(e["cv"], e["job"])]) > 1:
            counts["events_from_conflicting_pair_histories"] += 1
            continue
        if (
            not all(e[k] for k in ("cv", "person", "job", "org", "day", "published"))
            or e["day"] > e["published"]
        ):
            counts["invalid_event_identity_or_date"] += 1
            continue
        # Audit both documented cross-table directions; pair coincidence isn't a reply link.
        linked = [
            dict(x)
            for x in db.execute(
                "SELECT * FROM applications WHERE (eid=? AND eid<>'') OR (reply=? AND reply<>'')",
                (e["reply"], eid),
            )
        ]
        same = [
            x
            for x in linked
            if all(x[k] == e[k] for k in ("cv", "person", "job", "org"))
        ]
        links["explicit_link_same_pair"] += bool(same)
        links["explicit_link_different_pair"] += any(x not in same for x in linked)
        for x in same:
            links[e["kind"] + " <- " + x["kind"]] += 1
        j, reason = asof(jobs[e["job"]], e["day"])
        if reason:
            counts["job_" + reason] += 1
            continue
        c, reason = asof(cvs[e["cv"]], e["day"])
        if reason:
            counts["cv_" + reason] += 1
            continue
        if not j["is_it"]:
            counts["not_it_at_event"] += 1
            continue
        if j["org"] != e["org"] or c["person"] != e["person"]:
            counts["identity_mismatch"] += 1
            continue
        if len(c["text"]) < 30 or len(j["text"]) < 60:
            counts["insufficient_professional_text"] += 1
            continue
        preliminary.append(
            {
                "pair_id": digest(e["cv"] + "|" + e["job"]),
                "cv_id": digest(e["cv"]),
                "person_id": digest(e["person"]),
                "job_id": digest(e["job"]),
                "candidate_text": c["text"],
                "need_text": j["text"],
                "label": LABELS[e["kind"]],
                "label_origin": "source_recorded_event",
                "source_status": e["kind"],
                "event_day": e["day"],
                "cv_snapshot_day": c["day"],
                "job_snapshot_day": j["day"],
                "source_refs": {
                    "responses.csv": e["rownum"],
                    "curricula_vitae.csv": c["rownum"],
                    "vacancies.csv": j["rownum"],
                },
                "explicit_reply_link": bool(same),
                "reply_source_refs": [
                    {
                        "file": "invitations.csv",
                        "record": x["rownum"],
                        "source_status": x["kind"],
                    }
                    for x in sorted(same, key=lambda x: x["rownum"])
                ],
                "target_scope": "recorded_invitation_vs_refusal_actor_unresolved",
            }
        )
    # Conflicting pair histories are uncertain, not majority-voted; one pair once.
    grouped = defaultdict(list)
    for p in preliminary:
        grouped[p["pair_id"]].append(p)
    pairs = []
    for pid, rows in sorted(grouped.items()):
        if len({p["label"] for p in rows}) != 1:
            counts["conflicting_pair_histories"] += 1
            continue
        p = min(rows, key=lambda x: (x["event_day"], x["source_refs"]["responses.csv"]))
        pairs.append(p)
        counts["duplicate_pair_observations_removed"] += len(rows) - 1
    groups = split_pairs(pairs)
    with (root / "pairs.jsonl").open("x") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n")
    report = {
        "target": "recorded_invitation_vs_refusal",
        "actor_semantics_verified": False,
        "verified_professional_suitability_labels": 0,
        "counts": dict(counts),
        "explicit_links": dict(links),
        "pairs": len(pairs),
        "vacancy_technology_mentions": {
            term: sum(technology_mentioned(p["need_text"], term) for p in pairs)
            for term in ("python", "sql")
        },
        "split": {
            s: dict(Counter(str(p["label"]) for p in pairs if p["split"] == s))
            for s in ("train", "validation", "test")
        },
        **groups,
        "seed": SEED,
        "pairs_sha256": hashlib.sha256((root / "pairs.jsonl").read_bytes()).hexdigest(),
        "features": {
            "candidate": ["position_name", "skills"],
            "vacancy": ["title", "requirements_qualifications", "responsibilities"],
        },
        "production_promotion_allowed": False,
        "limitations": [
            "Actor of refusal unresolved: not a suitability gold standard.",
            "Selected observed interactions only; unobserved pairs have no negative label.",
            "Daily as-of snapshots strictly precede event; snapshot availability does not prove no selection bias.",
            "Broad IT title cohort, not exclusively Python/Data; historic source 2018–2021.",
            "No human judgement, certification, grade or FSP labels. No workexp/education enrichment in v1.",
        ],
    }
    write_json(root / "pairs-report.json", report)
    db.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    build(p.parse_args().root)

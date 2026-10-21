"""Streaming local-only adapters. Raw files and source labels remain unchanged."""

import csv
import hashlib
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from itertools import combinations
from pathlib import Path

from .common import csv_rows, record, source_ref, write_json


def external_candidate(original_id, text, *, specialization=None, group=None):
    return {
        "specialization": specialization,
        "claimed_grade": None,
        "verified_grade": None,
        "grade_status": "not_assessed",
        "skills": [],
        "evidence": [],
        "test_score": 0,
        "achievements": [],
        "leakage_group_id": group or original_id,
        "profile_text": text,
        "original_id": original_id,
        "simulation_ref": None,
        "mapping_status": "unreviewed",
    }


def external_need(original_id, title, text, **kwargs):
    return {
        "criteria": None,
        "title": title,
        "description": text,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "leakage_group_id": original_id,
        "original_id": original_id,
        "mapping_status": "unreviewed",
        **kwargs,
    }


def tianchi(writer, root):
    root = Path(root)
    confit = root / "raw_sources/confit/ConFit-master.zip"
    labeled = []
    with zipfile.ZipFile(confit) as z:
        for split, filename in [
            ("train", "train_labeled_data.jsonl"),
            ("valid", "valid_classification_data.jsonl"),
            ("test", "test_classification_data.jsonl"),
        ]:
            member = "ConFit-master/dataset/AliTianChi/" + filename
            with z.open(member) as f:
                for ordinal, line in enumerate(f, 1):
                    if line.strip():
                        labeled.append((split, member, ordinal, json.loads(line)))
        pools = json.loads(z.read("ConFit-master/dataset/AliTianChi/rank_resume.json"))
    needed_jobs = {str(r["jd_no"]) for _, _, _, r in labeled} | set(pools)
    users = set()
    userfile = "raw_sources/tianchi/table1_user.csv"
    for ordinal, row in csv_rows(root / userfile):
        uid = row["user_id"]
        users.add(uid)
        payload = external_candidate(
            uid, row.get("experience", ""), group="tianchi:user:" + uid
        )
        writer.add(
            "data/tianchi/candidates.jsonl",
            record(
                "candidate",
                "tc:u:" + uid,
                "tianchi",
                payload,
                refs=[
                    source_ref("tianchi", userfile, f"record:{ordinal};user_id:{uid}")
                ],
            ),
        )
    all_jobs, selected_jobs = set(), set()
    jobfile = "raw_sources/tianchi/table2_jd.csv"
    duplicate_text = Counter()
    job_text_hashes = {}
    for ordinal, row in csv_rows(root / jobfile, "\t"):
        jid = row["jd_no"]
        if jid in all_jobs:
            raise ValueError("Duplicate job ID in Tianchi")
        all_jobs.add(jid)
        if jid not in needed_jobs:
            continue
        text = row["job_description"]
        if "[[LONG_" in text:
            raise ValueError("Placeholder source text")
        digest = hashlib.sha256(text.strip().encode()).hexdigest()
        duplicate_text[digest] += 1
        job_text_hashes[jid] = digest
        selected_jobs.add(jid)
        writer.add(
            "data/tianchi/needs.jsonl",
            record(
                "need",
                "tc:j:" + jid,
                "tianchi",
                external_need(
                    jid,
                    row["jd_title"],
                    text,
                    leakage_group_id="tianchi:text:" + digest,
                ),
                refs=[source_ref("tianchi", jobfile, f"record:{ordinal};jd_no:{jid}")],
            ),
        )
    counts, combo, missing_flags = Counter(), Counter(), Counter()
    actual = {}
    missing_job_ids = set()
    needed_pairs = {(str(r["user_id"]), str(r["jd_no"])) for _, _, _, r in labeled}
    needed_pairs.update((str(u), j) for j, p in pools.items() for u in p["user_ids"])
    actionfile = "raw_sources/tianchi/table3_action.csv"
    for ordinal, row in csv_rows(root / actionfile):
        uid, jid = row["user_id"], row["jd_no"]
        flags = {k: int(row[k]) for k in ["browsed", "delivered", "satisfied"]}
        if not all(v in [0, 1] for v in flags.values()):
            raise ValueError("Unexpected event flag")
        counts["source_events"] += 1
        combo[tuple(flags.values())] += 1
        if uid not in users:
            counts["missing_user_events"] += 1
        if jid not in all_jobs:
            counts["missing_job_events"] += 1
            missing_job_ids.add(jid)
            missing_flags[tuple(flags.values())] += 1
        if (uid, jid) in needed_pairs:
            actual.setdefault((uid, jid), set()).add(flags["satisfied"])
        if uid in users and jid in selected_jobs:
            writer.add(
                "data/tianchi/outcomes.jsonl",
                record(
                    "outcome",
                    f"tc:a:{ordinal}",
                    "tianchi",
                    {
                        "candidate_id": "tc:u:" + uid,
                        "need_id": "tc:j:" + jid,
                        "flags": flags,
                        "label_semantics": "historical_outcome",
                        "original_record": str(ordinal),
                    },
                    label_origin="source_annotation",
                    refs=[source_ref("tianchi", actionfile, f"record:{ordinal}")],
                ),
            )
            counts["exported_events"] += 1
    checks = Counter(
        {
            key: 0
            for key in [
                "classification_missing_documents",
                "classification_label_conflicts",
                "ranking_incomplete_pools",
                "ranking_pairs_without_event",
                "ranking_negative_one_with_positive_event",
            ]
        }
    )
    for split, member, ordinal, row in labeled:
        uid, jid = str(row["user_id"]), str(row["jd_no"])
        if uid not in users or jid not in selected_jobs:
            checks["classification_missing_documents"] += 1
            continue
        if row["satisfied"] not in actual.get((uid, jid), set()):
            checks["classification_label_conflicts"] += 1
        writer.add(
            "data/tianchi/legacy_pairs.jsonl",
            record(
                "legacy_pair",
                f"tc:legacy:{split}:{ordinal}",
                "tianchi",
                {
                    "candidate_id": "tc:u:" + uid,
                    "need_id": "tc:j:" + jid,
                    "satisfied": row["satisfied"],
                    "original_split": split,
                    "label_semantics": "legacy_source_classification",
                },
                label_origin="source_annotation",
                refs=[
                    source_ref(
                        "confit",
                        "raw_sources/confit/ConFit-master.zip",
                        member + f":record:{ordinal}",
                    )
                ],
            ),
        )
    for jid, pool in sorted(pools.items()):
        if jid not in selected_jobs or any(
            str(u) not in users for u in pool["user_ids"]
        ):
            checks["ranking_incomplete_pools"] += 1
            continue
        for uid, label in zip(pool["user_ids"], pool["satisfied"]):
            pair = (str(uid), jid)
            if pair not in actual:
                checks["ranking_pairs_without_event"] += 1
            if label == -1 and 1 in actual.get(pair, set()):
                checks["ranking_negative_one_with_positive_event"] += 1
        writer.add(
            "data/tianchi/legacy_pools.jsonl",
            record(
                "legacy_pool",
                "tc:pool:" + jid,
                "tianchi",
                {
                    "need_id": "tc:j:" + jid,
                    "candidate_ids": ["tc:u:" + str(u) for u in pool["user_ids"]],
                    "labels": pool["satisfied"],
                    "label_semantics": "legacy_source_ranking_not_semantic_gold",
                },
                label_origin="source_annotation",
                refs=[
                    source_ref(
                        "confit",
                        "raw_sources/confit/ConFit-master.zip",
                        "rank_resume.json:" + jid,
                    )
                ],
            ),
        )
    split_sets = {}
    for split in ["train", "valid", "test"]:
        pairs = {
            (str(r["user_id"]), str(r["jd_no"])) for s, _, _, r in labeled if s == split
        }
        split_sets[split] = {
            "pairs": pairs,
            "users": {u for u, _ in pairs},
            "jobs": {j for _, j in pairs},
            "exact_job_texts": {
                job_text_hashes[j] for _, j in pairs if j in job_text_hashes
            },
        }
    overlap = {
        a
        + "__"
        + b: {k: len(split_sets[a][k] & split_sets[b][k]) for k in split_sets[a]}
        for a, b in combinations(split_sets, 2)
    }
    counts["missing_unique_job_ids"] = len(missing_job_ids)
    return {
        "status": "built_local_only",
        "users": len(users),
        "all_source_jobs": len(all_jobs),
        "selected_jobs": len(selected_jobs),
        "selection": "all ConFit classification jobs and rank_resume queries",
        "selected_exact_text_duplicate_extra_rows": sum(
            n - 1 for n in duplicate_text.values()
        ),
        "counts": dict(counts),
        "checks": dict(checks),
        "legacy_split_overlap": overlap,
        "event_flags": {str(k): v for k, v in sorted(combo.items())},
        "missing_job_flags": {str(k): v for k, v in sorted(missing_flags.items())},
        "application_evaluation": "not_run: these documents have no verified MVP grade",
        "split_policy": "legacy splits retained; no claim of near-duplicate-free holdout",
        "salary_policy": "Original salary scale/currency not established; normalized RUB salary remains null",
    }


def classify_text(text):
    text = text.lower()
    if re.search(r"\bpython\b", text):
        return "python"
    if re.search(r"\bsql\b", text) and ("аналит" in text or "analyst" in text):
        return "data"
    return None


def trudvsem(writer, root, scan_limit=100000, max_records=200):
    root = Path(root)
    results = {}
    for table, kind in [
        ("curricula_vitae.csv", "candidate"),
        ("vacancies.csv", "need"),
    ]:
        path = "raw_sources/trudvsem/" + table
        selected, scanned, seen = 0, 0, set()
        ended = True
        for ordinal, row in csv_rows(root / path, ";"):
            if ordinal > scan_limit:
                ended = False
                break
            scanned += 1
            title = row.get("position_name", row.get("title", ""))
            keys = (
                ["skills", "other_info_modified", "additional_skills"]
                if kind == "candidate"
                else ["responsibilities", "requirements_qualifications"]
            )
            text = "\n".join([title] + [row.get(k, "") for k in keys])
            spec = classify_text(text)
            oid = row.get("id_cv", row.get("identifier", ""))
            if not spec or not oid or oid in seen or selected >= max_records:
                continue
            seen.add(oid)
            selected += 1
            rid = "tv:" + ("u:" if kind == "candidate" else "j:") + oid
            if kind == "candidate":
                group = row.get("id_candidate") or oid
                payload = external_candidate(
                    oid, text, specialization=spec, group="trudvsem:person:" + group
                )
            else:
                payload = external_need(oid, title, text)
            writer.add(
                f"data/trudvsem/{kind}s.jsonl",
                record(
                    kind,
                    rid,
                    "trudvsem",
                    payload,
                    refs=[
                        source_ref(
                            "trudvsem",
                            path,
                            f"record:{ordinal};id:{oid};version:{row.get('date_last_updated','')}",
                        )
                    ],
                ),
            )
        results[table] = {
            "scanned_records": scanned,
            "selected": selected,
            "full_scan": ended,
            "selection": "first unique documents with literal Python or SQL+analyst; mapping unreviewed; first encountered version",
        }
    # Preserve a bounded sample of original event values without inventing normalized direction.
    for table in ["invitations.csv", "responses.csv"]:
        counts = Counter()
        for ordinal, row in csv_rows(root / ("raw_sources/trudvsem/" + table), ";"):
            if ordinal > 1000:
                break
            counts[row.get("response_type", "")] += 1
            writer.add(
                "data/trudvsem/events_unresolved.jsonl",
                record(
                    "historical_event",
                    f"tv:{table}:{ordinal}",
                    "trudvsem",
                    {
                        "original_values": row,
                        "label_semantics": "unresolved_source_event_direction",
                        "usable_for_semantic_scoring": False,
                    },
                    label_origin="source_annotation",
                    refs=[
                        source_ref(
                            "trudvsem",
                            "raw_sources/trudvsem/" + table,
                            f"record:{ordinal}",
                        )
                    ],
                ),
            )
        results[table] = {
            "sample_records": sum(counts.values()),
            "response_type": dict(counts),
        }
    return {
        "status": "built_bounded_sample_local_only",
        "tables": results,
        "limitations": [
            "Не случайная репрезентативная выборка рынка, ограниченный последовательный просмотр.",
            "Маппинг Python/Data — эвристика, не экспертная метка. Нет подтверждённых грейдов.",
            "Смысл/направление событий не установлен; события не связаны с выбранными документами как подтверждённые исходы.",
            "workexp/edu не присоединены: выбранные документы ограничены полями основной таблицы.",
            "Не установлена версия документа на момент события; temporal_leakage_risk=true.",
        ],
    }


def auxiliary(writer, root):
    root = Path(root)
    summary = {}
    for task in ["A", "B"]:
        file = f"raw_sources/talentclef/Task{task}.zip"
        with zipfile.ZipFile(root / file) as z:
            prefix = "validation/english/" if task == "A" else "validation/"
            lookups = {}
            for member, key in [("queries", "q_id"), ("corpus_elements", "c_id")]:
                with z.open(prefix + member) as f:
                    lookups[member] = {
                        r[key]: r
                        for r in csv.DictReader(
                            io.TextIOWrapper(f, encoding="utf-8-sig"), delimiter="\t"
                        )
                    }
            n = 0
            with z.open(prefix + "qrels.tsv") as f:
                for ordinal, values in enumerate(
                    csv.reader(io.TextIOWrapper(f, encoding="utf-8"), delimiter="\t"), 1
                ):
                    qid, _, cid, relevance = values
                    n += 1
                    writer.add(
                        "data/auxiliary/talentclef.jsonl",
                        record(
                            "auxiliary",
                            f"talent:{task}:{ordinal}",
                            "talentclef",
                            {
                                "source_task": "Task" + task,
                                "original_values": {
                                    "query": lookups["queries"][qid],
                                    "corpus": lookups["corpus_elements"][cid],
                                    "relevance": int(relevance),
                                },
                                "label_semantics": (
                                    "job_title_match"
                                    if task == "A"
                                    else "job_title_skill"
                                ),
                                "original_locator": prefix
                                + f"qrels.tsv:record:{ordinal}",
                            },
                            label_origin="source_annotation",
                            refs=[
                                source_ref(
                                    "talentclef",
                                    file,
                                    prefix + f"qrels.tsv:record:{ordinal}",
                                )
                            ],
                        ),
                    )
            summary["Task" + task] = {
                "validation_qrels": n,
                "test_files": sum(
                    p.startswith("test/") and not p.endswith("/") for p in z.namelist()
                ),
                "selection": "validation only; Task A English; samples/train not added as independent data",
            }
    file = "raw_sources/careercorpus/CareerCorpus.xlsx"
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    count = 0
    career_ids = Counter()
    with zipfile.ZipFile(root / file) as z:
        shared = [
            "".join(e.itertext()) for e in ET.fromstring(z.read("xl/sharedStrings.xml"))
        ]
        rows = ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall(".//m:row", ns)
        header = None
        for row in rows:
            values = {}
            for c in row.findall("m:c", ns):
                v = c.find("m:v", ns)
                if v is None:
                    continue
                col = re.sub(r"\d", "", c.attrib["r"])
                values[col] = (
                    shared[int(v.text)] if c.attrib.get("t") == "s" else v.text
                )
            if header is None:
                header = values
                continue
            if not values.get("A") or not values.get("B"):
                continue
            count += 1
            career_ids[values["A"]] += 1
            payload = {
                "source_task": "resume_scores",
                "original_values": {header[k]: v for k, v in values.items()},
                "label_semantics": "original_resume_score_rubric_unresolved",
                "original_locator": "Sheet1:row:" + row.attrib["r"],
            }
            writer.add(
                "data/auxiliary/careercorpus.jsonl",
                record(
                    "auxiliary",
                    "career:" + values["A"] + ":row:" + row.attrib["r"],
                    "careercorpus",
                    payload,
                    label_origin="source_annotation",
                    refs=[
                        source_ref("careercorpus", file, payload["original_locator"])
                    ],
                ),
            )
    summary["CareerCorpus"] = {
        "records": count,
        "unique_original_ids": len(career_ids),
        "duplicate_id_extra_rows": sum(n - 1 for n in career_ids.values()),
        "identity_policy": "Source ID is not unique; keep original ID and use sheet row for record identity",
        "pair_matching_eligible": False,
        "source_expert_labels_preserved": True,
        "our_human_reviewed_pairs": 0,
    }
    return summary

import re
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

from .common import dumps, read_json, records, safe_relative, sha256
from .schema import PAYLOADS, schema_for
from .synthetic import oracle


PUBLIC_FILES = (
    {
        "run.py",
        "requirements.lock.txt",
        "requirements-import.txt",
        "README.md",
        "DATASET_CARD.md",
        "ANNOTATION_GUIDE.md",
        "REQUIREMENTS_TRACEABILITY.md",
        "MVP_COMPATIBILITY.md",
        "LICENSES/OWN_MIT.txt",
        "sources.json",
        "SOURCES.md",
        "package.json",
        "splits.json",
        "AUDIT_PASSPORT.json",
        "VALIDATION_REPORT.json",
        "VALIDATION_REPORT.md",
        "manifest.json",
        "checksums.sha256",
        "snapshot/mvp/__init__.py",
        "snapshot/mvp/bank.py",
        "snapshot/mvp/matching.py",
        "snapshot/oracles.py",
        "data/synthetic/candidates.jsonl",
        "data/synthetic/needs.jsonl",
        "data/synthetic/pools.jsonl",
        "data/synthetic/simulations.jsonl",
        "labels/matching.jsonl",
        "assessment/attempts.jsonl",
        "scenarios/workflow.jsonl",
        "reports/assessment.json",
        "reports/matching.json",
        "reports/predictions.json",
        "reports/workflow-tests.json",
    }
    | {"schemas/" + k + ".json" for k in PAYLOADS}
    | {
        "fsp_dataset/" + k + ".py"
        for k in [
            "__init__",
            "assessment",
            "build",
            "catalog",
            "common",
            "evaluate",
            "external",
            "import_db",
            "inventory",
            "release",
            "schema",
            "synthetic",
            "validate",
        ]
    }
)


def validate(root, verify_manifest=True):
    try:
        return _validate(root, verify_manifest)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        # Do not echo untrusted record text, DSNs or secret-like payloads in errors.
        return {
            "status": "failed",
            "errors": ["Malformed or unreadable package: " + type(exc).__name__],
        }


def _validate(root, verify_manifest=True):
    root = Path(root)
    errors, counts, ids = [], Counter(), {}

    def fail(message):
        if len(errors) < 100:
            errors.append(message)

    validators = {k: Draft202012Validator(schema_for(k)) for k in PAYLOADS}
    metadata = read_json(root / "package.json")
    mode = metadata["mode"]
    if mode not in ["public", "local"]:
        fail("Invalid package mode")
    if metadata["external_models_used"] or metadata["external_api_calls"] != 0:
        fail("Unexpected external model provenance")
    if mode == "public":
        for p in root.rglob("*"):
            if p.is_symlink():
                fail("Public symlink blocked")
            if p.is_file() and p.relative_to(root).as_posix() not in PUBLIC_FILES:
                fail("File outside public allowlist")
    sources = {s["source_id"] for s in read_json(root / "sources.json")}
    inventory = (
        {x["path"] for x in read_json(root / "input_inventory.json")["files"]}
        if (root / "input_inventory.json").exists()
        else set()
    )
    candidate_payloads, need_payloads, judgments, pools, simulations = (
        {},
        {},
        {},
        [],
        {},
    )
    refs, groups = [], {}
    for path in sorted(root.rglob("*.jsonl")):
        if path.is_symlink():
            fail("Symlink JSONL")
            continue
        relative = path.relative_to(root).as_posix()
        # Predictions are evaluator artifacts, not source records.
        if relative.startswith("reports/"):
            continue
        for line_no, row in enumerate(records(path), 1):
            counts[relative] += 1
            if not isinstance(row, dict):
                fail("Record must be an object")
                continue
            rid, kind = row.get("record_id"), row.get("kind")
            if kind not in validators:
                fail(f"{relative}:{line_no}: unknown kind")
                continue
            problems = list(validators[kind].iter_errors(row))
            if problems:
                fail(
                    f"{relative}:{line_no}: schema violation at {list(problems[0].path)}"
                )
                continue
            if rid in ids:
                fail(f"Duplicate record ID: {rid}")
            ids[rid] = (kind, row["split"], row["track"])
            p = row["payload"]
            for ref in row["source_refs"]:
                if ref["source_id"] not in sources:
                    fail("Unknown source")
                if ref["source_id"] in ["team_synthetic", "mvp"]:
                    if not safe_relative(root, ref["file"]).is_file():
                        fail("Missing internal provenance file")
                elif ref["file"] not in inventory:
                    fail("Source file not in inventory")
            if mode == "public":
                if row["data_origin"] != "synthetic":
                    fail("Public data must be own synthetic records")
                if any(
                    ref["source_id"] not in ["team_synthetic", "mvp"]
                    for ref in row["source_refs"]
                ):
                    fail("External source content blocked in public package")
                if re.search(
                    r"sk-[A-Za-z0-9]{20,}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\+\d[\d ()-]{9,}",
                    dumps(row),
                ):
                    fail("Contact/secret-like string in public data")
            if "[[LONG_" in dumps(row):
                fail("Placeholder source text")
            if kind in ["candidate", "need"] and row["split"] != "external":
                group = (kind, p["leakage_group_id"])
                if group in groups and groups[group] != row["split"]:
                    fail("Entity leakage between splits")
                groups[group] = row["split"]
            if kind == "candidate":
                if row["data_origin"] != "synthetic":
                    if (
                        p["verified_grade"] is not None
                        or p["evidence"]
                        or p["achievements"]
                        or p["simulation_ref"]
                        or p["grade_status"] != "not_assessed"
                        or p["test_score"] != 0
                    ):
                        fail("Invented verified external qualification")
                else:
                    candidate_payloads[rid] = p
                    if (p["verified_grade"] is not None) != (
                        p["grade_status"] == "simulated_confirmed"
                    ):
                        fail("Inconsistent simulated grade")
                    if p["verified_grade"] is not None and not p["simulation_ref"]:
                        fail("Grade without simulation provenance")
                    if p["simulation_ref"]:
                        refs.append((rid, p["simulation_ref"], "simulation"))
            elif kind == "need" and row["data_origin"] == "synthetic":
                need_payloads[rid] = p
                if (
                    p["salary_currency"] != "RUB"
                    or p["salary_min"] is None
                    or p["salary_max"] is None
                    or p["salary_max"] < p["salary_min"]
                ):
                    fail("Invalid synthetic salary")
            elif kind in ["judgment", "outcome", "legacy_pair"]:
                refs.extend(
                    [(rid, p["candidate_id"], "candidate"), (rid, p["need_id"], "need")]
                )
                if kind == "judgment":
                    pair = (p["need_id"], p["candidate_id"])
                    if pair in judgments:
                        fail("Duplicate pair judgment")
                    judgments[pair] = p
                    if p["annotator_ids"] or row["label_origin"] != "team_rule_oracle":
                        fail("Invented human annotation")
                elif row["label_origin"] != "source_annotation":
                    fail("Outcome lost original annotation provenance")
            elif kind in ["pool", "legacy_pool"]:
                refs.append((rid, p["need_id"], "need"))
                refs.extend((rid, cid, "candidate") for cid in p["candidate_ids"])
                if len(set(p["candidate_ids"])) != len(p["candidate_ids"]):
                    fail("Duplicate candidate in pool")
                if kind == "pool":
                    pools.append(row)
                elif len(p["candidate_ids"]) != len(p["labels"]):
                    fail("Legacy pool label length mismatch")
            elif kind == "simulation":
                if (
                    row["data_origin"] != "synthetic"
                    or row["label_origin"] != "simulation"
                ):
                    fail("Simulation misrepresented")
                simulations[rid] = p
                refs.append((rid, p["candidate_id"], "candidate"))
            elif kind == "assessment_attempt":
                if (
                    row["data_origin"] != "synthetic"
                    or row["label_origin"] != "simulation"
                ):
                    fail("Simulated attempt misrepresented")
                qids = [q["id"] for q in p["questions"]]
                if (
                    len(set(qids)) != len(qids)
                    or set(qids) != set(p["answers"])
                    or set(qids) != set(p["reference_answers"])
                ):
                    fail("Attempt question/answer IDs inconsistent")
                if [d["id"] for d in p["application_result"]["details"]] != qids:
                    fail("Attempt detail IDs inconsistent")
            elif kind in ["auxiliary", "historical_event"]:
                if row["label_origin"] != "source_annotation":
                    fail("Source annotation provenance lost")
    for left, right, expected_kind in refs:
        if right not in ids:
            fail(f"Broken reference: {left} -> {right}")
        elif ids[right][0] != expected_kind:
            fail("Wrong reference type")
        elif ids[left][2] != ids[right][2]:
            fail("Reference crosses tracks")
        elif ids[left][1] != ids[right][1]:
            fail("Reference crosses splits")
    for cid, c in candidate_payloads.items():
        ref = c["simulation_ref"]
        if (
            ref
            and ref in simulations
            and (
                simulations[ref]["candidate_id"] != cid
                or simulations[ref]["declared_outcome"] != c["verified_grade"]
            )
        ):
            fail("Wrong grade simulation link")
    expected_pairs = set()
    for row in pools:
        pool = row["payload"]
        for cid in pool["candidate_ids"]:
            pair = (pool["need_id"], cid)
            expected_pairs.add(pair)
            if pair not in judgments:
                fail("Incomplete semantic pool")
                continue
            if cid in candidate_payloads and pool["need_id"] in need_payloads:
                expected = oracle(
                    candidate_payloads[cid], need_payloads[pool["need_id"]]["criteria"]
                )
                for key, value in expected.items():
                    if judgments[pair][key] != value:
                        fail("Decision/requirements contradict declared rubric")
    if set(judgments) != expected_pairs:
        fail("Judgments and declared pools differ")
    passport = read_json(root / "AUDIT_PASSPORT.json")
    if (
        passport.get("human_reviewed_new_pairs") != 0
        or passport.get("external_certification_status") != "not_certified"
        or passport.get("issuer") is not None
        or passport.get("certification_document_ref") is not None
    ):
        fail("Unsupported human review/certification claim")
    if passport.get("deepseek_used") is not False:
        fail("DeepSeek use is not authorized")
    if verify_manifest:
        manifest = read_json(root / "manifest.json")
        if manifest["mode"] != mode:
            fail("Manifest/package mode mismatch")
        allowed = {e["path"] for e in manifest["files"]}
        if len(allowed) != len(manifest["files"]):
            fail("Duplicate manifest path")
        actual = {
            p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
        }
        if actual != allowed | {"manifest.json", "checksums.sha256"}:
            fail("Unlisted or missing package file")
        for entry in manifest["files"]:
            path = safe_relative(root, entry["path"])
            if (
                not path.is_file()
                or sha256(path) != entry["sha256"]
                or path.stat().st_size != entry["bytes"]
            ):
                fail("Manifest hash/size mismatch")
            if (
                entry["records"] is not None
                and counts[entry["path"]] != entry["records"]
            ):
                fail("Manifest record count mismatch")
            if mode == "public" and entry["public_allowed"] is not True:
                fail("Unapproved public file")
            if any(
                part.startswith(".env") or part == "raw_sources"
                for part in Path(entry["path"]).parts
            ):
                fail("Private file in manifest")
        checksum_lines = (root / "checksums.sha256").read_text().splitlines()
        checksums = {}
        for line in checksum_lines:
            digest, name = line.split("  ", 1)
            if name in checksums:
                fail("Duplicate checksum path")
            checksums[name] = digest
        if set(checksums) != allowed | {"manifest.json"}:
            fail("Incomplete checksum set")
        for name, digest in checksums.items():
            path = safe_relative(root, name)
            if not path.is_file() or sha256(path) != digest:
                fail("Checksum mismatch")
    return {
        "status": "failed" if errors else "passed",
        "errors": errors,
        "records": sum(counts.values()),
        "counts": dict(counts),
        "scope": "Schemas, provenance links, IDs, references, matching splits/pools/rubric, public gate and optional manifest hashes",
        "limitations": [
            "Не полный семантический аудит реальных документов.",
            "Наличие хеша не подтверждает достоверность или права на исходный документ.",
        ],
    }

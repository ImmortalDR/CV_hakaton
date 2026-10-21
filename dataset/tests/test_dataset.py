import copy
import os
import shutil
import socket
import sys
import zipfile
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fsp_dataset.build import build
from fsp_dataset.common import (
    csv_rows,
    dumps,
    read_json,
    records,
    safe_relative,
    sha256,
    write_json,
)
from fsp_dataset.import_db import check_dsn, import_package
from fsp_dataset.release import release
from fsp_dataset.synthetic import oracle
from fsp_dataset.validate import validate

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    root = tmp_path_factory.mktemp("dataset") / "public"
    build(root, REPO)
    assert validate(root)["records"] == 1973
    return root


@pytest.fixture
def changed(package, tmp_path):
    root = tmp_path / "copy"
    shutil.copytree(package, root)
    return root


def rewrite(path, rows):
    path.write_text("".join(dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_validation_is_read_only(package):
    before = {
        p.relative_to(package): sha256(p) for p in package.rglob("*") if p.is_file()
    }
    assert validate(package)["status"] == "passed"
    assert before == {
        p.relative_to(package): sha256(p) for p in package.rglob("*") if p.is_file()
    }


def test_deterministic_build_and_archive(package, tmp_path):
    other = tmp_path / "second"
    build(other, REPO)
    assert sha256(other / "manifest.json") == sha256(package / "manifest.json")
    a, b = tmp_path / "a.zip", tmp_path / "b.zip"
    release(package, a, "public")
    release(other, b, "public")
    assert sha256(a) == sha256(b)
    with zipfile.ZipFile(a) as z:
        assert z.testzip() is None
        assert not any(".env" in n or "raw_sources" in n for n in z.namelist())


@pytest.mark.parametrize(
    "fault", ["duplicate", "broken_ref", "split_leak", "fake_grade", "placeholder"]
)
def test_candidate_corruption_rejected(changed, fault):
    path = changed / "data/synthetic/candidates.jsonl"
    rows = list(records(path))
    if fault == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif fault == "broken_ref":
        rows[0]["payload"]["simulation_ref"] = "missing"
    elif fault == "split_leak":
        test_row = next(r for r in rows if r["split"] == "test")
        test_row["payload"]["leakage_group_id"] = rows[0]["payload"]["leakage_group_id"]
    elif fault == "fake_grade":
        rows[0]["data_origin"] = "source"
    else:
        rows[0]["payload"]["profile_text"] = "[[LONG_RESUME_TEXT]]"
    rewrite(path, rows)
    assert validate(changed, verify_manifest=False)["status"] == "failed"


@pytest.mark.parametrize(
    "fault", ["human", "decision", "incomplete", "extra", "source_gold"]
)
def test_label_corruption_rejected(changed, fault):
    path = changed / "labels/matching.jsonl"
    rows = list(records(path))
    if fault == "human":
        rows[0]["payload"]["annotator_ids"] = ["invented-expert"]
    elif fault == "decision":
        rows[0]["payload"]["decision"] = "reject"
    elif fault == "incomplete":
        rows.pop()
    elif fault == "extra":
        rows[0]["payload"]["certified"] = True
    else:
        rows[0]["label_origin"] = "source_annotation"
    rewrite(path, rows)
    assert validate(changed, verify_manifest=False)["status"] == "failed"


def test_unknown_evidence_is_not_negative_even_with_large_fsp_bonus(package):
    candidate = copy.deepcopy(
        next(records(package / "data/synthetic/candidates.jsonl"))["payload"]
    )
    need = next(records(package / "data/synthetic/needs.jsonl"))["payload"]["criteria"]
    candidate["evidence"] = []
    candidate["achievements"] = [{"provider": "demo_fsp", "points": 100000}]
    label = oracle(candidate, need)
    assert label["decision"] == "insufficient_evidence"
    assert label["relevance"] is None


def test_invented_certification_rejected(changed):
    path = changed / "AUDIT_PASSPORT.json"
    value = read_json(path)
    value["external_certification_status"] = "certified"
    write_json(path, value)
    assert validate(changed, verify_manifest=False)["status"] == "failed"


def test_private_file_blocks_release(changed, tmp_path):
    (changed / ".env").write_text("TEST_ONLY=canary\n")
    out = tmp_path / "blocked.zip"
    with pytest.raises(ValueError):
        release(changed, out, "public")
    assert not out.exists()


def test_local_bundle_cannot_be_exported_as_public(changed, tmp_path):
    path = changed / "manifest.json"
    value = read_json(path)
    value["mode"] = "local"
    write_json(path, value)
    with pytest.raises(ValueError):
        release(changed, tmp_path / "blocked.zip", "public")


@pytest.mark.parametrize("path", ["../data", "/etc/passwd", "data/../../secret"])
def test_path_traversal_rejected(tmp_path, path):
    with pytest.raises(ValueError):
        safe_relative(tmp_path, path)


def test_symlink_rejected(tmp_path):
    (tmp_path / "linked").symlink_to("/etc/passwd")
    with pytest.raises(ValueError):
        safe_relative(tmp_path, "linked")


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://localhost/fsp",
        "postgresql://localhost/fsp_test",
        "postgresql://localhost/intellect",
        "postgresql://localhost/fsp_dataset_eval?dbname=fsp",
        "postgresql://localhost/fsp_dataset_eval#override",
        "dbname=fsp_dataset_eval",
    ],
)
def test_application_database_dsns_rejected(dsn):
    with pytest.raises(ValueError):
        check_dsn(dsn)


def test_dry_run_never_connects(package, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected network connection")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setenv("FSP_DATASET_EVAL_DSN", "postgresql://localhost/fsp")
    assert import_package(package) == {
        "dry_run": True,
        "records": 1973,
        "release_sha256": sha256(package / "manifest.json"),
        "target_schema": "fsp_evaluation",
        "application_tables_touched": False,
    }


def test_real_csv_dialect_and_multiline_header(tmp_path):
    p = tmp_path / "jobs.csv"
    p.write_text('jd_no\t"job_description\n"\n001\t"Python\nSQL"\n', encoding="utf-8")
    assert list(csv_rows(p, "\t")) == [
        (1, {"jd_no": "001", "job_description": "Python\nSQL"})
    ]


def test_same_size_raw_source_mutation_rejected(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    p = source / "data.csv"
    p.write_text("before")
    inventory = tmp_path / "inventory.json"
    write_json(
        inventory, {"files": [{"path": "data.csv", "bytes": 6, "sha256": sha256(p)}]}
    )
    p.write_text("after!")
    with pytest.raises(ValueError, match="Inventory/source mismatch"):
        build(tmp_path / "local", REPO, source, inventory, mode="local")


@pytest.mark.parametrize("invalid", [[], None, "not a record", {"kind": "nonexistent"}])
def test_malformed_record_rejected(changed, invalid):
    rewrite(changed / "data/synthetic/candidates.jsonl", [invalid])
    assert validate(changed, verify_manifest=False)["status"] == "failed"


def test_unallowlisted_file_rejected_even_if_rehashed(changed):
    from fsp_dataset.common import build_manifest

    (changed / "private_profiles.csv").write_text("contact,profile\nlocal,private\n")
    build_manifest(
        changed,
        mode="public",
        counts=read_json(changed / "VALIDATION_REPORT.json")["counts"],
        metadata={},
    )
    assert validate(changed)["status"] == "failed"


@pytest.mark.skipif(
    not os.environ.get("FSP_DATASET_TEST_DSN"),
    reason="Needs disposable PostgreSQL, never production",
)
def test_actual_database_import_is_transactional_and_idempotent(
    package, monkeypatch, tmp_path
):
    import psycopg

    dsn = os.environ["FSP_DATASET_TEST_DSN"]
    check_dsn(dsn)
    monkeypatch.setenv("FSP_DATASET_EVAL_DSN", dsn)
    first = import_package(package, apply=True)
    second = import_package(package, apply=True)
    assert first == second
    with psycopg.connect(dsn) as conn:
        assert (
            conn.execute("SELECT count(*) FROM fsp_evaluation.records").fetchone()[0]
            == 1973
        )
        assert (
            conn.execute("SELECT count(*) FROM fsp_evaluation.releases").fetchone()[0]
            == 1
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
            ).fetchone()[0]
            == 0
        )
    from fsp_dataset import import_db
    from fsp_dataset.common import build_manifest

    variant = tmp_path / "interrupted"
    shutil.copytree(package, variant)
    build_manifest(
        variant,
        mode="public",
        counts=read_json(variant / "VALIDATION_REPORT.json")["counts"],
        metadata={"test": "rollback"},
    )
    calls = 0
    original_records = import_db.records

    def interrupted_records(path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("Injected interruption after the first file insert")
        yield from original_records(path)

    monkeypatch.setattr(import_db, "records", interrupted_records)
    with pytest.raises(ValueError, match="Injected interruption"):
        import_package(variant, apply=True)
    with psycopg.connect(dsn) as conn:
        assert (
            conn.execute("SELECT count(*) FROM fsp_evaluation.records").fetchone()[0]
            == 1973
        )
        assert (
            conn.execute("SELECT count(*) FROM fsp_evaluation.releases").fetchone()[0]
            == 1
        )


def test_assessment_schema_detects_missing_results(changed):
    path = changed / "assessment/attempts.jsonl"
    rows = list(records(path))
    rows[0]["payload"]["application_result"] = {}
    rewrite(path, rows)
    assert validate(changed, verify_manifest=False)["status"] == "failed"


def test_ranker_does_not_read_reference_labels(package, tmp_path):
    from fsp_dataset.evaluate import evaluate

    root = tmp_path / "independence"
    shutil.copytree(package, root)
    before, predictions_before = evaluate(root)
    path = root / "labels/matching.jsonl"
    rows = list(records(path))
    for row in rows:
        row["payload"]["decision"] = "reject"
        row["payload"]["relevance"] = 0
    rewrite(path, rows)
    after, predictions_after = evaluate(root)
    assert predictions_before == predictions_after
    assert before["summary"] != after["summary"]


def test_duplicate_careercorpus_source_ids_preserve_both_rows(tmp_path):
    from fsp_dataset.common import Writer
    from fsp_dataset.external import auxiliary

    sources = tmp_path / "inputs/raw_sources"
    (sources / "talentclef").mkdir(parents=True)
    (sources / "careercorpus").mkdir()
    for task in ["A", "B"]:
        prefix = "validation/english/" if task == "A" else "validation/"
        with zipfile.ZipFile(sources / f"talentclef/Task{task}.zip", "w") as z:
            z.writestr(prefix + "queries", "q_id\tjobtitle\nq1\tPython\n")
            z.writestr(prefix + "corpus_elements", "c_id\tjobtitle\nc1\tPython\n")
            z.writestr(prefix + "qrels.tsv", "q1\t0\tc1\t1\n")
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with zipfile.ZipFile(sources / "careercorpus/CareerCorpus.xlsx", "w") as z:
        z.writestr(
            "xl/sharedStrings.xml",
            f'<sst xmlns="{ns}"><si><t>ID</t></si><si><t>Domain</t></si><si><t>Design</t></si></sst>',
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{ns}"><sheetData>'
            '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
            '<row r="2"><c r="A2"><v>3.5421497E7</v></c><c r="B2" t="s"><v>2</v></c></row>'
            '<row r="3"><c r="A3"><v>3.5421497E7</v></c><c r="B3" t="s"><v>2</v></c></row>'
            "</sheetData></worksheet>",
        )
    out = tmp_path / "output"
    writer = Writer(out)
    try:
        report = auxiliary(writer, tmp_path / "inputs")
    finally:
        writer.close()
    rows = list(records(out / "data/auxiliary/careercorpus.jsonl"))
    assert len(rows) == 2 and rows[0]["record_id"] != rows[1]["record_id"]
    assert all(r["payload"]["original_values"]["ID"] == "3.5421497E7" for r in rows)
    assert report["CareerCorpus"]["duplicate_id_extra_rows"] == 1


def test_fractional_assessment_scores_are_retained(package):
    rows = list(records(package / 'assessment/attempts.jsonl'))
    scores = [r['payload']['application_result']['score'] for r in rows]
    assert any(score == 87.5 for score in scores)
    assert validate(package)['status'] == 'passed'

import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import VERSION
from . import assessment, external, synthetic
from .catalog import SOURCES, sources_markdown
from .common import Writer, build_manifest, read_json, safe_relative, sha256, write_json
from .evaluate import evaluate
from .schema import PAYLOADS, schema_for
from .validate import validate


def copy_file(source, target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def build(
    root,
    repo,
    source_root=None,
    inventory_path=None,
    mode="public",
    seed=20261008,
    scan_limit=100000,
    workflow_report=None,
):
    root, repo = Path(root), Path(repo)
    if mode not in ["public", "local"]:
        raise ValueError("Unknown package mode")
    if scan_limit < 1:
        raise ValueError("scan_limit must be positive")
    if root.exists():
        raise ValueError("Output exists; select a new output directory")
    root.mkdir(parents=True)
    snapshot = [
        ("apps/api/fsp/bank.py", "snapshot/mvp/bank.py"),
        ("apps/api/fsp/matching.py", "snapshot/mvp/matching.py"),
        ("evaluation/oracles.py", "snapshot/oracles.py"),
    ]
    hashes = {}
    for original, target in snapshot:
        copy_file(repo / original, root / target)
        hashes[original] = sha256(repo / original)
    (root / "snapshot/mvp/__init__.py").write_text(
        "# Pure MVP snapshot; no API/database.\n"
    )
    for p in sorted((repo / "dataset/fsp_dataset").glob("*.py")):
        copy_file(p, root / "fsp_dataset" / p.name)
    for name in [
        "run.py",
        "requirements.lock.txt",
        "requirements-import.txt",
        "README.md",
        "DATASET_CARD.md",
        "ANNOTATION_GUIDE.md",
        "REQUIREMENTS_TRACEABILITY.md",
        "MVP_COMPATIBILITY.md",
    ]:
        copy_file(repo / "dataset" / name, root / name)
    copy_file(repo / "LICENSE", root / "LICENSES/OWN_MIT.txt")
    write_json(root / "sources.json", SOURCES)
    (root / "SOURCES.md").write_text(sources_markdown())
    for kind in PAYLOADS:
        write_json(root / f"schemas/{kind}.json", schema_for(kind))
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()
    except subprocess.CalledProcessError:
        commit = None
    write_json(
        root / "package.json",
        {
            "version": VERSION,
            "mode": mode,
            "seed": seed,
            "source_commit": commit,
            "snapshot_sha256": hashes,
            "build_code_sha256": {
                p.name: sha256(p) for p in sorted((root / "fsp_dataset").glob("*.py"))
            },
            "external_models_used": [],
            "external_api_calls": 0,
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        },
    )
    writer = Writer(root)
    try:
        synthetic.generate(writer, seed)
        synthetic.workflow(writer)
        assessment_result = assessment.generate(writer, root, seed)
        if mode == "local":
            if not source_root or not inventory_path:
                raise ValueError("Local build requires source root and inventory")
            inv = read_json(inventory_path)
            print("Verifying raw source hashes", flush=True)
            stamps = {}
            for item in inv["files"]:
                p = safe_relative(Path(source_root), item["path"])
                before = p.stat()
                if (
                    not p.is_file()
                    or p.stat().st_size != item["bytes"]
                    or sha256(p) != item["sha256"]
                ):
                    raise ValueError("Inventory/source mismatch: " + item["path"])
                stamps[p] = (before.st_size, before.st_mtime_ns)
            write_json(root / "input_inventory.json", inv)
            print("Building Tianchi local extension", flush=True)
            write_json(
                root / "reports/tianchi.json", external.tianchi(writer, source_root)
            )
            print("Building bounded Trudvsem selection", flush=True)
            write_json(
                root / "reports/trudvsem.json",
                external.trudvsem(writer, source_root, scan_limit),
            )
            print("Preserving auxiliary source labels", flush=True)
            write_json(
                root / "reports/auxiliary.json", external.auxiliary(writer, source_root)
            )
            for p, stamp in stamps.items():
                after = p.stat()
                if stamp != (after.st_size, after.st_mtime_ns):
                    raise ValueError("Input changed during build")
    finally:
        writer.close()
    write_json(root / "reports/assessment.json", assessment_result)
    matching_result, predictions = evaluate(root)
    write_json(root / "reports/matching.json", matching_result)
    write_json(root / "reports/predictions.json", predictions)
    # Recorded test results are evidence only; scenarios remain specifications.
    if workflow_report:
        copy_file(workflow_report, root / "reports/workflow-tests.json")
    else:
        write_json(
            root / "reports/workflow-tests.json",
            {
                "status": "not_run",
                "reason": "Requires isolated test DB; offline bundle never connects to it",
            },
        )
    splits = {
        "matching": {
            "unit": "candidate and need IDs",
            "seed": seed,
            "policy": "disjoint entities; shared scenario families; no training or parameter tuning in builder",
        },
        "assessment": {
            "unit": "variant",
            "dev": "0..3",
            "test": "4..19",
            "repeated_personas_intentional": True,
        },
        "external": {
            "policy": "legacy split recorded as metadata; no new independent holdout claimed"
        },
    }
    write_json(root / "splits.json", splits)
    passport = {
        "structural_validation_status": "pending",
        "provenance_status": "linked_to_sources_and_hashes",
        "rights_review_status": (
            "own_synthetic_only" if mode == "public" else "mixed_sources_local_only"
        ),
        "privacy_review_status": (
            "synthetic_data_only" if mode == "public" else "pending_no_public_export"
        ),
        "human_reviewed_new_pairs": 0,
        "human_review_status": "not_performed_not_required_for_synthetic_scope",
        "assessment_validation_status": "synthetic_simulation_only",
        "application_evaluation_status": "pure_functions_measured",
        "external_certification_status": "not_certified",
        "issuer": None,
        "certification_document_ref": None,
        "deepseek_used": False,
        "real_professional_validity": "not_established",
    }
    write_json(root / "AUDIT_PASSPORT.json", passport)
    report = validate(root, verify_manifest=False)
    if report["status"] != "passed":
        raise ValueError("Validation failed: " + "; ".join(report["errors"][:6]))
    passport["structural_validation_status"] = "passed"
    write_json(root / "AUDIT_PASSPORT.json", passport)
    write_json(root / "VALIDATION_REPORT.json", report)
    (root / "VALIDATION_REPORT.md").write_text(
        "# Результат проверки структуры\n\nСтатус: passed. Записей: "
        + str(report["records"])
        + ".\n\nПроверены схемы, ID, ссылки, происхождение, пулы, разметка, разделение сущностей "
        "matching dev/test и ограничения публичного экспорта. После фиксации манифеста "
        "команда validate дополнительно сверяет все SHA-256 без изменения файлов.\n\n"
        "Метрики приложения находятся в reports/matching.json; ошибки ранжирования "
        "сохранены. Симуляция тестов — reports/assessment.json. Исходные внешние метки "
        "не подтверждают профессиональную пригодность. Содержательное чтение всех "
        "40 ГБ исходных данных не заявляется.\n"
    )
    build_manifest(root, mode=mode, counts=writer.counts, metadata={"seed": seed})
    verified = validate(root)
    if verified["status"] != "passed":
        raise ValueError(
            "Frozen manifest validation failed: " + str(verified["errors"])
        )
    return {
        "status": "built",
        "mode": mode,
        "records": report["records"],
        "counts": writer.counts,
        "manifest_sha256": sha256(root / "manifest.json"),
    }

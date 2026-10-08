#!/usr/bin/env python3
"""Offline entry point. Deliberately does not load .env or any API key."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
os.umask(0o077)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("--source-root", type=Path, default=Path(__file__).parent)
    inv.add_argument("--out", type=Path, required=True)
    build = sub.add_parser("build")
    build.add_argument("--mode", choices=["public", "local"], required=True)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parent.parent
    )
    build.add_argument("--source-root", type=Path, default=Path(__file__).parent)
    build.add_argument("--inventory", type=Path)
    build.add_argument("--seed", type=int, default=20261008)
    build.add_argument("--scan-limit", type=int, default=100000)
    build.add_argument("--workflow-report", type=Path)
    check = sub.add_parser("validate")
    check.add_argument("--root", type=Path, required=True)
    pack = sub.add_parser("release")
    pack.add_argument("--root", type=Path, required=True)
    pack.add_argument("--mode", choices=["public", "local"], required=True)
    pack.add_argument("--out", type=Path, required=True)
    imp = sub.add_parser("import-db")
    imp.add_argument("--root", type=Path, required=True)
    action = imp.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true")
    action.add_argument("--dry-run", action="store_true")
    imp.add_argument("--dsn-env", default="FSP_DATASET_EVAL_DSN")
    for name in ["evaluate", "evaluate-assessment"]:
        evaluate = sub.add_parser(name)
        evaluate.add_argument("--root", type=Path, required=True)
        evaluate.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    from fsp_dataset.common import write_json

    if args.command == "inventory":
        from fsp_dataset.inventory import inventory

        result = inventory(args.source_root)
        write_json(args.out, result)
        result = {"files": len(result["files"]), "status": "hashed"}
    elif args.command == "build":
        from fsp_dataset.build import build

        result = build(
            args.out,
            args.repo,
            args.source_root,
            args.inventory,
            args.mode,
            args.seed,
            args.scan_limit,
            args.workflow_report,
        )
    elif args.command == "validate":
        from fsp_dataset.validate import validate

        result = validate(args.root)
    elif args.command == "release":
        from fsp_dataset.release import release

        result = release(args.root, args.out, args.mode)
    elif args.command == "import-db":
        from fsp_dataset.import_db import import_package

        result = import_package(args.root, args.apply, args.dsn_env)
    else:
        from fsp_dataset.evaluate import evaluate
        from fsp_dataset.validate import validate

        if (
            args.root.resolve() == args.out.resolve()
            or args.root.resolve() in args.out.resolve().parents
        ):
            raise ValueError("Evaluation output must be outside the frozen package")
        if validate(args.root)["status"] != "passed":
            raise ValueError("Invalid input package")
        if args.command == "evaluate":
            result, predictions = evaluate(args.root)
            write_json(args.out, {"report": result, "predictions": predictions})
        else:
            import tempfile
            from fsp_dataset.assessment import generate
            from fsp_dataset.common import Writer, read_json, sha256

            with tempfile.TemporaryDirectory(prefix="fsp-assessment-") as temporary:
                writer = Writer(temporary)
                try:
                    report = generate(
                        writer, args.root, read_json(args.root / "package.json")["seed"]
                    )
                finally:
                    writer.close()
                same = sha256(Path(temporary) / "assessment/attempts.jsonl") == sha256(
                    args.root / "assessment/attempts.jsonl"
                )
            result = {
                "status": (
                    "passed" if same and not report["oracle_errors"] else "failed"
                ),
                "attempt_records_identical": same,
                "report": report,
            }
            write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("status") == "failed" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

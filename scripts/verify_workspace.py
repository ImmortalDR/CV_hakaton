#!/usr/bin/env python3
"""Verify this packet's paths and bytes; does not inspect application correctness."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument(
        "--inputs-only",
        action="store_true",
        help="Check preserved source inputs; exclude editable project instructions/scripts",
    )
    args = ap.parse_args()
    root = args.root.resolve()
    manifest = root / "MANIFEST.sha256"
    if not manifest.is_file():
        raise SystemExit(f"Missing packet manifest: {manifest}")
    failures = []
    checked = 0
    skipped = 0
    remapped = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            failures.append({"path": name, "error": "unsafe path"})
            continue
        source_roots = {
            "Архив исходников для MVP обратного найма ФСП",
            "transcription",
            "ФСП спец. трек ТЗ-1.pdf",
            "ЛЦТ_2026_Шаблон презентации ФСП(1).pptx",
        }
        if args.inputs_only and relative.parts[0] not in source_roots:
            skipped += 1
            continue
        p = root / name
        # The provided extraction has one extra archive directory level.
        if (
            not p.exists()
            and relative.parts[0] == "Архив исходников для MVP обратного найма ФСП"
        ):
            nested = (
                root / relative.parts[0] / "fsp_mvp_bundle" / Path(*relative.parts[1:])
            )
            if nested.is_file():
                p = nested
                remapped += 1
        if not p.is_file() or p.is_symlink():
            failures.append({"path": name, "error": "missing or symlink"})
            continue
        with p.open("rb") as f:
            actual = hashlib.file_digest(f, "sha256").hexdigest()
        checked += 1
        if actual != expected:
            failures.append({"path": name, "error": "changed bytes"})
    print(
        json.dumps(
            {
                "root": str(root),
                "checked_files": checked,
                "skipped_mutable_project_files": skipped,
                "remapped_archive_paths": remapped,
                "failures": failures,
                "ok": not failures,
                "scope": "packet integrity only; not application tests",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

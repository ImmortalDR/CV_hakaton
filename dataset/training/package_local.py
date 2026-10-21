"""Allowlisted local-only training handoff; never a public data release."""

from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if (
            len(names) != len(set(names))
            or sum(i.file_size for i in z.infolist()) > 256 * 1024 * 1024
        ):
            raise ValueError("Duplicate names or excessive expanded size")
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts or "\\" in name:
                raise ValueError("Unsafe archive path")
        m = json.loads(z.read("MANIFEST.json"))
        if m["mode"] != "local_only" or set(names) != set(m["files"]) | {
            "MANIFEST.json"
        }:
            raise ValueError("Invalid release scope")
        for name, entry in m["files"].items():
            data = z.read(name)
            if len(data) != entry["bytes"] or sha(data) != entry["sha256"]:
                raise ValueError("Checksum mismatch: " + name)
    return {
        "mode": "local_only",
        "verification": "passed",
        "files": len(names),
        "bytes": path.stat().st_size,
        "sha256": sha(path.read_bytes()),
    }


def package(repo, out):
    os.umask(0o077)
    paths = {}
    for name in (
        "prepare.py",
        "pairs.py",
        "application_pairs.py",
        "train.py",
        "package_local.py",
        "requirements.lock.txt",
    ):
        paths["pipeline/" + name] = repo / "dataset/training" / name
    for name in ("README.md", "EXPERIMENT.md", "RESULTS.md"):
        paths["docs/" + name] = repo / "dataset/training" / name
    paths["LICENSE"] = repo / "LICENSE"
    for name in ("replay.json", "input-continuity.json", "checks.json"):
        paths["reports/" + name] = repo / "dataset/training/reports" / name
    for v, data_dir in [
        ("v1", "trudvsem-training-v1"),
        ("v2", "trudvsem-decisions-v2"),
    ]:
        for name in ("pairs.jsonl", "pairs-report.json", "scan.json"):
            paths[f"data/{v}/{name}"] = repo / "dataset/builds" / data_dir / name
        model_dir = repo / "dataset/builds" / ("trudvsem-model-" + v)
        for name in (
            "model.joblib",
            "split-manifest.json",
            "training-report.json",
            "test-predictions.jsonl",
        ):
            paths[f"models/{v}/{name}"] = model_dir / name
        report = json.loads((model_dir / "training-report.json").read_text())
        if sha((model_dir / "model.joblib").read_bytes()) != report["model_sha256"]:
            raise ValueError("Model differs from measured artifact")
        if (
            sha((repo / "dataset/builds" / data_dir / "pairs.jsonl").read_bytes())
            != report["pairs_sha256"]
        ):
            raise ValueError("Pairs differ from measured input")
    payload = {}
    for name, p in paths.items():
        if p.is_symlink():
            raise ValueError("Symlink input forbidden")
        payload[name] = p.read_bytes()
    replacements = {
        "reports/scan.json": "../data/v1/scan.json",
        "reports/input-continuity.json": "../reports/input-continuity.json",
        "reports/v1-pairs.json": "../data/v1/pairs-report.json",
        "reports/v2-pairs.json": "../data/v2/pairs-report.json",
        "reports/v1-training.json": "../models/v1/training-report.json",
        "reports/v2-training.json": "../models/v2/training-report.json",
        "reports/replay.json": "../reports/replay.json",
        "reports/local-release.json": "../MANIFEST.json",
    }
    rendered = payload["docs/RESULTS.md"].decode()
    for original, bundled in replacements.items():
        rendered = rendered.replace(original, bundled)
    payload["docs/RESULTS.md"] = rendered.encode()
    payload["LOCAL_ONLY.txt"] = (
        "PRIVATE LOCAL HANDOFF. Contains real professional profile texts and derived model weights.\n"
        "Do not upload this archive to public GitHub. No expert certification or verified grades.\n"
        "Source and rights: https://data.rcsi.science/data-catalog/datasets/186/ (CC BY-SA).\n"
        "The root LICENSE covers our code; it does not relicense third-party data.\n"
        "Verify ZIP: python pipeline/package_local.py --verify /path/to/archive.zip\n"
        "Create a Python 3.12 environment, install pipeline/requirements.lock.txt; then run:\n"
        "python pipeline/train.py predict --model models/v2/model.joblib "
        "--candidate-file /path/candidate.txt --need-file /path/need.txt\n"
        "docs/README.md describes paths in the original repository for rebuilding from raw sources.\n"
        "Hashes check integrity, not independent authenticity or professional validity.\n"
    ).encode()
    manifest = {
        "version": 1,
        "mode": "local_only",
        "raw_source_files_included": False,
        "files": {
            name: {"bytes": len(data), "sha256": sha(data)}
            for name, data in sorted(payload.items())
        },
    }
    payload["MANIFEST.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    ).encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        out, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as z:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return verify(out)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--out", type=Path)
    g.add_argument("--verify", type=Path)
    a = p.parse_args()
    print(
        json.dumps(verify(a.verify) if a.verify else package(a.repo, a.out), indent=2)
    )

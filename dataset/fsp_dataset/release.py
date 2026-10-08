import os
import zipfile
from pathlib import Path

from .common import read_json, safe_relative, sha256
from .validate import validate


def release(root, output, mode):
    root, output = Path(root), Path(output)
    manifest = read_json(root / "manifest.json")
    if manifest["mode"] != mode:
        raise ValueError("Local research data cannot be exported as public")
    result = validate(root)
    if result["status"] != "passed":
        raise ValueError("Package validation failed; export denied")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError("Archive already exists; refusing to overwrite")
    names = sorted(
        [e["path"] for e in manifest["files"]] + ["manifest.json", "checksums.sha256"]
    )
    try:
        with zipfile.ZipFile(
            output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as z:
            for name in names:
                path = safe_relative(root, name)
                info = zipfile.ZipInfo(
                    "fsp-eval-1.0.0-" + mode + "/" + name,
                    date_time=(2026, 10, 8, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100644 if mode == "public" else 0o100600) << 16
                with path.open("rb") as src, z.open(
                    info, "w", force_zip64=True
                ) as dest:
                    for chunk in iter(lambda: src.read(1024 * 1024), b""):
                        dest.write(chunk)
        output.chmod(0o600 if mode == "local" else 0o644)
    except Exception:
        # Only our newly-created incomplete archive, never existing source data.
        output.unlink(missing_ok=True)
        raise
    digest = sha256(output)
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.name}\n"
    )
    return {
        "status": "created",
        "mode": mode,
        "sha256": digest,
        "bytes": output.stat().st_size,
        "files": len(names),
    }

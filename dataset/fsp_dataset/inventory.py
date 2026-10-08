from pathlib import Path, PurePosixPath
import zipfile

from .common import sha256


def inventory(root, progress=print):
    root = Path(root)
    inputs = sorted((root / "raw_sources").rglob("*"))
    inputs += sorted(root.glob("*.zip"))
    results = []
    for p in inputs:
        if p.is_symlink():
            raise ValueError("Input symlinks are not accepted")
        if not p.is_file():
            continue
        relative = p.relative_to(root).as_posix()
        progress("Hashing " + relative, flush=True)
        before = p.stat()
        digest = sha256(p)
        after = p.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("Input changed during inventory")
        item = {
            "path": relative,
            "sha256": digest,
            "bytes": after.st_size,
            "content_review": "not_full_read",
            "automatic_check": "byte_hash",
        }
        if p.suffix in [".zip", ".xlsx"]:
            with zipfile.ZipFile(p) as z:
                members = []
                for e in z.infolist():
                    path = PurePosixPath(e.filename)
                    if path.is_absolute() or ".." in path.parts or "\\" in e.filename:
                        raise ValueError("Unsafe archive member")
                    members.append({"path": e.filename, "bytes": e.file_size})
                item["archive_members"] = members
                item["archive_crc_status"] = "not_run"
        results.append(item)
    return {
        "version": "1.0",
        "files": results,
        "scope": "Full byte hashing and archive directory inspection; not full semantic reading",
    }

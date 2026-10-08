import csv
import hashlib
import json
from pathlib import Path


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def records(path):
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def csv_rows(path, delimiter=","):
    csv.field_size_limit(8 * 1024 * 1024)
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        r = csv.reader(f, delimiter=delimiter, strict=True)
        fields = [s.strip() for s in next(r)]
        if len(fields) != len(set(fields)):
            raise ValueError("Duplicate normalized CSV headers")
        for ordinal, values in enumerate(r, 1):
            if len(values) != len(fields):
                raise ValueError(f"Unexpected CSV width at record {ordinal}")
            yield ordinal, dict(zip(fields, values))


def safe_relative(root, relative):
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise ValueError("Unsafe relative path")
    root = Path(root).resolve()
    target = root / p
    if target.is_symlink() or root not in target.resolve().parents:
        raise ValueError("Path escapes package or is a symlink")
    if any((root / Path(*p.parts[:i])).is_symlink() for i in range(1, len(p.parts))):
        raise ValueError("Symlink directory is not allowed")
    return target


def source_ref(source_id, file, locator):
    return {"source_id": source_id, "file": file, "locator": str(locator)}


def record(
    kind,
    rid,
    track,
    payload,
    *,
    split="external",
    origin="adapted",
    label_origin="none",
    refs=None,
):
    return {
        "schema_version": "1.0",
        "kind": kind,
        "record_id": rid,
        "track": track,
        "split": split,
        "data_origin": origin,
        "label_origin": label_origin,
        "source_refs": refs or [],
        "payload": payload,
    }


class Writer:
    def __init__(self, root):
        self.root, self.handles, self.counts = Path(root), {}, {}

    def add(self, relative, value):
        if relative not in self.handles:
            path = safe_relative(self.root, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.handles[relative] = path.open("w", encoding="utf-8")
            self.counts[relative] = 0
        self.handles[relative].write(dumps(value) + "\n")
        self.counts[relative] += 1

    def close(self):
        for h in self.handles.values():
            h.close()


def build_manifest(root, *, mode, counts, metadata):
    root = Path(root)
    entries = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name in ("manifest.json", "checksums.sha256"):
            continue
        relative = p.relative_to(root).as_posix()
        safe_relative(root, relative)
        entries.append(
            {
                "path": relative,
                "sha256": sha256(p),
                "bytes": p.stat().st_size,
                "records": counts.get(relative),
                "public_allowed": mode == "public",
            }
        )
    write_json(
        root / "manifest.json",
        {
            "schema_version": "1.0",
            "version": "1.0.0",
            "mode": mode,
            "files": entries,
            **metadata,
        },
    )
    targets = [e["path"] for e in entries] + ["manifest.json"]
    (root / "checksums.sha256").write_text(
        "".join(f"{sha256(root / name)}  {name}\n" for name in sorted(targets)),
        encoding="utf-8",
    )

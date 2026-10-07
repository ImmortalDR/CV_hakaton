#!/usr/bin/env python3
"""Verify this packet's paths and bytes; does not inspect application correctness."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()
    root = args.root.resolve()
    manifest = root / 'MANIFEST.sha256'
    if not manifest.is_file():
        raise SystemExit(f'Missing packet manifest: {manifest}')
    failures = []
    checked = 0
    for line in manifest.read_text(encoding='utf-8').splitlines():
        expected, name = line.split('  ', 1)
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts:
            failures.append({'path': name, 'error': 'unsafe path'})
            continue
        p = root / name
        if not p.is_file() or p.is_symlink():
            failures.append({'path': name, 'error': 'missing or symlink'})
            continue
        with p.open('rb') as f:
            actual = hashlib.file_digest(f, 'sha256').hexdigest()
        checked += 1
        if actual != expected:
            failures.append({'path': name, 'error': 'changed bytes'})
    print(json.dumps({'root': str(root), 'checked_files': checked,
                      'failures': failures, 'ok': not failures,
                      'scope': 'packet integrity only; not application tests'},
                     ensure_ascii=False, indent=2))
    return 1 if failures else 0

if __name__ == '__main__':
    raise SystemExit(main())

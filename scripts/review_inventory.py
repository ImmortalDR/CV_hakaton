#!/usr/bin/env python3
"""Inventory bytes and merge explicit reading notes. Never infer read from a scan."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__',
                  '.pytest_cache', '.cache', 'tmp'}
EXCLUDED_PREFIXES = ('audit/current/', 'docs/review/')
STATUSES = {'read', 'inspected_binary', 'duplicate_of', 'not_read', 'blocked'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    args = ap.parse_args()
    root = args.root.resolve()
    out = root / 'docs/review'
    out.mkdir(parents=True, exist_ok=True)
    notes = json.loads((out / 'reading_log.json').read_text())
    records = []
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if not p.is_file() or any(x in EXCLUDED_PARTS for x in rel.parts):
            continue
        name = rel.as_posix()
        if name.startswith(EXCLUDED_PREFIXES):
            continue
        raw = p.read_bytes()
        kind = 'text'
        try:
            text = raw.decode('utf-8-sig')
            if '\0' in text:
                kind = 'binary'
        except UnicodeError:
            kind = 'binary'
        records.append({'path': name, 'kind': kind, 'bytes': len(raw),
                        'sha256': hashlib.sha256(raw).hexdigest()})

    fields = ['path', 'kind'] + [f'pass{i}_{s}' for i in range(1, 4)
                                for s in ('status', 'note')]
    rows = []
    for rec in records:
        row = {k: rec[k] for k in ('path', 'kind')}
        for i in range(1, 4):
            own = notes.get(rec['path'], {})
            status = own.get(f'pass{i}_status', 'not_read')
            note = own.get(f'pass{i}_note', 'Содержательный проход не выполнен.')
            if status not in STATUSES:
                raise ValueError((rec['path'], status))
            row[f'pass{i}_status'] = status
            row[f'pass{i}_note'] = note
        rows.append(row)

    # Only duplicates of substantively reviewed files inherit review coverage.
    for i in range(1, 4):
        reviewed = {}
        for rec, row in zip(records, rows):
            if row[f'pass{i}_status'] in ('read', 'inspected_binary'):
                reviewed.setdefault(rec['sha256'], row)
        for rec, row in zip(records, rows):
            source = reviewed.get(rec['sha256'])
            if row[f'pass{i}_status'] == 'not_read' and source:
                row[f'pass{i}_status'] = 'duplicate_of'
                row[f'pass{i}_note'] = (f"SHA-256 идентичен {source['path']}. "
                                         + source[f'pass{i}_note'])
    with (out / 'coverage.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with (out / 'inventory.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['path', 'kind', 'bytes', 'sha256'])
        writer.writeheader()
        writer.writerows(records)
    summary = {'files': len(records), 'unique_sha256': len({r['sha256'] for r in records}),
               'passes': {i: dict(Counter(r[f'pass{i}_status'] for r in rows))
                          for i in range(1, 4)},
               'excluded_parts': sorted(EXCLUDED_PARTS),
               'excluded_generated_outputs': EXCLUDED_PREFIXES,
               'warning': 'Опись и хеши не являются содержательным чтением.'}
    (out / 'coverage_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

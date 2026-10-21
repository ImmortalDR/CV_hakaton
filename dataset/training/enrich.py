"""Dated work/education extraction and anchored expansion of real application pairs."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from application_pairs import LABELS, decision_reason
from pairs import Union, asof, SEED
from prepare import clean, csv_rows, digest, valid_date, write_json


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def read_jsonl(path):
    with Path(path).open() as f:
        return [json.loads(line) for line in f]


def connect(root):
    db = sqlite3.connect(f'file:{root / "index.sqlite"}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db


def index(source, root, out):
    """Each completed file is checkpointed; partial derived files can be restarted."""
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'complete.json').exists():
        raise FileExistsError('Enrichment index is frozen')
    scan = json.loads((root / 'scan.json').read_text())
    with connect(root) as db:
        wanted = {r[0] for r in db.execute('SELECT DISTINCT id FROM cvs')}
        apps = {r['rownum']: dict(r) for r in db.execute('SELECT * FROM applications')}
    inputs = {}
    for filename in ('workexp.csv', 'edu.csv', 'invitations.csv'):
        output = out / (filename + '.jsonl')
        metadata = out / (filename + '.json')
        if metadata.exists():
            saved = json.loads(metadata.read_text())
            if (file_hash(source / filename) != saved['input']['sha256']
                    or file_hash(output) != saved['output_sha256']):
                raise ValueError('Checkpoint input/output changed')
            inputs[filename] = saved
            continue
        counts = Counter()
        temporary = output.with_suffix('.partial')
        report = {}
        with temporary.open('w') as f:
            for n, header, values in csv_rows(source / filename, report):
                # Avoid creating millions of dicts for unrelated CVs.
                if filename == 'invitations.csv':
                    if n not in apps:
                        continue
                    r = dict(zip(header, values))
                    a = apps[n]
                    if r['id_invitation'] != a['eid'] or r['id_reply'] != a['reply']:
                        raise ValueError('Application index/source mismatch')
                    record = {'rownum': n, 'created': valid_date(r['date_creation'])
                              if r['date_creation_mistake'] in ('', '0') else ''}
                else:
                    if values[header.index('id_cv')] not in wanted:
                        continue
                    r = dict(zip(header, values))
                    counts['selected_source_rows'] += 1
                    day = valid_date(r['date_last_updated'])
                    if not day:
                        counts['invalid_publication_date'] += 1
                        continue
                    if filename == 'workexp.csv':
                        start = valid_date(r['date_from'])
                        end = valid_date(r['date_to']) if r['date_to'] else ''
                        if (r['date_mistake'] not in ('', '0') or not start
                                or start > day or (r['date_to'] and not end)
                                or (end and end < start)):
                            counts['invalid_work_dates'] += 1
                            continue
                        key = digest('|'.join(clean(r[k]) for k in
                                              ('company_name', 'job_title', 'date_from')))
                        text = clean(' '.join(r[k] for k in ('job_title', 'demands', 'achievements')))
                        extra = {'start': start, 'end': end}
                    else:
                        year = r['graduate_year']
                        if r['grad_year_mistake'] not in ('', '0') or not year.isdigit():
                            counts['invalid_education_year'] += 1
                            continue
                        year = int(year)
                        if year < 1900 or year > 2100:
                            counts['invalid_education_year'] += 1
                            continue
                        key = digest('|'.join(clean(r[k]) for k in
                                              ('legal_name', 'speciality', 'qualification')))
                        text = clean(' '.join(r[k] for k in ('speciality', 'qualification', 'faculty')))
                        extra = {'graduate_year': year}
                    if not text:
                        counts['empty_professional_text'] += 1
                        continue
                    record = {'cv': r['id_cv'], 'day': day, 'key': key, 'text': text,
                              'rownum': n, **extra}
                counts['stored'] += 1
                f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
        if filename == 'invitations.csv' and report[filename] != scan['inputs'][filename]:
            raise ValueError('Applications differ from frozen source')
        temporary.replace(output)
        saved = {'input': report[filename], 'counts': dict(counts),
                 'output_sha256': file_hash(output)}
        write_json(metadata, saved)
        inputs[filename] = saved
        print(json.dumps({'stage': filename, 'counts': dict(counts)}, ensure_ascii=False), flush=True)
    write_json(out / 'complete.json', {
        'inputs': inputs, 'wanted_cvs': len(wanted),
        'base_scan_sha256': file_hash(root / 'scan.json'),
        'base_index_sha256': file_hash(root / 'index.sqlite'),
        'code_sha256': file_hash(Path(__file__)),
    })


def history_asof(rows, day, kind):
    """Latest unambiguous version per approximate entity; no future graduation."""
    grouped = defaultdict(list)
    for r in rows:
        if r['day'] >= day:
            continue
        if kind == 'work' and r['start'] >= day:
            continue
        if kind == 'edu' and r['graduate_year'] >= int(day[:4]):
            continue
        # Contact cleanup can remove ISO dates from a textual key. Preserve the
        # typed start date explicitly: two tenures at the same role are distinct.
        entity = (r['key'], r['start']) if kind == 'work' else (r['key'],)
        grouped[entity].append(r)
    picked = []
    ambiguous = 0
    for versions in grouped.values():
        latest = max(r['day'] for r in versions)
        latest_rows = [r for r in versions if r['day'] == latest]
        sig = lambda r: (r['text'], r.get('start'), r.get('end'), r.get('graduate_year'))
        if len({sig(r) for r in latest_rows}) != 1:
            ambiguous += 1
            continue
        picked.append(min(latest_rows, key=lambda r: r['rownum']))
    # Most recent experience first. Repeated texts contribute only once.
    unique = {}
    for r in sorted(picked, key=lambda r: (r.get('start', ''), r['day'], -r['rownum']), reverse=True):
        unique.setdefault(r['text'], r)
    return list(unique.values()), ambiguous


def anchored_split(rows, anchors):
    """Never move a previously used V2 entity to another split."""
    u = Union()

    def keys(p):
        result = ['person:' + p['person_id'], 'cv:' + p['cv_id'], 'job:' + p['job_id'],
                  'jt:' + digest(p['need_text'])]
        for field in ('candidate_text', 'candidate_base_text'):
            # A recovered title shorter than V2's minimum is not a copied CV.
            if len(p.get(field, '')) >= 30:
                result.append('ct:' + digest(p[field]))
        return result

    # Anchors include all V2 rows, even those lost by new source filters.
    for p in rows + anchors:
        ks = keys(p)
        for k in ks[1:]:
            u.join(ks[0], k)
    assigned = defaultdict(set)
    for p in anchors:
        assigned[u.root('person:' + p['person_id'])].add(p['split'])
    retained = []
    dropped = 0
    for p in rows:
        group = u.root('person:' + p['person_id'])
        old = assigned[group]
        if len(old) > 1:
            dropped += 1
            continue
        bucket = int(digest(SEED + group)[:8], 16) / 2**32
        p['split'] = next(iter(old)) if old else ('train' if bucket < .7 else 'validation' if bucket < .85 else 'test')
        p['group_id'] = digest(group)
        retained.append(p)
    return retained, dropped


def build(root, enrichment, anchors, out):
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=False)
    meta = json.loads((enrichment / 'complete.json').read_text())
    if file_hash(root / 'index.sqlite') != meta['base_index_sha256']:
        raise ValueError('Base index changed')
    for filename, info in meta['inputs'].items():
        if file_hash(enrichment / (filename + '.jsonl')) != info['output_sha256']:
            raise ValueError('Enrichment checkpoint changed')
    histories = {}
    for filename in ('workexp.csv', 'edu.csv'):
        grouped = defaultdict(list)
        for r in read_jsonl(enrichment / (filename + '.jsonl')):
            grouped[r['cv']].append(r)
        histories[filename] = grouped
    created = {r['rownum']: r['created'] for r in read_jsonl(enrichment / 'invitations.csv.jsonl')}
    db = connect(root)
    jobs, cvs = defaultdict(list), defaultdict(list)
    for r in db.execute('SELECT j.* FROM jobs j JOIN (SELECT DISTINCT id FROM jobs WHERE is_it=1) i ON j.id=i.id'):
        jobs[r['id']].append(dict(r))
    for r in db.execute('SELECT * FROM cvs'):
        cvs[r['id']].append(dict(r))
    counts = Counter()
    linked = []
    for a in map(dict, db.execute('SELECT * FROM applications')):
        counts['applications'] += 1
        if not a['reply']:
            counts['no_reply_unknown'] += 1
            continue
        events = list(map(dict, db.execute('SELECT * FROM events WHERE eid=?', (a['reply'],))))
        if len(events) != 1:
            counts['ambiguous_reply'] += 1
            continue
        e = events[0]
        day = created[a['rownum']]
        reason = decision_reason(e, a, day)
        if reason:
            counts[reason] += 1
            continue
        linked.append((e, a, day))
    labels = defaultdict(set)
    for e, a, day in linked:
        labels[(e['cv'], e['job'])].add(LABELS[e['kind']])
    grouped = defaultdict(list)
    for e, a, day in linked:
        if len(labels[(e['cv'], e['job'])]) > 1:
            counts['conflicting_closed_pair_histories'] += 1
            continue
        j, reason = asof(jobs[e['job']], day)
        if reason:
            counts['job_' + reason] += 1
            continue
        c, reason = asof(cvs[e['cv']], day)
        if reason:
            counts['cv_' + reason] += 1
            continue
        if not j['is_it']:
            counts['not_it_at_application'] += 1
            continue
        if j['org'] != e['org'] or c['person'] != e['person']:
            counts['document_identity_mismatch'] += 1
            continue
        work, wa = history_asof(histories['workexp.csv'][e['cv']], day, 'work')
        edu, ea = history_asof(histories['edu.csv'][e['cv']], day, 'edu')
        counts['ambiguous_history_entities'] += wa + ea
        wt = clean(' '.join(r['text'] for r in work))
        et = clean(' '.join(r['text'] for r in edu))
        text = clean(' '.join((c['text'], wt, et)))
        if len(text) < 30 or len(j['text']) < 60:
            counts['insufficient_professional_text'] += 1
            continue
        p = {
            'pair_id': digest(e['cv'] + '|' + e['job']), 'cv_id': digest(e['cv']),
            'person_id': digest(e['person']), 'job_id': digest(e['job']),
            'candidate_base_text': c['text'], 'candidate_text': text,
            'work_text': wt, 'education_text': et, 'need_text': j['text'],
            'label': LABELS[e['kind']], 'label_origin': 'source_reply_to_application',
            'source_status': e['kind'], 'application_day': day, 'event_day': e['day'],
            'cv_snapshot_day': c['day'], 'job_snapshot_day': j['day'],
            'history_snapshot_days': {f: [r['day'] for r in records] for f, records in
                                      [('workexp.csv', work), ('edu.csv', edu)]},
            'source_refs': {'invitations.csv': a['rownum'], 'responses.csv': e['rownum'],
                            'curricula_vitae.csv': c['rownum'], 'vacancies.csv': j['rownum'],
                            'workexp.csv': [r['rownum'] for r in work],
                            'edu.csv': [r['rownum'] for r in edu]},
        }
        grouped[p['pair_id']].append(p)
    rows = []
    for versions in grouped.values():
        rows.append(min(versions, key=lambda p: (p['application_day'], p['event_day'], p['source_refs']['invitations.csv'])))
        counts['repeat_closed_pair_observations_removed'] += len(versions) - 1
    old = read_jsonl(anchors / 'pairs.jsonl')
    old_report = json.loads((anchors / 'pairs-report.json').read_text())
    if file_hash(anchors / 'pairs.jsonl') != old_report['pairs_sha256']:
        raise ValueError('Anchor dataset changed')
    oldids = {p['pair_id'] for p in old}
    for p in rows:
        p['in_v2'] = p['pair_id'] in oldids
    rows, dropped = anchored_split(rows, old)
    counts['cross_anchor_component_rows_excluded'] = dropped
    rows.sort(key=lambda p: p['pair_id'])
    with (out / 'pairs.jsonl').open('x') as f:
        for p in rows:
            f.write(json.dumps(p, ensure_ascii=False, sort_keys=True) + '\n')
    report = {
        'version': 'application-decisions-v3-enriched', 'target': old_report['target'],
        'counts': dict(counts), 'pairs': len(rows),
        'split': {s: dict(Counter(str(p['label']) for p in rows if p['split'] == s))
                  for s in ('train', 'validation', 'test')},
        'with_work': sum(bool(p['work_text']) for p in rows),
        'with_education': sum(bool(p['education_text']) for p in rows),
        'new_vs_v2': sum(not p['in_v2'] for p in rows),
        'v2_pairs_retained': sum(p['in_v2'] for p in rows),
        'pairs_sha256': file_hash(out / 'pairs.jsonl'),
        'anchor_pairs_sha256': old_report['pairs_sha256'],
        'enrichment': meta, 'code_sha256': file_hash(Path(__file__)),
        'test_is_pristine': False, 'production_promotion_allowed': False,
    }
    write_json(out / 'pairs-report.json', report)
    db.close()
    print(json.dumps({k: v for k, v in report.items() if k != 'enrichment'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    i = sub.add_parser('index')
    i.add_argument('--source', type=Path, required=True)
    i.add_argument('--root', type=Path, required=True)
    i.add_argument('--out', type=Path, required=True)
    b = sub.add_parser('pairs')
    b.add_argument('--root', type=Path, required=True)
    b.add_argument('--enrichment', type=Path, required=True)
    b.add_argument('--anchors', type=Path, required=True)
    b.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.command == 'index':
        index(a.source, a.root, a.out)
    else:
        build(a.root, a.enrichment, a.anchors, a.out)

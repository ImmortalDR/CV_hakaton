"""Read-only source expansion; separate checkpointed V4 index, no app DB access."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sqlite3
import time

from prepare import clean, csv_rows, event_date, valid_date, write_json
from enrich import file_hash

# Deliberately exclude generic office literacy and generic 1C/accounting mentions.
IT_CONTENT = re.compile(
    r'программист|программирован\w*|разработ\w*\s+(?:программн\w*|веб|web|сайт|приложен\w*)'
    r'|тестирован\w*\s+(?:программн\w*|по\b|приложен\w*)'
    r'|администрирован\w*\s+(?:сервер\w*|баз\w*\s+данных|сет\w*)'
    r'|системн\w*\s+администратор|информационн\w*\s+безопасност\w*'
    r'|(?<!\w)(?:python|java|javascript|typescript|c\+\+|c#|php|golang|django|'
    r'react|kubernetes|devops|backend|frontend|fullstack|postgresql|machine learning)(?!\w)', re.I)


def in_cohort(row):
    return bool(row['is_it'] or IT_CONTENT.search(row['text']))


def build(base, source, out):
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=True)
    if (out/'scan.json').exists():
        raise FileExistsError('Completed index is frozen')
    frozen = json.loads((base/'scan.json').read_text())
    started = time.monotonic()
    db = sqlite3.connect(out/'index.sqlite')
    db.execute('PRAGMA cache_size=-32000')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS checkpoints(name TEXT PRIMARY KEY, info TEXT)')
    inputs = {}
    old = sqlite3.connect(f'file:{(base/"index.sqlite").resolve()}?mode=ro', uri=True)
    old.row_factory = sqlite3.Row
    if not db.execute("SELECT 1 FROM checkpoints WHERE name='base'").fetchone():
        db.executescript('DROP TABLE IF EXISTS events; DROP TABLE IF EXISTS jobs; '
            'CREATE TABLE events(eid TEXT, reply TEXT, cv TEXT, person TEXT, job TEXT, org TEXT, kind TEXT, day TEXT, published TEXT, rownum INTEGER);'
            'CREATE TABLE jobs(id TEXT, org TEXT, day TEXT, text TEXT, is_it INTEGER, rownum INTEGER);')
        db.executemany('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?)', old.execute('SELECT * FROM events'))
        counts = Counter()
        def jobs():
            for r in old.execute('SELECT * FROM jobs'):
                row = dict(r)
                new = int(in_cohort(row))
                counts['job_versions'] += 1
                counts['selected_versions'] += new
                row['is_it'] = new
                yield tuple(row.values())
        db.executemany('INSERT INTO jobs VALUES(?,?,?,?,?,?)', jobs())
        db.executescript('CREATE INDEX event_eid ON events(eid); CREATE INDEX event_job ON events(job); CREATE INDEX job_id ON jobs(id,day);')
        info={'counts':dict(counts), 'base_index_sha256':file_hash(base/'index.sqlite')}
        db.execute('INSERT INTO checkpoints VALUES(?,?)',('base',json.dumps(info)))
        db.commit()
    base_meta=json.loads(db.execute("SELECT info FROM checkpoints WHERE name='base'").fetchone()[0])
    if file_hash(base/'index.sqlite') != base_meta['base_index_sha256']:
        raise ValueError('Base index changed')
    old.close()
    it_jobs={r[0] for r in db.execute('SELECT DISTINCT id FROM jobs WHERE is_it=1')}
    cvs={r[0] for r in db.execute('SELECT DISTINCT e.cv FROM events e JOIN (SELECT DISTINCT id FROM jobs WHERE is_it=1) j ON e.job=j.id') if r[0]}
    print(json.dumps({'it_job_ids':len(it_jobs),'wanted_cv_ids':len(cvs)}),flush=True)
    stages=[('cvs','curricula_vitae.csv', 'id TEXT, person TEXT, day TEXT, text TEXT, rownum INTEGER'),
            ('applications','invitations.csv','eid TEXT, reply TEXT, cv TEXT, person TEXT, job TEXT, org TEXT, kind TEXT, day TEXT, published TEXT, rownum INTEGER')]
    for table, filename, schema in stages:
        done=db.execute('SELECT info FROM checkpoints WHERE name=?',(table,)).fetchone()
        if done:
            inputs[filename]=json.loads(done[0])
            if file_hash(source/filename)!=inputs[filename]['sha256']:
                raise ValueError('Source changed since checkpoint')
            continue
        db.execute('DROP TABLE IF EXISTS '+table)
        db.execute('CREATE TABLE '+table+'('+schema+')')
        stored=0
        for n, header, values in csv_rows(source/filename, inputs):
            key='id_cv' if table=='cvs' else 'id_vacancy'
            wanted=cvs if table=='cvs' else it_jobs
            if values[header.index(key)] not in wanted:
                continue
            r=dict(zip(header,values))
            if table=='cvs':
                record=(r['id_cv'],r['id_candidate'],valid_date(r['date_last_updated']),
                        clean(' '.join(r[k] for k in ('position_name','skills'))),n)
            else:
                record=(r['id_invitation'],r['id_reply'],r['id_cv'],r['id_candidate'],r['id_vacancy'],
                        r['id_hiring_organization'],r['response_type'],event_date(r),valid_date(r['date_last_updated']),n)
            db.execute('INSERT INTO '+table+' VALUES('+','.join('?'*len(record))+')',record)
            stored+=1
            if stored%10000==0: db.commit()
        if inputs[filename]!=frozen['inputs'][filename]:
            raise ValueError('Source differs from prior full scan')
        indices = ('CREATE INDEX cv_id ON cvs(id,day)' if table=='cvs' else
                   'CREATE INDEX app_eid ON applications(eid); CREATE INDEX app_reply ON applications(reply)')
        db.executescript(indices)
        db.execute('INSERT INTO checkpoints VALUES(?,?)',(table,json.dumps(inputs[filename])))
        db.commit()
        print(json.dumps({'stage':table,'stored':stored}),flush=True)
    inputs.update({k:frozen['inputs'][k] for k in ('responses.csv','vacancies.csv')})
    counts={'jobs_with_it_content':len(it_jobs),'wanted_cvs':len(cvs),
            'stored':{t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('jobs','cvs','events','applications')}}
    db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.close()
    write_json(out/'scan.json',{'version':'v4-content-cohort','inputs':inputs,'counts':counts,
        'base':base_meta,'code_sha256':file_hash(Path(__file__)), 'seconds':time.monotonic()-started})
    print(json.dumps(counts),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('base','source','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();build(a.base,a.source,a.out)

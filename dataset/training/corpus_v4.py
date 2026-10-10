"""Unlabelled job corpus: stable sample, held-out entity and near-copy exclusions."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sqlite3

from enrich import file_hash,read_jsonl
from freeze_v4 import purge
from prepare import digest,write_json


def build(index,pairs,out,limit=30000):
    os.umask(0o077);out.mkdir(parents=True,exist_ok=False)
    rows=read_jsonl(pairs);heldout=[p for p in rows if p['split']!='train']
    excluded={p['job_id'] for p in heldout}
    cutoff=max(p['application_day'] for p in rows if p['split']=='train')
    db=sqlite3.connect(f'file:{index.resolve()}?mode=ro',uri=True);db.row_factory=sqlite3.Row
    docs={};counts=Counter()
    for r in db.execute('SELECT * FROM jobs'):
        counts['input_versions']+=1
        if digest(r['id']) in excluded:counts['heldout_job_versions']+=1;continue
        if not r['day'] or r['day']>=cutoff:counts['after_corpus_cutoff']+=1;continue
        if len(r['text'])<60:continue
        key=digest(r['text'])
        p={'doc_id':key,'job_id':digest(r['id']),'need_text':r['text'],'day':r['day'],
           'source_ref':{'vacancies.csv':r['rownum']}}
        old=docs.get(key)
        if old is None or (p['day'],r['rownum'])<(old['day'],old['source_ref']['vacancies.csv']):docs[key]=p
    db.close()
    selected=[docs[k] for k in sorted(docs)[:limit]]
    kept,dropped=purge(selected,heldout)
    with (out/'corpus.jsonl').open('x') as f:
        for p in kept:f.write(json.dumps(p,ensure_ascii=False,sort_keys=True)+'\n')
    report={'kind':'unlabelled vacancies; not candidate relevance labels','rows':len(kept),
            'limit':limit,'unique_eligible_texts_before_sample':len(docs),
            'near_heldout_copies_removed':dropped,'counts':dict(counts),'cutoff_exclusive':cutoff,
            'cutoff_meaning':'last training application; grouped evaluation, NOT temporal forecasting',
            'heldout_job_versions_excluded':True,'corpus_sha256':file_hash(out/'corpus.jsonl'),
            'pairs_sha256':file_hash(pairs),'index_sha256':file_hash(index),'code_sha256':file_hash(Path(__file__))}
    write_json(out/'corpus-report.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('index','pairs','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();build(a.index,a.pairs,a.out)

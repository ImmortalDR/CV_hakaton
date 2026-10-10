"""Pre-frozen sampled retrieval pool with real, unjudged, dated CV distractors."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import sqlite3
import time
import joblib
import numpy as np
from threadpoolctl import threadpool_limits
from enrich import read_jsonl,history_asof,file_hash
from pairs import asof
from prepare import clean,digest,write_json
from freeze_v4 import purge
from e5_local import LocalE5


def prepare(index,history,pairs,legacy,out,limit=2000):
    os.umask(0o077);out.mkdir(parents=True,exist_ok=False)
    hm=json.loads((history/'complete.json').read_text())
    if file_hash(index)!=hm['base_index_sha256']:raise ValueError('Retrieval index changed')
    for name in ('workexp.csv','edu.csv'):
        if file_hash(history/(name+'.jsonl'))!=hm['inputs'][name]['output_sha256']:raise ValueError('History changed')
    rows=read_jsonl(pairs);test=[p for p in rows if p['split']=='test']
    blocked=[p for p in rows if p['split']!='test']+read_jsonl(legacy)
    forbidden_people={p['person_id'] for p in blocked};forbidden_cvs={p['cv_id'] for p in blocked}
    observed_people={p['person_id'] for p in test}
    db=sqlite3.connect(f'file:{index.resolve()}?mode=ro',uri=True);db.row_factory=sqlite3.Row
    eligible={r['person'] for r in db.execute('SELECT DISTINCT person FROM cvs')
              if r['person'] and digest(r['person']) not in forbidden_people|observed_people}
    selected=set(sorted(eligible,key=digest)[:limit]);cvs=defaultdict(list)
    for r in db.execute('SELECT * FROM cvs'):
        if r['person'] in selected and digest(r['id']) not in forbidden_cvs:cvs[r['id']].append(dict(r))
    db.close()
    hh={}
    for filename in ('workexp.csv','edu.csv'):
        d=defaultdict(list)
        for r in read_jsonl(history/(filename+'.jsonl')):
            if r['cv'] in cvs:d[r['cv']].append(r)
        hh[filename]=d
    pools=defaultdict(list)
    for p in test:pools[(p['job_id'],p['need_text'])].append(p)
    documents={};queries=[];cache={};removed=0
    for (job,need),ps in sorted(pools.items()):
        positives={p['person_id'] for p in ps if p['label']==1}
        if not positives:continue
        day=max(p['application_day'] for p in ps)
        if day not in cache:
            byperson={}
            for cv,versions in cvs.items():
                c,reason=asof(versions,day)
                if reason:continue
                work,_=history_asof(hh['workexp.csv'][cv],day,'work');edu,_=history_asof(hh['edu.csv'][cv],day,'edu')
                text=clean(' '.join([c['text']]+[r['text'] for r in work+edu]))
                if len(text)<30:continue
                p={'person_id':digest(c['person']),'cv_id':digest(cv),'candidate_base_text':c['text'],
                   'candidate_text':text,'cv_snapshot_day':c['day'],
                   'history_snapshot_days':{'workexp.csv':[r['day'] for r in work],'edu.csv':[r['day'] for r in edu]},
                   'source_refs':{'curricula_vitae.csv':c['rownum'],'workexp.csv':[r['rownum'] for r in work],'edu.csv':[r['rownum'] for r in edu]}}
                old=byperson.get(p['person_id'])
                if old is None or (p['cv_snapshot_day'],p['cv_id'])>(old['cv_snapshot_day'],old['cv_id']):byperson[p['person_id']]=p
            kept,dropped=purge(list(byperson.values()),blocked);removed+=dropped
            cache[day]=kept
        available={p['person_id']:p for p in cache[day]}
        for p in test:
            if p['application_day']>day or p['cv_snapshot_day']>=day:continue
            old=available.get(p['person_id'])
            if old is None or (p['cv_snapshot_day'],p['cv_id'])>(old['cv_snapshot_day'],old['cv_id']):available[p['person_id']]=p
        if not positives<=available.keys():raise ValueError('Observed positive missing')
        refs={}
        for person,p in sorted(available.items()):
            doc=digest(person+'|'+p['candidate_text']);refs[person]=doc
            # Private source references; no fabricated outcome for these documents.
            documents.setdefault(doc,{'doc_id':doc,'person_id':person,'candidate_text':p['candidate_text'],'source_refs':p['source_refs']})
        queries.append({'query_id':digest(job+'|'+need),'job_id':job,'group_id':ps[0]['group_id'],
                        'need_text':need,'query_day':day,'candidates':refs,'positive_people':sorted(positives)})
        print(json.dumps({'query':len(queries),'candidate_people':len(refs),'unique_documents':len(documents)}),flush=True)
    for filename,items in [('documents.jsonl',[documents[k] for k in sorted(documents)]),('queries.jsonl',queries)]:
        with (out/filename).open('x') as f:
            for p in items:f.write(json.dumps(p,ensure_ascii=False,sort_keys=True)+'\n')
    report={'extra_people_limit':limit,'eligible_extra_people':len(eligible),'selected_extra_people':len(selected),
            'queries':len(queries),'unique_documents':len(documents),'near_training_copies_removed_across_dates':removed,
            'candidate_people_min':min((len(q['candidates']) for q in queries),default=0),
            'candidate_people_max':max((len(q['candidates']) for q in queries),default=0),
            'pairs_sha256':file_hash(pairs),'legacy_sha256':file_hash(legacy),
            'index_sha256':file_hash(index),'history_manifest_sha256':file_hash(history/'complete.json'),
            'files':{n:file_hash(out/n) for n in ('documents.jsonl','queries.jsonl')},
            'code_sha256':file_hash(Path(__file__)),
            'unobserved_outcome':'unknown, not negative','scope':'sampled real-CV pool, not the entire marketplace'}
    write_json(out/'pool-report.json',report);print(json.dumps(report,indent=2))


def evaluate(root,model,encoder_path):
    start=time.monotonic();meta=json.loads((root/'pool-report.json').read_text())
    for name,h in meta['files'].items():
        if file_hash(root/name)!=h:raise ValueError('Pool changed')
    docs=read_jsonl(root/'documents.jsonl');queries=read_jsonl(root/'queries.jsonl')
    ix={p['doc_id']:i for i,p in enumerate(docs)}
    enc=LocalE5(encoder_path)
    texts=[p['candidate_text'] for p in docs];needs=[p['need_text'] for p in queries]
    a=[]
    for start_i in range(0,len(texts),100):
        a.extend(enc.encode(texts[start_i:start_i+100]));print(json.dumps({'encoded':min(start_i+100,len(texts)),'total':len(texts)}),flush=True)
    a=np.asarray(a);b=enc.encode(needs,role='query')
    artifact=joblib.load(model);vectorizer=artifact['features'].word
    wa,wb=vectorizer.transform(texts),vectorizer.transform(needs)
    records=[]
    for n,q in enumerate(queries):
        people=list(q['candidates']);indices=[ix[q['candidates'][p]] for p in people]
        truth=np.asarray([p in q['positive_people'] for p in people])
        for name,score in [('e5',a[indices]@b[n]),('word_tfidf',(wa[indices]@wb[n].T).toarray().ravel())]:
            k=min(100,len(score));cut=np.sort(score)[-k];above=score>cut;tied=score==cut
            fraction=(k-int(above.sum()))/int(tied.sum())
            recall=float((truth[above].sum()+fraction*truth[tied].sum())/truth.sum())
            records.append({'model':name,'job':q['job_id'],'group':q['group_id'],'recall':recall})
    from metrics_v4 import job_values
    results={name:job_values([r for r in records if r['model']==name],'recall') for name in ('e5','word_tfidf')}
    deltas=defaultdict(list)
    for (j,g,x),(j2,g2,y) in zip(results['e5'],results['word_tfidf']):
        if (j,g)!=(j2,g2):raise ValueError('Mismatched queries')
        deltas[g].append(x-y)
    keys=sorted(deltas);rng=np.random.default_rng(20261010);boot=[]
    if keys:
        for _ in range(1000):boot.append(float(np.mean([v for i in rng.integers(len(keys),size=len(keys)) for v in deltas[keys[i]]])))
    report={'pool':meta,'metric':'macro vacancy Recall@100 of observed positives',
            'scores':{n:float(np.mean([v for _,_,v in rs])) if rs else None for n,rs in results.items()},
            'jobs':len(results['e5']),'components':len(keys),'gain_ci95':np.quantile(boot,[.025,.975]).tolist() if boot else None,
            'small_sample_warning':len(keys)<30,'trivial_queries':sum(len(q['candidates'])<=100 for q in queries),
            'encoder_runtime':enc.stats,'seconds':time.monotonic()-start,'model_sha256':file_hash(model),
            'production_promotion_allowed':False,'encoder_manifest':enc.manifest,
            'code_sha256':file_hash(Path(__file__))}
    np.savez_compressed(root/'embeddings.npz',documents=a,queries=b)
    write_json(root/'retrieval-report.json',report);write_json(root/'per-query-private.json',records)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('prepare')
    for k in ('index','history','pairs','legacy','out'):q.add_argument('--'+k,type=Path,required=True)
    q=s.add_parser('evaluate')
    for k in ('root','model','encoder'):q.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    with threadpool_limits(limits=2):
        if a.command=='prepare':prepare(a.index,a.history,a.pairs,a.legacy,a.out)
        else:evaluate(a.root,a.model,a.encoder)

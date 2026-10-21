"""Legacy-isolated split and explicit corpus manifest before any V4 fitting."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path

from enrich import file_hash, read_jsonl
from pairs import Union
from prepare import digest, write_json
from sklearn.feature_extraction.text import HashingVectorizer

SEED='fsp-expanded-v4-20261010'


def keys(p):
    k=[f'{f}:{p[f]}' for f in ('person_id','cv_id','job_id')]
    k.append('jt:'+digest(p['need_text']))
    for field in ('candidate_text','candidate_base_text'):
        if len(p.get(field,''))>=30:k.append('ct:'+digest(p[field]))
    return k


def anchors(paths, out):
    os.umask(0o077);out.mkdir(parents=True,exist_ok=False)
    rows=[]
    for path in paths:
        for p in read_jsonl(path):
            rows.append(p | {'split':'train'})
    with (out/'pairs.jsonl').open('x') as f:
        for p in rows:f.write(json.dumps(p,ensure_ascii=False,sort_keys=True)+'\n')
    write_json(out/'pairs-report.json',{'target':'recorded_application_acceptance_vs_refusal_within_30_days',
        'pairs_sha256':file_hash(out/'pairs.jsonl'),'sources':{str(p):file_hash(p) for p in paths},
        'meaning':'Legacy entities allowed only in training, never a new validation/test'})


def assign(rows, legacy):
    u=Union()
    for p in rows+legacy:
        kk=keys(p)
        for k in kk[1:]:u.join(kk[0],k)
    old={u.root(keys(p)[0]) for p in legacy}
    for p in rows:
        g=u.root(keys(p)[0]);x=int(digest(SEED+g)[:8],16)/2**32
        p['legacy_component']=g in old
        p['split']='train' if g in old or x<.7 else ('validation' if x<.85 else 'test')
        p['group_id']=digest(g)
    return rows


def purge(target, refs):
    """Label blind overlap guard on both base and enriched CV, and job texts."""
    h=HashingVectorizer(n_features=2**20,alternate_sign=False,ngram_range=(2,3),binary=True)
    drop=set()
    for field in ('candidate_text','candidate_base_text','need_text'):
        texts=sorted({p.get(field,'') for p in refs if len(p.get(field,''))>=30})
        if not texts:continue
        r=h.transform(texts)
        for start in range(0,len(target),64):
            batch=target[start:start+64]
            q=h.transform([p.get(field,'') if len(p.get(field,''))>=30 else '' for p in batch])
            maximum=(q@r.T).max(axis=1).toarray().ravel()
            drop.update(start+i for i,x in enumerate(maximum) if x>=.95)
    return [p for i,p in enumerate(target) if i not in drop],len(drop)


def pool_counts(rows):
    groups=defaultdict(list)
    for p in rows:groups[(p['job_id'],p['need_text'])].append(p)
    mixed=[g for g in groups.values() if len({p['label'] for p in g})==2]
    large=[g for g in mixed if len(g)>=10]
    return {'rows':len(rows),'labels':dict(Counter(str(p['label']) for p in rows)),
            'people':len({p['person_id'] for p in rows}),'jobs':len({p['job_id'] for p in rows}),
            'components':len({p['group_id'] for p in rows}),
            'mixed_snapshot_pools':len(mixed),'mixed_jobs':len({g[0]['job_id'] for g in mixed}),
            'primary_jobs_min10':len({g[0]['job_id'] for g in large}),
            'primary_rows':sum(map(len,large)),'largest_mixed_pool':max(map(len,mixed),default=0)}


def freeze(raw, legacy_path, out):
    os.umask(0o077);out.mkdir(parents=True,exist_ok=False)
    rows=read_jsonl(raw);legacy=read_jsonl(legacy_path);raw_count=len(rows)
    # One person once per vacancy, with conflicting outcomes quarantined.
    grouped=defaultdict(list)
    for p in rows:grouped[(p['person_id'],p['job_id'])].append(p)
    unique=[];counts=Counter()
    for ps in grouped.values():
        if len({p['label'] for p in ps})>1:
            counts['conflicting_person_job_rows']+=len(ps);continue
        unique.append(min(ps,key=lambda p:(p['application_day'],p['event_day'],p['pair_id'])))
        counts['repeated_person_job_rows']+=len(ps)-1
    rows=assign(unique,legacy)
    splits={s:[p for p in rows if p['split']==s] for s in ('train','validation','test')}
    for s,ref in [('validation',legacy+splits['train']),('test',legacy+splits['train']+splits['validation'])]:
        splits[s],removed=purge(splits[s],ref);counts['near_duplicate_'+s]=removed
    retained=sorted([p for rs in splits.values() for p in rs],key=lambda p:p['pair_id'])
    for a,b in [('train','validation'),('train','test'),('validation','test')]:
        if {k for p in splits[a] for k in keys(p)} & {k for p in splits[b] for k in keys(p)}:
            raise ValueError('Entity/text leakage')
    for s in ('validation','test'):
        if {k for p in splits[s] for k in keys(p)} & {k for p in legacy for k in keys(p)}:
            raise ValueError('Legacy leakage')
    with (out/'pairs.jsonl').open('x') as f:
        for p in retained:f.write(json.dumps(p,ensure_ascii=False,sort_keys=True)+'\n')
    report={'version':'v4-frozen','seed':SEED,'target':'recorded_application_acceptance_vs_refusal_within_30_days',
            'split_kind':'group_disjoint; not chronological/external','legacy_validation_test_entity_overlap':0,
            'counts':dict(counts),'raw_pairs':raw_count,'pairs':len(retained),
            'split':{s:pool_counts(rs) for s,rs in splits.items()},
            'pairs_sha256':file_hash(out/'pairs.jsonl'),'raw_pairs_sha256':file_hash(raw),
            'legacy_sha256':file_hash(legacy_path),'code_sha256':file_hash(Path(__file__)),
            'production_promotion_allowed':False}
    write_json(out/'pairs-report.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('anchors');a.add_argument('--inputs',type=Path,nargs='+',required=True);a.add_argument('--out',type=Path,required=True)
    f=sub.add_parser('freeze')
    for n in ('raw','legacy','out'):f.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.command=='anchors':anchors(a.inputs,a.out)
    else:freeze(a.raw,a.legacy,a.out)

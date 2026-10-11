"""Freeze a blind ranking study and evaluate complete independent judgments.

Private input: {queries: [{id, component, text, candidates: [{id, text,
    scores: {baseline, challenger}}]}]}. Unknown labels never become negatives.
All artifacts belong in ignored/private folders. No remote APIs or model fitting.
"""
import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

COLUMNS=['query_id','candidate_id','reviewer_id','relevance','source']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def prepare(source,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise ValueError('Output must be empty; frozen study cannot be overwritten')
    data=json.loads(Path(source).read_text());seen=set();blind=[]
    for q in data['queries']:
        if not q['id'] or q['id'] in seen or not q['component']:raise ValueError('Unique queries and component IDs required')
        seen.add(q['id']);ids=set();candidates=[]
        for c in q['candidates']:
            if c['id'] in ids:raise ValueError('Duplicate candidate')
            ids.add(c['id'])
            if set(c['scores'])!={'baseline','challenger'} or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in c['scores'].values()):raise ValueError('Two finite precomputed model scores required')
            candidates.append(dict(id=c['id'],text=c['text']))
        random.Random('blind-'+q['id']).shuffle(candidates)
        blind.append(dict(id=q['id'],text=q['text'],candidates=candidates))
    write(out/'private-scores.json',data);(out/'private-scores.json').chmod(0o600)
    write(out/'blind-review.json',dict(queries=blind))
    with (out/'judgments.csv').open('w',newline='') as f:csv.writer(f).writerow(COLUMNS)
    write(out/'protocol.json',dict(metric='macro NDCG@10',min_candidates=10,min_components=20,
        min_reviewers=2,labels=[0,1,2],unknown='blank',seed=20261011,
        promotion='CI95 lower bound > 0, coverage complete, independent component threshold met',
        scores_sha256=sha(out/'private-scores.json'),blind_sha256=sha(out/'blind-review.json')))
    (out/'protocol.sha256').write_text(sha(out/'protocol.json')+'\n')
    return dict(status='prepared',queries=len(blind),human_judgments=0)


def ndcg(candidates,labels,model):
    def dcg(ids):return sum((2**labels[c['id']]-1)/math.log2(i+2) for i,c in enumerate(ids[:10]))
    ideal=dcg(sorted(candidates,key=lambda c:(-labels[c['id']],c['id'])))
    return dcg(sorted(candidates,key=lambda c:(-c['scores'][model],c['id'])))/ideal if ideal else None


def evaluate(root):
    root=Path(root)
    if sha(root/'protocol.json')!=(root/'protocol.sha256').read_text().strip():raise ValueError('Frozen protocol modified')
    protocol=json.loads((root/'protocol.json').read_text())
    for name,key in [('private-scores.json','scores_sha256'),('blind-review.json','blind_sha256')]:
        if sha(root/name)!=protocol[key]:raise ValueError('Frozen artifact modified: '+name)
    data=json.loads((root/'private-scores.json').read_text());queries={q['id']:q for q in data['queries']}
    judgments=defaultdict(dict);pairs={(q['id'],c['id']) for q in queries.values() for c in q['candidates']}
    with (root/'judgments.csv').open(newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=COLUMNS:raise ValueError('Unexpected judgment columns')
        for r in reader:
            if None in r or any(v is None for v in r.values()):raise ValueError('Malformed judgment')
            key=r['query_id'],r['candidate_id'];reviewer=r['reviewer_id'].strip()
            if key not in pairs or not reviewer or not r['source'].strip():raise ValueError('Unknown pair or missing reviewer/source')
            if reviewer in judgments[key]:raise ValueError('Duplicate judgment')
            if r['relevance'] not in ['','0','1','2']:raise ValueError('Relevance must be 0/1/2 or blank')
            judgments[key][reviewer]=int(r['relevance']) if r['relevance'] else None
    rows=[];excluded=[];agreements=[]
    for q in queries.values():
        labels={};complete=True
        for c in q['candidates']:
            values=[v for v in judgments[q['id'],c['id']].values() if v is not None]
            if len(values)<protocol['min_reviewers']:complete=False;break
            agreements.append(len(set(values))==1);labels[c['id']]=mean(values)
        if not complete or len(q['candidates'])<protocol['min_candidates']:
            excluded.append(q['id']);continue
        baseline=ndcg(q['candidates'],labels,'baseline');challenger=ndcg(q['candidates'],labels,'challenger')
        if baseline is None:excluded.append(q['id']);continue
        rows.append(dict(query_id=q['id'],component=q['component'],baseline=baseline,challenger=challenger,delta=challenger-baseline))
    groups=defaultdict(list)
    for r in rows:groups[r['component']].append(r)
    interval=None
    if len(groups)>=2:
        rng=random.Random(protocol['seed']);keys=list(groups);samples=[]
        for _ in range(2000):
            sampled=[r for key in rng.choices(keys,k=len(keys)) for r in groups[key]]
            samples.append(mean(r['delta'] for r in sampled))
        samples.sort();interval=[samples[50],samples[1950]]
    allowed=bool(rows and not excluded and len(groups)>=protocol['min_components'] and interval and interval[0]>0)
    return dict(status='measured' if rows else 'not_run',queries_total=len(queries),queries_evaluated=len(rows),
        independent_components=len(groups),excluded_queries=excluded,
        baseline_ndcg10=mean(r['baseline'] for r in rows) if rows else None,
        challenger_ndcg10=mean(r['challenger'] for r in rows) if rows else None,
        delta=mean(r['delta'] for r in rows) if rows else None,delta_ci95=interval,
        reviewer_exact_agreement=mean(agreements) if agreements else None,
        statistical_gate_passed=allowed,production_promotion_allowed=False,results=rows,
        limitations=['Labels and reviewer independence must be verified by people; source strings are not certification.',
            'Unknown/incomplete judgments exclude queries, not count as negative relevance.',
            'A statistical gate is necessary, not sufficient: privacy and product acceptance are separate.',
            'The protocol must be frozen before labels/test inspection; file hashes cannot prove historical independence.'])


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','evaluate']);p.add_argument('--root',type=Path,required=True);p.add_argument('--source',type=Path);a=p.parse_args()
    if a.command=='prepare' and not a.source:p.error('--source required')
    result=prepare(a.source,a.root) if a.command=='prepare' else evaluate(a.root)
    if a.command=='evaluate':write(a.root/'results.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))


if __name__=='__main__':main()

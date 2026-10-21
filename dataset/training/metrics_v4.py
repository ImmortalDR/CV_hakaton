"""Vacancy macro metrics; unknown outcomes excluded, tie-aware scores."""
from collections import defaultdict
import numpy as np
from sklearn.metrics import average_precision_score,roc_auc_score,ndcg_score


def pools(rows,scores,min_size=2):
    groups=defaultdict(list)
    for i,p in enumerate(rows):groups[(p['job_id'],p['need_text'])].append(i)
    out=[]
    for (job,_),ix in sorted(groups.items()):
        y=np.asarray([rows[i]['label'] for i in ix]);s=np.asarray(scores)[ix]
        if len(ix)<min_size or len(set(y))<2:continue
        if len({rows[i]['person_id'] for i in ix})!=len(ix):raise ValueError('Repeated person in pool')
        out.append({'job':job,'group':rows[ix[0]]['group_id'],'n':len(ix),
                    'ndcg':float(ndcg_score(y[None,:],s[None,:],k=10)),
                    'auc':float(roc_auc_score(y,s))})
    return out


def job_values(records,field):
    byjob=defaultdict(list)
    for p in records:byjob[(p['job'],p['group'])].append(p[field])
    return [(job,group,float(np.mean(v))) for (job,group),v in sorted(byjob.items())]


def evaluate(rows,scores):
    y=[p['label'] for p in rows]
    small=pools(rows,scores);large=pools(rows,scores,10)
    mean=lambda rs,f:float(np.mean([v for _,_,v in job_values(rs,f)])) if rs else None
    return {'rows':len(rows),'positives':sum(y),'mixed_jobs':len(job_values(small,'ndcg')),
            'primary_jobs_min10':len(job_values(large,'ndcg')),
            'ndcg_at_10_primary':mean(large,'ndcg'),
            'ndcg_at_min10n_small_pools':mean(small,'ndcg'),'within_job_auc':mean(small,'auc'),
            'average_precision':float(average_precision_score(y,scores)) if len(set(y))==2 else None}


def selection_metric(rows):
    m=evaluate(rows,np.zeros(len(rows)))
    if m['primary_jobs_min10']>=10:return 'ndcg_at_10_primary'
    if m['mixed_jobs']>=5:return 'within_job_auc'
    return 'average_precision'


def gain_interval(rows,score,baseline,min_size=10,repeats=1000):
    a=job_values(pools(rows,score,min_size),'ndcg');b=job_values(pools(rows,baseline,min_size),'ndcg')
    groups=defaultdict(list)
    for (job,g,x),(job2,g2,y) in zip(a,b):
        if (job,g)!=(job2,g2):raise ValueError('Non-paired pools')
        groups[g].append(x-y)
    keys=sorted(groups);rng=np.random.default_rng(20261010)
    vals=[]
    if keys:
        for _ in range(repeats):
            sample=[v for i in rng.integers(len(keys),size=len(keys)) for v in groups[keys[i]]]
            vals.append(float(np.mean(sample)))
    return {'metric':'macro_ndcg_at_10' if min_size==10 else 'macro_ndcg_at_min10n',
            'jobs':len(a),'components':len(keys),'repeats':len(vals),
            'mean_gain':float(np.mean([x-y for (_,_,x),(_,_,y) in zip(a,b)])) if a else None,
            'ci95':np.quantile(vals,[.025,.975]).tolist() if vals else None,
            'small_sample_warning':len(keys)<30}


def recall_at_100(rows,similarity):
    """Fixed test-only candidate pool, latest eligible CV per person at query time.

    Unjudged candidates are distractors with UNKNOWN relevance, never negatives.
    Each query uses a fixed vacancy snapshot and the last application in its pool.
    """
    groups=defaultdict(list)
    for i,p in enumerate(rows):groups[(p['job_id'],p['need_text'])].append(i)
    records=[]
    for (job,_),ix in sorted(groups.items()):
        positive={rows[i]['person_id'] for i in ix if rows[i]['label']==1}
        if not positive:continue
        day=max(rows[i]['application_day'] for i in ix)
        available={}
        for i,p in enumerate(rows):
            # This document includes history reconstructed at its application.
            # An older CV snapshot alone does not make that later history safe.
            if p['application_day']>day:continue
            if p['cv_snapshot_day']>=day:continue
            if any(d>=day for ds in p.get('history_snapshot_days',{}).values() for d in ds):continue
            old=available.get(p['person_id'])
            if old is None or (p['cv_snapshot_day'],p['pair_id'])>(rows[old]['cv_snapshot_day'],rows[old]['pair_id']):available[p['person_id']]=i
        if not positive<=available.keys():raise ValueError('Positive absent from dated retrieval pool')
        indices=list(available.values());scores=similarity(ix[0],indices)
        k=min(100,len(indices));cut=np.sort(scores)[-k]
        above=scores>cut;tied=scores==cut;fraction=(k-int(above.sum()))/int(tied.sum())
        hits=sum((1. if above[n] else fraction if tied[n] else 0.) for n,i in enumerate(indices) if rows[i]['person_id'] in positive)
        records.append({'job':job,'group':rows[ix[0]]['group_id'],'recall':hits/len(positive),'candidates':len(indices),'positives':len(positive)})
    vals=job_values(records,'recall')
    return {'recall_at_100':float(np.mean([v for _,_,v in vals])) if vals else None,
            'queries':len(records),'jobs':len(vals),'candidate_pool':'held-out people reconstructed at applications no later than query; unjudged relevance unknown',
            'candidate_count_min':min((r['candidates'] for r in records),default=0),
            'candidate_count_max':max((r['candidates'] for r in records),default=0),
            'trivial_queries_n_le_100':sum(r['candidates']<=100 for r in records)}

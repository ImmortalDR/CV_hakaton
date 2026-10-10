"""Predeclared CPU experiments with selection saved before test evaluation."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import platform
import resource
import time
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from catboost import CatBoostRanker,Pool
from threadpoolctl import threadpool_limits

from enrich import file_hash,read_jsonl
from prepare import write_json
from model_v4 import Features,scores,rank
from e5_local import LocalE5,pair_embeddings
from metrics_v4 import evaluate,selection_metric,gain_interval,recall_at_100

TARGET='recorded_application_acceptance_vs_refusal_within_30_days'


def pairwise(rows,x):
    groups=defaultdict(list)
    for i,p in enumerate(rows):groups[(p['job_id'],p['need_text'])].append(i)
    xx=[];yy=[];weights=[]
    for ix in groups.values():
        pos=[i for i in ix if rows[i]['label']==1];neg=[i for i in ix if rows[i]['label']==0]
        pairs=[(a,b) for a in pos for b in neg][:400]
        for a,b in pairs:
            d=x[a]-x[b];xx.extend([d,-d]);yy.extend([1,0]);weights.extend([1/(2*len(pairs))]*2)
    return np.asarray(xx),np.asarray(yy),np.asarray(weights)


def cb_pool(rows,x):
    groups=defaultdict(list)
    for i,p in enumerate(rows):groups[(p['job_id'],p['need_text'])].append(i)
    indices=[];gids=[];weights=[]
    for g,(_,ix) in enumerate(sorted(groups.items())):
        if len({rows[i]['label'] for i in ix})<2:continue
        indices.extend(ix);gids.extend([g]*len(ix));weights.extend([1/len(ix)]*len(ix))
    if not indices:return None
    return Pool(x[indices],label=[rows[i]['label'] for i in indices],group_id=gids,group_weight=weights)


def run(pairs,corpus,encoder_path,out):
    os.umask(0o077);out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    rmeta=json.loads(pairs.with_name('pairs-report.json').read_text())
    cmeta=json.loads(corpus.with_name('corpus-report.json').read_text())
    if file_hash(pairs)!=rmeta['pairs_sha256'] or file_hash(corpus)!=cmeta['corpus_sha256'] or cmeta['pairs_sha256']!=file_hash(pairs):raise ValueError('Input hash mismatch')
    rows=read_jsonl(pairs);rs={s:[p for p in rows if p['split']==s] for s in ('train','validation','test')}
    if any(len({p['label'] for p in rs[s]})<2 for s in rs):raise ValueError('Both outcomes required in every split')
    method=selection_metric(rs['validation']);write_json(out/'run-plan.json',{'selection_metric':method,'pairs_sha256':file_hash(pairs),'corpus_sha256':file_hash(corpus)})
    encoder=LocalE5(encoder_path)
    feature=Features().fit(rs['train'],[p['need_text'] for p in read_jsonl(corpus)])
    embeddings={};views={}
    for s in rs:
        print(json.dumps({'stage':'embedding','split':s,'rows':len(rs[s])}),flush=True)
        embeddings[s]=pair_embeddings(encoder,rs[s]);views[s]=feature.transform(rs[s],embeddings[s])
        np.savez_compressed(out/(s+'-embeddings.npz'),a=embeddings[s][0],b=embeddings[s][1])
    common={'features':feature,'target':TARGET,'encoder_manifest':encoder.manifest}
    artifacts={};trials=[];selection={}
    def register(name,artifact,param):
        score=scores(artifact,views['validation']);m=evaluate(rs['validation'],score)
        trials.append({'family':name,'parameter':param,'validation':m})
        value=m[method]
        if value is None:raise ValueError('Undefined selection metric')
        if name not in selection or value>selection[name]['value']:
            selection[name]={'value':value,'parameter':param,'validation':m}
            artifacts[name]=common|artifact
    for name in ('word_cosine','char_cosine','broad_cosine','e5_cosine'):
        register(name,{'view':name,'model':None},None)
    y=np.asarray([p['label'] for p in rs['train']])
    for name in ('word_pair','broad_pair','e5_pair','hybrid_pair','job_only'):
        for c in (.1,1.,10.):
            model=LogisticRegression(C=c,class_weight='balanced',max_iter=1000,solver='liblinear',random_state=20261010)
            model.fit(views['train'][name],y)
            register(name,{'view':name,'model':model},c)
        print(json.dumps({'stage':'trained','family':name}),flush=True)
    scaler=StandardScaler().fit(views['train']['dense'])
    x=scaler.transform(views['train']['dense']);px,py,pw=pairwise(rs['train'],x)
    if len(py):
        for c in (.1,1.,10.):
            model=LogisticRegression(C=c,fit_intercept=False,max_iter=1000,solver='liblinear',random_state=20261010).fit(px,py,sample_weight=pw)
            register('pairwise_dense',{'view':'dense','model':model,'scaler':scaler},c)
    pool=cb_pool(rs['train'],views['train']['dense'])
    if pool is not None:
        for depth in (3,5):
            model=CatBoostRanker(iterations=250,depth=depth,learning_rate=.03,loss_function='YetiRank',random_seed=20261010,thread_count=2,verbose=False,allow_writing_files=False)
            model.fit(pool);register('catboost_ranker',{'view':'dense','model':model},depth)
    choices=[n for n in artifacts if n!='job_only']
    winner=max(choices,key=lambda n:selection[n]['value'])
    # Persistent boundary: test labels have not entered any fit or comparison above.
    write_json(out/'selection.json',{'metric':method,'winner':winner,'families':selection,'trials':trials,
        'primary_validation_sufficient':method=='ndcg_at_10_primary','selection_uses_test':False})
    for name,a in artifacts.items():joblib.dump(a,out/(name+'.joblib'),compress=3)
    encoder_stats=dict(encoder.stats)
    del encoder
    predictions={n:np.asarray(scores(a,views['test'])) for n,a in artifacts.items()}
    predictions['constant']=np.zeros(len(rs['test']))
    np.savez_compressed(out/'test-scores.npz',**predictions)
    report={'version':'v4','target':TARGET,'winner':winner,'selection_metric':method,
        'data':rmeta,'corpus':cmeta,'test':{n:evaluate(rs['test'],s) for n,s in predictions.items()},
        'gain_vs_word_cosine':gain_interval(rs['test'],predictions[winner],predictions['word_cosine']),
        'small_pool_gain_vs_word_cosine':gain_interval(rs['test'],predictions[winner],predictions['word_cosine'],2),
        'gain_vs_constant':gain_interval(rs['test'],predictions[winner],predictions['constant']),
        'encoder':common['encoder_manifest'],'encoder_runtime':encoder_stats,
        'encoder_weights_finetuned':False,'production_promotion_allowed':False,
        'models':{n:file_hash(out/(n+'.joblib')) for n in artifacts},
        'pairs_sha256':file_hash(pairs),'corpus_sha256':file_hash(corpus),
        'python':platform.python_version(),'seconds':time.monotonic()-start,
        'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'code_sha256':{n:file_hash(Path(__file__).with_name(n)) for n in ('experiment_v4.py','model_v4.py','e5_local.py','metrics_v4.py','freeze_v4.py','corpus_v4.py','expand_v4.py')}}
    # Retrieval across the full dated test-only candidate universe, not prefiltered top100.
    a,b=embeddings['test']
    report['retrieval']={'e5':recall_at_100(rs['test'],lambda q,ix:a[ix]@b[q])}
    ca=feature.word.transform([p['candidate_text'] for p in rs['test']]);jb=feature.word.transform([p['need_text'] for p in rs['test']])
    report['retrieval']['word_tfidf']=recall_at_100(rs['test'],lambda q,ix:(ca[ix]@jb[q].T).toarray().ravel())
    # Descriptive shuffled-CV diagnostic; refit is deliberately not performed.
    rng=np.random.default_rng(20261010);ix=np.arange(len(rs['test']));groups=defaultdict(list)
    for i,p in enumerate(rs['test']):groups[(p['job_id'],p['need_text'])].append(i)
    for indices in groups.values():ix[indices]=rng.permutation(indices)
    shuffled=[]
    for i,p in enumerate(rs['test']):
        cp=rs['test'][ix[i]]
        shuffled.append(p|{k:cp[k] for k in ('candidate_text','work_text','education_text')})
    sv=feature.transform(shuffled,(a[ix],b))
    report['selected_shuffled_cv_test']=evaluate(rs['test'],scores(artifacts[winner],sv))
    report['seconds']=time.monotonic()-start
    write_json(out/'training-report.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


def replay(pairs,root):
    report=json.loads((root/'training-report.json').read_text())
    if file_hash(pairs)!=report['pairs_sha256']:raise ValueError('Pairs changed')
    rows=[p for p in read_jsonl(pairs) if p['split']=='test']
    e=np.load(root/'test-embeddings.npz');expected=np.load(root/'test-scores.npz');verified=[]
    for name,h in report['models'].items():
        path=root/(name+'.joblib')
        if file_hash(path)!=h:raise ValueError('Model changed')
        artifact=joblib.load(path);v=artifact['features'].transform(rows,(e['a'],e['b']))
        s=scores(artifact,v)
        if not np.array_equal(s,expected[name]):raise ValueError('Prediction replay mismatch')
        if evaluate(rows,s)!=report['test'][name]:raise ValueError('Metric replay mismatch')
        verified.append(name)
    result={'models':verified,'test_rows':len(rows),'predictions_exact':True,'metrics_exact':True,
            'note':'Replay uses frozen embeddings; separate encoder probe checks local inference'}
    write_json(root/'replay.json',result);print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    t=s.add_parser('train')
    for k in ('pairs','corpus','encoder','out'):t.add_argument('--'+k,type=Path,required=True)
    r=s.add_parser('replay');r.add_argument('--pairs',type=Path,required=True);r.add_argument('--root',type=Path,required=True)
    q=s.add_parser('predict')
    for k in ('model','encoder','need','candidates'):q.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    with threadpool_limits(limits=2):
        if a.command=='train':run(a.pairs,a.corpus,a.encoder,a.out)
        elif a.command=='replay':replay(a.pairs,a.root)
        else:print(json.dumps(rank(joblib.load(a.model),a.need.read_text(),read_jsonl(a.candidates),a.encoder),ensure_ascii=False,indent=2))

"""Rank-focused group OOF selection after V4; old test reuse explicitly disclosed."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import resource
import time
import joblib
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from catboost import CatBoostRanker
from threadpoolctl import threadpool_limits
from enrich import read_jsonl,file_hash
from prepare import write_json
from freeze_v4 import purge,keys
from model_v4 import Features,scores
from experiment_v4 import pairwise,cb_pool,TARGET
from metrics_v4 import selection_metric,evaluate,gain_interval

CONFIGS=[(n,None) for n in ('word_cosine','char_cosine','broad_cosine','e5_cosine')]+[
    ('pairwise_dense',c) for c in (.1,1.,10.)]+[('catboost_ranker',d) for d in (3,5)]


def config_key(name,param):return name+':'+str(param)


def fit_ranker(name,param,rows,views):
    if name.endswith('_cosine'):return {'view':name,'model':None}
    x=views['dense']
    if name=='pairwise_dense':
        scaler=StandardScaler().fit(x);px,py,pw=pairwise(rows,scaler.transform(x))
        if not len(py):raise ValueError('No mixed training pools')
        model=LogisticRegression(C=param,fit_intercept=False,max_iter=1000,solver='liblinear',random_state=20261010).fit(px,py,sample_weight=pw)
        return {'view':'dense','model':model,'scaler':scaler}
    pool=cb_pool(rows,x)
    if pool is None:raise ValueError('No ranking pool')
    model=CatBoostRanker(iterations=250,depth=param,learning_rate=.03,loss_function='YetiRank',random_seed=20261010,thread_count=2,verbose=False,allow_writing_files=False).fit(pool)
    return {'view':'dense','model':model}


def fold_corpus(corpus,heldout):
    blocked={p['job_id'] for p in heldout}
    candidates=[p for p in corpus if p['job_id'] not in blocked]
    kept,removed=purge(candidates,heldout)
    return kept,{'excluded_job_documents':len(corpus)-len(candidates),'excluded_near_copies':removed}


def load_embeddings(base,rows):
    """NPZ members decompress on every access: load each array exactly once."""
    em={};hashes={}
    for split in ('train','validation','test'):
        path=base/(split+'-embeddings.npz');rs=[p for p in rows if p['split']==split]
        with np.load(path) as packed:a,b=packed['a'],packed['b']
        if a.shape!=(len(rs),384) or b.shape!=(len(rs),384):raise ValueError('Embedding shape mismatch')
        if not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('Non-finite embeddings')
        hashes[split]=file_hash(path)
        for i,p in enumerate(rs):em[p['pair_id']]=(a[i].copy(),b[i].copy())
    return em,hashes


def run(pairs,corpus,base,out):
    os.umask(0o077);out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    prior=json.loads((base/'training-report.json').read_text())
    if file_hash(pairs)!=prior['pairs_sha256'] or file_hash(corpus)!=prior['corpus_sha256']:raise ValueError('Input changed')
    rows=read_jsonl(pairs);dev=[p for p in rows if p['split']!='test'];test=[p for p in rows if p['split']=='test']
    corpus_rows=read_jsonl(corpus);em,embedding_hashes=load_embeddings(base,rows)
    def embeddings(rs):return tuple(np.stack([em[p['pair_id']][j] for p in rs]) for j in (0,1))
    splitter=StratifiedGroupKFold(n_splits=4,shuffle=True,random_state=20261010)
    predictions={config_key(*c):np.full(len(dev),np.nan) for c in CONFIGS};folds=[]
    for fold,(ti,vi) in enumerate(splitter.split(dev,[p['label'] for p in dev],[p['group_id'] for p in dev])):
        tr=[dev[i] for i in ti];raw_val=[dev[i] for i in vi];va,removed=purge(raw_val,tr)
        if {k for p in tr for k in keys(p)} & {k for p in va for k in keys(p)}:raise ValueError('Fold leakage')
        vmap={p['pair_id']:i for i,p in enumerate(dev)};kept_ix=[vmap[p['pair_id']] for p in va]
        cc,cm=fold_corpus(corpus_rows,raw_val)
        feature=Features().fit(tr,[p['need_text'] for p in cc])
        tv=feature.transform(tr,embeddings(tr));vv=feature.transform(va,embeddings(va))
        for name,param in CONFIGS:
            key=config_key(name,param);artifact=fit_ranker(name,param,tr,tv)
            if not np.isnan(predictions[key][kept_ix]).all():raise ValueError('OOF row predicted twice')
            predictions[key][kept_ix]=scores(artifact,vv)
        info={'fold':fold,'train_rows':len(tr),'heldout_rows_before_purge':len(raw_val),'heldout_rows':len(va),
              'near_rows_removed':removed,'corpus_rows':len(cc),'corpus_exclusions':cm,
              'train_components':len({p['group_id'] for p in tr}),'heldout_components':len({p['group_id'] for p in va})}
        folds.append(info);print(json.dumps(info),flush=True)
    mask=np.isfinite(next(iter(predictions.values())))
    if any(not np.array_equal(np.isfinite(v),mask) for v in predictions.values()):raise ValueError('Different OOF coverage')
    oof=[p for p,m in zip(dev,mask) if m];metric=selection_metric(oof);selected={};trials=[]
    for name,param in CONFIGS:
        m=evaluate(oof,predictions[config_key(name,param)][mask]);value=m[metric]
        if value is None:raise ValueError('Undefined OOF selection')
        trials.append({'family':name,'parameter':param,'oof':m})
        if name not in selected or value>selected[name]['value']:selected[name]={'parameter':param,'value':value,'oof':m}
    winner=max(selected,key=lambda n:selected[n]['value'])
    write_json(out/'selection.json',{'winner':winner,'metric':metric,'families':selected,'trials':trials,
              'folds':folds,'oof_rows':len(oof),'development_rows':len(dev),'test_used_for_selection':False,
              'adaptive_after_v4_test':True})
    np.savez_compressed(out/'oof-scores-private.npz',pair_ids=np.asarray([p['pair_id'] for p in dev]),**predictions)
    # Refit only after a persistent OOF selection boundary.
    feature=Features().fit(dev,[p['need_text'] for p in corpus_rows]);dv=feature.transform(dev,embeddings(dev));test_emb=embeddings(test)
    views=feature.transform(test,test_emb);artifacts={};pred={}
    for name,choice in selected.items():
        a=fit_ranker(name,choice['parameter'],dev,dv)|{'features':feature,'target':TARGET,'encoder_manifest':prior['encoder']}
        joblib.dump(a,out/(name+'.joblib'),compress=3);artifacts[name]=a;pred[name]=scores(a,views)
    np.savez_compressed(out/'test-embeddings.npz',a=test_emb[0],b=test_emb[1]);np.savez_compressed(out/'test-scores.npz',**pred)
    dependencies=list(prior['code_sha256'])+['cv_v4.py']
    report={'version':'v4-cv','target':TARGET,'winner':winner,'selection_metric':metric,'development_rows':len(dev),'oof_rows':len(oof),
            'oof':{n:d['oof'] for n,d in selected.items()},'test':{n:evaluate(test,p) for n,p in pred.items()},
            'gain_vs_word_cosine':gain_interval(test,pred[winner],pred['word_cosine']),
            'small_pool_gain_vs_word_cosine':gain_interval(test,pred[winner],pred['word_cosine'],2),
            'models':{n:file_hash(out/(n+'.joblib')) for n in artifacts},'encoder':prior['encoder'],'encoder_weights_finetuned':False,
            'pairs_sha256':file_hash(pairs),'corpus_sha256':file_hash(corpus),'input_embedding_sha256':embedding_hashes,
            'code_sha256':{n:file_hash(Path(__file__).with_name(n)) for n in dependencies},
            'adaptive_after_v4_test':True,'test_is_pristine':False,'production_promotion_allowed':False,
            'seconds':time.monotonic()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    write_json(out/'training-report.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('pairs','corpus','base','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    with threadpool_limits(limits=2):run(a.pairs,a.corpus,a.base,a.out)

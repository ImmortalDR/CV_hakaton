"""Grouped OOF model selection; explicitly exploratory after the first V3 experiment."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import time

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold

from enrich import file_hash, read_jsonl
from experiment_v3 import (SEED, pool_indices, prepare_splits, rank_differences,
                           rank_metrics, ranking_bootstrap, selection_key, replay)
from prepare import write_json
from rank_features import Encoder, predict_artifact
from train import bootstrap

FAMILIES = [('base_pair','base_pair','point'),('enriched_word','enriched_word','point'),
            ('dual_pair','dual_pair','point'),('dense_pair','dense_pair','point'),
            ('boosted_pair','dense_pair','boost'),('pairwise_dense','dense_pair','rank'),
            ('pairwise_dual','dual_pair','rank'),('job_only','job_only','point'),
            ('candidate_only','candidate_only','point')]


def fit(rows, features, objective, parameter):
    y=np.array([p['label'] for p in rows])
    if objective=='boost':
        model=HistGradientBoostingClassifier(max_leaf_nodes=parameter,max_iter=100,
                learning_rate=.05,l2_regularization=10,min_samples_leaf=20,
                early_stopping=False,random_state=SEED)
        model.fit(features,y)
    else:
        model=LogisticRegression(C=parameter,solver='liblinear',max_iter=2000,
                random_state=SEED,class_weight=None if objective=='rank' else 'balanced',
                fit_intercept=objective!='rank')
        if objective=='rank':
            data=rank_differences(rows,features)
            if data is None or len(pool_indices(rows))<5:
                return None
            model.fit(data[0],data[1],sample_weight=data[2])
        else:
            model.fit(features,y)
        if max(model.n_iter_)>=model.max_iter:
            raise RuntimeError('Model did not converge')
    return model


def score(model, features):
    return model.decision_function(features) if hasattr(model,'decision_function') else model.predict_proba(features)[:,1]


def run(root,out):
    os.umask(0o077)
    out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    source=json.loads((root/'pairs-report.json').read_text())
    if file_hash(root/'pairs.jsonl')!=source['pairs_sha256']:
        raise ValueError('Frozen pairs hash mismatch')
    splits,removed=prepare_splits(read_jsonl(root/'pairs.jsonl'))
    dev=splits['train']+splits['validation']
    test=splits['test']
    labels=np.array([p['label'] for p in dev])
    groups=np.array([p['group_id'] for p in dev])
    cv=StratifiedGroupKFold(n_splits=3,shuffle=True,random_state=SEED)
    collected={}
    fold_reports=[]
    for fold,(tr,va) in enumerate(cv.split(np.zeros(len(dev)),labels,groups)):
        foldrows=[dev[i] | {'split':'train'} for i in tr]+[dev[i] | {'split':'validation'} for i in va]
        fs,removed_fold=prepare_splits(foldrows)
        train,valid=fs['train'],fs['validation']
        if min(Counter(p['label'] for p in train).values())<10 or len(set(p['label'] for p in valid))<2:
            raise ValueError('Insufficient independent fold classes')
        encoder=Encoder().fit(train)
        xt,xv=encoder.transform(train),encoder.transform(valid)
        models={}
        for name,view,objective in FAMILIES:
            for parameter in ((3,7) if objective=='boost' else (.1,1.,10.)):
                model=fit(train,xt[view],objective,parameter)
                if model is None:
                    continue
                pred=score(model,xv[view])
                key=(name,parameter)
                collected.setdefault(key,[]).extend((p,float(v),fold) for p,v in zip(valid,pred))
                models[f'{name}:{parameter}']=rank_metrics(valid,pred)
        fold_reports.append({'fold':fold,'train':len(train),'validation':len(valid),
                             'removed':removed_fold,'train_pools':len(pool_indices(train)),
                             'validation_pools':len(pool_indices(valid)),'scores':models})
        print(json.dumps({'fold_complete':fold,'train':len(train),'validation':len(valid)}),flush=True)
    expected={p['pair_id'] for p,_,_ in collected[('base_pair',.1)]}
    trials={}
    for key,values in collected.items():
        if len(values)!=len({p['pair_id'] for p,_,_ in values}):
            raise ValueError('OOF observation repeated')
        if {p['pair_id'] for p,_,_ in values}!=expected:
            continue  # A ranker unavailable in any fold is ineligible globally.
        rows=[p for p,_,_ in values]
        m=rank_metrics(rows,np.array([v for _,v,_ in values]))
        trials.setdefault(key[0],[]).append({'parameter':key[1],'oof':m})
    ranking=trials['base_pair'][0]['oof']['mixed_vacancy_pools']>=10
    selected={}
    for name,ts in trials.items():
        use_rank=ranking and name not in ('job_only','candidate_only')
        selected[name]=max(ts,key=lambda t:selection_key(t['oof'],use_rank))
    winner=max((n for n in selected if n not in ('job_only','candidate_only')),
               key=lambda n:selection_key(selected[n]['oof'],ranking))
    encoder=Encoder().fit(dev)
    features=encoder.transform(dev)
    artifacts={}
    family_reports={}
    for name,view,objective in FAMILIES:
        if name not in selected:
            continue
        chosen=selected[name]
        model=fit(dev,features[view],objective,chosen['parameter'])
        artifact={'encoder':encoder,'model':model,'view':view,'family':name,
                  'target':source['target'],'pairs_sha256':source['pairs_sha256'],
                  'production_promotion_allowed':False}
        joblib.dump(artifact,out/(name+'.joblib'),compress=3)
        artifacts[name]=artifact
        family_reports[name]={'selected_parameter':chosen['parameter'],'oof':chosen['oof'],
                              'trials':trials[name],'artifact_sha256':file_hash(out/(name+'.joblib'))}
    choice={'winner':winner,'selection_metric':'oof_macro_within_job_auc_then_ndcg_then_ap' if ranking else 'oof_ap_insufficient_pools',
            'families':family_reports,'folds':fold_reports,
            'protocol_sha256':file_hash(Path(__file__).with_name('EXPERIMENT_V3_CV.md'))}
    write_json(out/'selection.json',choice)
    write_json(out/'split-manifest.json',{'pairs_sha256':source['pairs_sha256'],
               'splits':{'train':[p['pair_id'] for p in dev],'validation':[],
                         'test':[p['pair_id'] for p in test]},'near_duplicates_removed':removed})
    with (out/'oof-predictions.jsonl').open('x') as f:
        for (name,param),values in sorted(collected.items()):
            for p,v,fold in values:
                f.write(json.dumps({'family':name,'parameter':param,'pair_id':p['pair_id'],
                                     'fold':fold,'label':p['label'],'score':v},sort_keys=True)+'\n')
    # Test is evaluated only after OOF selection and final weights are frozen.
    predictions={n:predict_artifact(a,test) for n,a in artifacts.items()}
    scores={n:rank_metrics(test,v) for n,v in predictions.items()}
    comparisons={n:{'ap':bootstrap(test,predictions[winner],predictions[n],repeats=1000),
                    'ranking':ranking_bootstrap(test,predictions[winner],predictions[n])}
                 for n in ('base_pair','enriched_word','job_only','candidate_only')}
    rng=np.random.default_rng(SEED)
    permutation=[]
    for _ in range(100):
        shuffled=predictions[winner].copy()
        for ix in pool_indices(test):
            shuffled[ix]=predictions[winner][rng.permutation(ix)]
        value=rank_metrics(test,shuffled)['macro_within_job_auc']
        if value is not None:
            permutation.append(value)
    observed=scores[winner]['macro_within_job_auc']
    diag={'observed_macro_within_job_auc':observed,'repeats':100,
          'shuffled_mean':float(np.mean(permutation)) if permutation else None,
          'one_sided_p':(1+sum(x>=observed for x in permutation))/(1+len(permutation)) if permutation else None}
    report={'status':'trained_offline','target':source['target'],'winner_selected_without_test':winner,
            'selection_metric':choice['selection_metric'],'scores':scores,'comparisons':comparisons,
            'counts':{'dev':len(dev),'test':len(test),'oof':len(expected)},
            'candidate_permutation':diag,'production_promotion_allowed':False,'test_is_pristine':False,
            'adaptive_after_v3':True,'pairs_sha256':source['pairs_sha256'],
            'selection_sha256':file_hash(out/'selection.json'),'split_sha256':file_hash(out/'split-manifest.json'),
            'seconds':time.monotonic()-started,
            'code_sha256':{n:file_hash(Path(__file__).with_name(n)) for n in
                           ('cross_validate_v3.py','experiment_v3.py','rank_features.py','enrich.py','train.py','prepare.py','pairs.py','application_pairs.py')}}
    write_json(out/'training-report.json',report)
    with (out/'test-predictions.jsonl').open('x') as f:
        for i,p in enumerate(test):
            f.write(json.dumps({'pair_id':p['pair_id'],'label':p['label'],
                                 'scores':{n:float(v[i]) for n,v in predictions.items()}},sort_keys=True)+'\n')
    replay(root,out)
    print(json.dumps({'winner':winner,'oof':selected[winner]['oof'],'test':scores[winner],'permutation':diag},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    run(a.root,a.out)

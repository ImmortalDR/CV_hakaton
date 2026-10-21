"""Predeclared CPU model comparison, candidate ranking controls and reproducible weights."""
from __future__ import annotations

import argparse
from collections import defaultdict, Counter
import json
import os
from pathlib import Path
import platform
import resource
import time

import joblib
import numpy as np
from scipy import sparse
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from enrich import file_hash, read_jsonl
from prepare import clean, technology_mentioned, write_json
from rank_features import Encoder, predict_artifact
from train import assert_isolated, bootstrap, metrics, remove_near_duplicates

SEED = 20261010


def pool_indices(rows):
    grouped = defaultdict(list)
    for i, p in enumerate(rows):
        grouped[(p['job_id'], p['need_text'])].append(i)
    return [ix for ix in grouped.values() if len({rows[i]['label'] for i in ix}) == 2]


def rank_metrics(rows, scores):
    m = metrics(rows, np.asarray(scores))
    pools = pool_indices(rows)
    m['macro_within_job_auc'] = float(np.mean([
        roc_auc_score([rows[i]['label'] for i in ix], np.asarray(scores)[ix]) for ix in pools
    ])) if pools else None
    m['mixed_pool_rows'] = sum(map(len, pools))
    return m


def rank_differences(rows, features):
    differences, weights = [], []
    for ix in pool_indices(rows):
        pos = [i for i in ix if rows[i]['label'] == 1]
        neg = [i for i in ix if rows[i]['label'] == 0]
        pairs = [(i,j) for i in pos for j in neg]
        # Deterministic cap prevents one huge vacancy dominating resources.
        if len(pairs) > 2000:
            rng = np.random.default_rng(SEED)
            pairs = [pairs[k] for k in sorted(rng.choice(len(pairs), 2000, replace=False))]
        for i, j in pairs:
            diff = features[i:i+1] - features[j:j+1]
            differences.extend((diff, -diff))
            weights.extend((1/(2*len(pairs)), 1/(2*len(pairs))))
    if not differences:
        return None
    x = sparse.vstack(differences, format='csr') if sparse.issparse(features) else np.vstack(differences)
    return x, np.tile([1,0], len(differences)//2), np.asarray(weights)


def selection_key(m, ranking):
    if ranking:
        return (m['macro_within_job_auc'], m['ndcg_at_5'], m['average_precision'])
    return (m['average_precision'],)


def ranking_bootstrap(rows, a, b, repeats=1000):
    units = defaultdict(list)
    for ix in pool_indices(rows):
        y = [rows[i]['label'] for i in ix]
        delta = roc_auc_score(y, a[ix]) - roc_auc_score(y, b[ix])
        units[rows[ix[0]]['group_id']].append(delta)
    keys = sorted(units)
    if not keys:
        return {'components': 0, 'macro_within_job_auc_gain_ci95': None}
    rng = np.random.default_rng(SEED)
    values = [np.mean([x for k in rng.choice(keys, len(keys), replace=True) for x in units[k]])
              for _ in range(repeats)]
    return {'components': len(keys), 'mixed_pools': sum(map(len, units.values())),
            'macro_within_job_auc_gain_ci95': np.quantile(values,[.025,.975]).tolist()}


def prepare_splits(rows):
    splits = {s:[p for p in rows if p['split']==s] for s in ('train','validation','test')}
    assert_isolated(splits)
    enriched_removed = remove_near_duplicates(splits)
    # Base CV duplicates remain leakage even after adding different history text.
    base_splits = {s:[p | {'candidate_text': p['candidate_base_text'] if len(p['candidate_base_text'])>=30 else ''}
                     for p in ps] for s,ps in splits.items()}
    base_removed = remove_near_duplicates(base_splits)
    for s in splits:
        allowed = {p['pair_id'] for p in base_splits[s]}
        splits[s] = [p for p in splits[s] if p['pair_id'] in allowed]
    assert_isolated(splits)
    # Blank base text is not a meaningful duplicate document.
    for a,b in [('train','validation'),('train','test'),('validation','test')]:
        if {p['candidate_base_text'] for p in splits[a] if len(p['candidate_base_text'])>=30} & {p['candidate_base_text'] for p in splits[b] if len(p['candidate_base_text'])>=30}:
            raise ValueError('Base text leakage')
    return splits, {'enriched': enriched_removed, 'base': base_removed}


def run(root, out):
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    source = json.loads((root/'pairs-report.json').read_text())
    if file_hash(root/'pairs.jsonl') != source['pairs_sha256']:
        raise ValueError('Frozen pairs hash mismatch')
    splits, removed = prepare_splits(read_jsonl(root/'pairs.jsonl'))
    counts = {s:dict(Counter(str(p['label']) for p in ps)) for s,ps in splits.items()}
    if any(counts[s].get(str(y),0)<10 for s in splits for y in (0,1)):
        write_json(out/'training-report.json', {'status':'insufficient_independent_classes','counts':counts})
        raise ValueError('Insufficient independent classes')
    manifest = {'pairs_sha256': source['pairs_sha256'], 'near_duplicates_removed': removed,
                'splits': {s:[p['pair_id'] for p in ps] for s,ps in splits.items()}}
    write_json(out/'split-manifest.json', manifest)
    encoder = Encoder().fit(splits['train'])
    features = {s:encoder.transform(splits[s]) for s in ('train','validation')}
    y = np.asarray([p['label'] for p in splits['train']])
    ranking_select = len(pool_indices(splits['validation'])) >= 5
    families = [('base_pair','base_pair','point'), ('enriched_word','enriched_word','point'),
                ('dual_pair','dual_pair','point'), ('dense_pair','dense_pair','point'),
                ('boosted_pair','dense_pair','boost'), ('pairwise_dense','dense_pair','rank'),
                ('pairwise_dual','dual_pair','rank'), ('job_only','job_only','point'),
                ('candidate_only','candidate_only','point')]
    artifacts, selection, skipped = {}, {}, {}
    for name, view, objective in families:
        x = features['train'][view]
        rank_data = rank_differences(splits['train'],x) if objective == 'rank' else None
        if objective == 'rank' and (rank_data is None or len(pool_indices(splits['train'])) < 5):
            skipped[name] = 'fewer_than_5_mixed_training_pools'
            continue
        attempts = []
        best = None
        for parameter in ((3,7) if objective=='boost' else (.1,1.,10.)):
            if objective=='boost':
                model = HistGradientBoostingClassifier(max_leaf_nodes=parameter,max_iter=100,
                    learning_rate=.05,l2_regularization=10,min_samples_leaf=20,
                    early_stopping=False,random_state=SEED)
                model.fit(x,y)
                score = model.predict_proba(features['validation'][view])[:,1]
            else:
                model = LogisticRegression(C=parameter,solver='liblinear',max_iter=2000,
                    random_state=SEED,class_weight=None if objective=='rank' else 'balanced',
                    fit_intercept=objective!='rank')
                if objective=='rank':
                    model.fit(rank_data[0],rank_data[1],sample_weight=rank_data[2])
                else:
                    model.fit(x,y)
                if max(model.n_iter_) >= model.max_iter:
                    raise RuntimeError('Classifier did not converge')
                score = model.decision_function(features['validation'][view])
            m = rank_metrics(splits['validation'],score)
            key = selection_key(m, objective=='rank')
            attempts.append({'parameter':parameter,'validation':m})
            if best is None or key > best[0]:
                best = (key,model,parameter,m)
        artifact = {'encoder':encoder, 'model':best[1], 'view':view, 'family':name,
                    'target':source['target'], 'pairs_sha256':source['pairs_sha256'],
                    'production_promotion_allowed':False}
        path = out/(name+'.joblib')
        joblib.dump(artifact,path,compress=3)
        artifacts[name] = artifact
        selection[name] = {'selected_parameter':best[2],'validation':best[3],
                            'trials':attempts,'artifact_sha256':file_hash(path)}
        print(json.dumps({'family_completed':name,'validation':best[3]},ensure_ascii=False),flush=True)
    eligible = [n for n in artifacts if n not in ('job_only','candidate_only')]
    winner = max(eligible,key=lambda n:selection_key(selection[n]['validation'],ranking_select))
    choice = {'winner':winner,'selection_metric':'macro_within_job_auc_then_ndcg_then_ap' if ranking_select else 'validation_ap_insufficient_pools',
              'families':selection,'skipped':skipped, 'training_mixed_pools':len(pool_indices(splits['train'])),
              'validation_mixed_pools':len(pool_indices(splits['validation'])),
              'protocol_sha256':file_hash(Path(__file__).with_name('EXPERIMENT_V3.md'))}
    # Persist selection and artifacts BEFORE computing test predictions or metrics.
    write_json(out/'selection.json',choice)
    test = splits['test']
    features['test'] = encoder.transform(test)
    predictions, scores = {}, {}
    for name,a in artifacts.items():
        f = features['test'][a['view']]
        model=a['model']
        pred = model.decision_function(f) if hasattr(model,'decision_function') else model.predict_proba(f)[:,1]
        restored=joblib.load(out/(name+'.joblib'))
        if not np.allclose(pred,predict_artifact(restored,test),rtol=0,atol=1e-12):
            raise AssertionError('Artifact reload mismatch')
        predictions[name] = pred
        scores[name] = rank_metrics(test,pred)
    for name in ('base_cosine','enriched_cosine','char_cosine'):
        predictions[name] = features['test'][name]
        scores[name] = rank_metrics(test,predictions[name])
    predictions['constant'] = np.zeros(len(test))
    scores['constant'] = rank_metrics(test,predictions['constant'])
    comparisons = {}
    for baseline in ('base_pair','enriched_word','job_only','candidate_only','enriched_cosine','constant'):
        comparisons[baseline] = {
            'ap':bootstrap(test,predictions[winner],predictions[baseline],repeats=1000),
            'ranking':ranking_bootstrap(test,predictions[winner],predictions[baseline]),
        }
    # Swapping whole candidate histories within a job leaves job-only signals fixed.
    rng=np.random.default_rng(SEED)
    permuted=[]
    pools=pool_indices(test)
    for _ in range(100):
        pred=predictions[winner].copy()
        for ix in pools:
            shuffled=rng.permutation(ix)
            # All job features are identical within this exact-text pool.
            # Swapping the full candidate is exactly a permutation of its score.
            pred[ix]=predictions[winner][shuffled]
        permuted.append(rank_metrics(test,pred)['macro_within_job_auc'])
    permuted=[x for x in permuted if x is not None]
    actual=scores[winner]['macro_within_job_auc']
    permutation={'repeats':100,'observed_macro_within_job_auc':actual,
                 'shuffled_mean':float(np.mean(permuted)) if permuted else None,
                 'one_sided_p':float((1+sum(x>=actual for x in permuted))/(1+len(permuted))) if permuted else None}
    slices={}
    selectors={'v2_retained':lambda p:p['in_v2'], 'new_vs_v2':lambda p:not p['in_v2'],
               'with_work':lambda p:bool(p['work_text']), 'without_work':lambda p:not p['work_text'],
               'with_education':lambda p:bool(p['education_text']),
               'python':lambda p:technology_mentioned(p['need_text'],'python'),
               'sql':lambda p:technology_mentioned(p['need_text'],'sql')}
    for name,fn in selectors.items():
        ix=[i for i,p in enumerate(test) if fn(p)]
        slices[name]={n:rank_metrics([test[i] for i in ix],pred[ix]) for n,pred in predictions.items() if n in (winner,'base_pair','job_only','enriched_cosine')}
    report={'status':'trained_offline','target':source['target'],'winner_selected_without_test':winner,
            'selection_metric':choice['selection_metric'],'counts':counts,'near_duplicates_removed':removed,
            'scores':scores,'comparisons':comparisons,'candidate_permutation':permutation,'slices':slices,
            'artifact_reload_equal':True,'production_promotion_allowed':False,'test_is_pristine':False,
            'pairs_sha256':source['pairs_sha256'],'selection_sha256':file_hash(out/'selection.json'),
            'split_sha256':file_hash(out/'split-manifest.json'),
            'versions':{'python':platform.python_version(),'sklearn':sklearn.__version__,'numpy':np.__version__},
            'seconds':time.monotonic()-started,'max_rss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'code_sha256':{name:file_hash(Path(__file__).with_name(name)) for name in
                           ('experiment_v3.py','rank_features.py','enrich.py','train.py','prepare.py','pairs.py','application_pairs.py')},
            'limitations':['Recorded reply is not competence or hiring; actor inferred from links.',
                           'Old V1/V2 corpus reused; no new independent external validation.',
                           'Pre-event history is incomplete; entity keys approximate.',
                           'Historical applicant pools are not simultaneously available candidate banks.']}
    write_json(out/'training-report.json',report)
    with (out/'test-predictions.jsonl').open('x') as f:
        for i,p in enumerate(test):
            f.write(json.dumps({'pair_id':p['pair_id'],'label':p['label'],
                                 'scores':{n:float(v[i]) for n,v in predictions.items()}},sort_keys=True)+'\n')
    print(json.dumps({'winner':winner,'scores':scores,'candidate_permutation':permutation},ensure_ascii=False,indent=2))


def replay(root,out):
    report=json.loads((out/'training-report.json').read_text())
    if file_hash(root/'pairs.jsonl')!=report['pairs_sha256']:
        raise ValueError('Pairs hash mismatch')
    if file_hash(out/'selection.json')!=report['selection_sha256'] or file_hash(out/'split-manifest.json')!=report['split_sha256']:
        raise ValueError('Selection or split changed')
    rows={p['pair_id']:p for p in read_jsonl(root/'pairs.jsonl')}
    manifest=json.loads((out/'split-manifest.json').read_text())
    test=[rows[k] for k in manifest['splits']['test']]
    selection=json.loads((out/'selection.json').read_text())
    saved=read_jsonl(out/'test-predictions.jsonl')
    assert [p['pair_id'] for p in saved]==[p['pair_id'] for p in test]
    for name,info in selection['families'].items():
        path=out/(name+'.joblib')
        if file_hash(path)!=info['artifact_sha256']:
            raise ValueError('Model hash mismatch')
        pred=predict_artifact(joblib.load(path),test)
        np.testing.assert_allclose(pred,[p['scores'][name] for p in saved],rtol=0,atol=1e-12)
        if rank_metrics(test,pred)!=report['scores'][name]:
            raise AssertionError('Metric replay mismatch')
    result={'status':'pass','models':len(selection['families']),'test_rows':len(test),'predictions_and_metrics_equal':True}
    write_json(out/'replay.json',result)
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=('run','replay'))
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    (run if a.command=='run' else replay)(a.root,a.out)

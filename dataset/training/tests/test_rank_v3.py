import json
from pathlib import Path
import random
import sys

import numpy as np
import pytest
from scipy import sparse

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from enrich import file_hash
from experiment_v3 import rank_differences, rank_metrics, run, replay
from rank_features import Encoder, tech_vector


def fixture_rows():
    rng=random.Random(324)
    def words(n):
        return ' '.join(''.join(rng.choices('abcdefghijklmnopqrstuvwxyz',k=9)) for _ in range(n))
    rows=[]
    for split in ('train','validation','test'):
        for j in range(8):
            key=f'{split}{j}'
            need=words(20)+' python sql backend development testing applications'
            for i in range(4):
                cv=words(18)+(' python sql' if i%2 else ' java excel')
                work=words(8)+' программирование'
                rows.append(dict(pair_id=key+str(i),person_id=key+str(i),cv_id=key+str(i),
                                 job_id=key,group_id=key,candidate_base_text=cv,
                                 candidate_text=cv+' '+work,work_text=work,education_text='',
                                 need_text=need,label=i%2,split=split,in_v2=True))
    return rows


def test_pairwise_examples_cancel_vacancy_features_and_weight_each_pool_equally():
    rows=[dict(job_id='a',need_text='a',label=y) for y in (0,1,1)]
    rows += [dict(job_id='b',need_text='b',label=y) for y in (0,1)]
    x=sparse.csr_matrix([[99,0],[99,1],[99,2],[55,0],[55,3]])
    xx,y,w=rank_differences(rows,x)
    assert np.all(xx.toarray()[:,0]==0)
    assert np.all(xx.toarray()[::2]==-xx.toarray()[1::2])
    assert w[:4].sum()==pytest.approx(1) and w[4:].sum()==pytest.approx(1)
    assert len(y)==6


def test_job_only_scores_cannot_look_like_candidate_ranking():
    rows=[dict(job_id='a',need_text='a',label=y) for y in (0,1)]
    rows += [dict(job_id='b',need_text='b',label=y) for y in (0,1)]
    assert rank_metrics(rows,np.array([1,1,8,8]))['macro_within_job_auc']==.5


def test_encoder_is_train_only_and_ignores_outcomes_identifiers_and_dates():
    rows=fixture_rows()
    e=Encoder().fit(rows[:32])
    assert 'heldoutmarkernotinthetrain' not in e.word.vocabulary_
    p=rows[32] | {'candidate_text':rows[32]['candidate_text']+' heldoutmarkernotinthetrain'}
    changed=p | {'label':1-p['label'],'source_status':'Принятие','job_id':'evil',
                 'age':87,'event_day':'2999-01-01'}
    a=e.transform([p]); b=e.transform([changed])
    for k in a:
        x,y=(a[k].toarray(),b[k].toarray()) if sparse.issparse(a[k]) else (a[k],b[k])
        np.testing.assert_array_equal(x,y)
    assert 'heldoutmarkernotinthetrain' not in e.word.vocabulary_


def test_technology_boundaries_do_not_equate_nosql_and_sql():
    from rank_features import TECH
    sql=list(TECH).index('sql')
    assert tech_vector('NoSQL')[sql]==0
    assert tech_vector('PostgreSQL')[sql]==1


def test_experiment_freezes_selection_and_replays_all_models(tmp_path):
    root=tmp_path/'input'; root.mkdir()
    rows=fixture_rows()
    (root/'pairs.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in rows))
    (root/'pairs-report.json').write_text(json.dumps({'pairs_sha256':file_hash(root/'pairs.jsonl'),
                                                    'target':'artificial_software_fixture'}))
    out=tmp_path/'out'
    run(root,out)
    report=json.loads((out/'training-report.json').read_text())
    assert report['production_promotion_allowed'] is False
    assert report['selection_metric']=='macro_within_job_auc_then_ndcg_then_ap'
    assert report['scores']['job_only']['macro_within_job_auc']==.5
    assert report['scores']['base_pair']['n']==32
    replay(root,out)
    assert json.loads((out/'replay.json').read_text())['models']==9
    (out/'selection.json').write_text('{}')
    with pytest.raises(ValueError,match='Selection or split'):
        replay(root,out)

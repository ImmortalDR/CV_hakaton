import json
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from expand_v4 import in_cohort
from freeze_v4 import assign,freeze,purge,keys
from metrics_v4 import evaluate,gain_interval,recall_at_100,selection_metric
from experiment_v4 import pairwise,cb_pool


def row(i,job='j',label=0,**kw):
    return {'pair_id':str(i),'cv_id':'c'+str(i),'person_id':'p'+str(i),'job_id':job,
            'group_id':job,'candidate_text':'professional unique candidate '+str(i),
            'candidate_base_text':'base unique candidate '+str(i),'need_text':'need '+job,
            'application_day':'2020-02-01','event_day':'2020-02-02','cv_snapshot_day':'2020-01-01',
            'work_text':'','education_text':'','label':label,**kw}


def test_cohort_distinguishes_professional_context_from_office_literacy():
    for text in ['уверенный пользователь ПК Excel Word','бухгалтер знание 1С','инженер механик']:
        assert not in_cohort({'is_it':0,'text':text})
    for text in ['разработка программного обеспечения','сопровождение PostgreSQL','администрирование серверов']:
        assert in_cohort({'is_it':0,'text':text})
    assert in_cohort({'is_it':1,'text':'legacy selected title'})


def test_old_entities_and_text_copies_cannot_be_new_holdout():
    old=[row(1,job='old',need_text='old document '*10)]
    rows=[row(2,job='fresh',person_id='p1'),row(3,job='another',candidate_text=old[0]['candidate_text'])]
    out=assign(rows,old)
    assert all(p['split']=='train' and p['legacy_component'] for p in out)
    assert [p['split'] for p in assign(rows,old)]==[p['split'] for p in out]


def test_near_copies_removed_without_using_labels():
    old=[row(1,candidate_text=' '.join('technicalskill'+str(i) for i in range(100)))]
    rows=[row(2,job='other',candidate_text=old[0]['candidate_text']+' tiny edit')]
    assert purge(rows,old)==([],1)
    rows[0]['label']=1
    assert purge(rows,old)==([],1)


def test_metric_counts_unique_jobs_not_versions_and_handles_ties():
    rows=[row(i,label=int(i==0)) for i in range(10)]
    assert evaluate(rows,np.arange(10)[::-1])['ndcg_at_10_primary']==1.
    assert evaluate(rows,np.zeros(10))['ndcg_at_10_primary']<1
    assert evaluate(rows[:9],np.zeros(9))['ndcg_at_10_primary'] is None
    other=[row(i+100,label=int(i==0),need_text='second version') for i in range(10)]
    m=evaluate(rows+other,np.zeros(20))
    assert m['mixed_jobs']==1 and m['primary_jobs_min10']==1
    duplicate=rows+[row(50,person_id='p0')]
    with pytest.raises(ValueError,match='Repeated person'):evaluate(duplicate,np.zeros(11))


def test_selection_does_not_call_small_pools_primary():
    rows=[row(i,job='j'+str(i//2),label=i%2) for i in range(12)]
    assert selection_metric(rows)=='within_job_auc'
    assert selection_metric(rows[:4])=='average_precision'
    ci=gain_interval(rows,np.zeros(12),np.zeros(12))
    assert ci['ci95'] is None and ci['jobs']==0
    ci=gain_interval(rows,np.zeros(12),np.zeros(12),2,repeats=10)
    assert ci['ci95']==[0.,0.] and ci['components']==6


def test_retrieval_excludes_future_profiles_and_deduplicates_people():
    rows=[row(0,label=1),row(1,job='b'),row(2,job='c',cv_snapshot_day='2021-01-01'),row(3,job='d',person_id='p1'),
          row(4,job='e',application_day='2020-03-01')]
    seen=[]
    def sim(q,ix):seen.append(ix);return np.zeros(len(ix))
    r=recall_at_100(rows,sim)
    assert r['candidate_count_max']==2 and r['recall_at_100']==1
    assert all(2 not in ix and 4 not in ix for ix in seen)


def test_pairwise_training_never_compares_different_jobs_and_balances_pools():
    rows=[row(0,label=1),row(1),row(2,job='b',label=1),row(3,job='b'),row(4,job='b')]
    x=np.asarray([[10.],[5.],[100.],[90.],[80.]])
    px,py,w=pairwise(rows,x)
    assert px[:,0].tolist()==[5.,-5.,10.,-10.,20.,-20.]
    assert w[:2].sum()==1 and w[2:].sum()==1
    assert cb_pool(rows,x).num_row()==5


def test_freeze_rejects_conflicting_cvs_of_one_person(tmp_path):
    rows=[row(1,label=0),row(2,label=1,person_id='p1')]
    raw=tmp_path/'raw.jsonl';old=tmp_path/'old.jsonl'
    raw.write_text(''.join(json.dumps(p)+'\n' for p in rows));old.write_text('')
    out=tmp_path/'out';freeze(raw,old,out)
    report=json.loads((out/'pairs-report.json').read_text())
    assert report['pairs']==0 and report['counts']['conflicting_person_job_rows']==2


def test_training_freezes_selection_before_test_and_replays_all_models(tmp_path,monkeypatch):
    import hashlib
    import experiment_v4 as experiment
    from enrich import file_hash
    from prepare import write_json
    from threadpoolctl import threadpool_limits

    class FakeEncoder:
        manifest={'kind':'test-only deterministic encoder, NOT research evidence'}
        def __init__(self,path):self.stats={}
        def encode(self,texts,role='passage'):
            out=[]
            for text in texts:
                seed=int(hashlib.sha256((role+text).encode()).hexdigest()[:8],16)
                x=np.random.default_rng(seed).normal(size=384);out.append(x/np.linalg.norm(x))
            return np.asarray(out)
    monkeypatch.setattr(experiment,'LocalE5',FakeEncoder)
    pairs=tmp_path/'pairs.jsonl';corpus=tmp_path/'corpus.jsonl';out=tmp_path/'model'
    rows=[]
    for i in range(80):
        split='train' if i<40 else 'validation' if i<60 else 'test'
        rows.append(row(i,job='j'+str(i//10),label=i%2,split=split,
                        need_text='python software data developer '+('project'+str(i//10)+' ')*10,
                        candidate_text='python software developer experience '+('specialty'+str(i)+' ')*10,
                        work_text='python production engineering'))
    pairs.write_text(''.join(json.dumps(p)+'\n' for p in rows))
    corpus.write_text(json.dumps({'job_id':'extra','need_text':'software developer python data engineering'})+'\n')
    write_json(pairs.with_name('pairs-report.json'),{'pairs_sha256':file_hash(pairs)})
    write_json(corpus.with_name('corpus-report.json'),{'corpus_sha256':file_hash(corpus),'pairs_sha256':file_hash(pairs)})
    original=experiment.evaluate
    def audited(rows,scores):
        if rows and rows[0]['split']=='test':assert (out/'selection.json').exists()
        return original(rows,scores)
    monkeypatch.setattr(experiment,'evaluate',audited)
    with threadpool_limits(limits=2):
        experiment.run(pairs,corpus,tmp_path,out)
        experiment.replay(pairs,out)
    report=json.loads((out/'replay.json').read_text())
    assert len(report['models'])==11 and report['predictions_exact'] and report['metrics_exact']
    import cv_v4
    cvout=tmp_path/'cv-model'
    fit_original=cv_v4.Features.fit;fit_calls=[]
    def guarded_fit(self,rows,corpus):
        assert all(p['split']!='test' for p in rows)
        fit_calls.append({p['group_id'] for p in rows})
        return fit_original(self,rows,corpus)
    monkeypatch.setattr(cv_v4.Features,'fit',guarded_fit)
    evaluate_original=cv_v4.evaluate
    def guarded_metric(rows,scores):
        if rows and rows[0]['split']=='test':assert (cvout/'selection.json').exists()
        return evaluate_original(rows,scores)
    monkeypatch.setattr(cv_v4,'evaluate',guarded_metric)
    with threadpool_limits(limits=2):
        cv_v4.run(pairs,corpus,out,cvout)
        experiment.replay(pairs,cvout)
    cvreport=json.loads((cvout/'training-report.json').read_text())
    assert len(fit_calls)==5 and len(cvreport['models'])==6
    assert cvreport['adaptive_after_v4_test'] and not cvreport['test_is_pristine']
    assert cvreport['oof_rows']==60


def test_extended_retrieval_preserves_unknown_and_rejects_training_and_future(tmp_path):
    import sqlite3
    from retrieval_v4 import prepare
    from enrich import file_hash,read_jsonl
    from prepare import write_json,digest
    index=tmp_path/'index.sqlite'
    db=sqlite3.connect(index)
    db.execute('CREATE TABLE cvs(id TEXT,person TEXT,day TEXT,text TEXT,rownum INTEGER)')
    db.executemany('INSERT INTO cvs VALUES(?,?,?,?,?)',[
        ('a','blocked','2019-01-01','private blocked training professional experience',1),
        ('b','unknown','2019-01-01','медицинская практика хирургия лечение больных в поликлинике',2),
        ('c','future','2021-01-01','future professional profile unavailable at query time',3)])
    db.commit();db.close()
    history=tmp_path/'history';history.mkdir()
    for name in ('workexp.csv','edu.csv'):(history/(name+'.jsonl')).write_text('')
    write_json(history/'complete.json',{'base_index_sha256':file_hash(index),
               'inputs':{name:{'output_sha256':file_hash(history/(name+'.jsonl'))} for name in ('workexp.csv','edu.csv')}})
    pairs=tmp_path/'pairs.jsonl';legacy=tmp_path/'legacy.jsonl'
    train=row(0,person_id=digest('blocked'),cv_id=digest('a'),split='train')
    test=row(1,label=1,job='q',split='test',source_refs={})
    pairs.write_text(json.dumps(train)+'\n'+json.dumps(test)+'\n');legacy.write_text('')
    out=tmp_path/'retrieval';prepare(index,history,pairs,legacy,out)
    docs=read_jsonl(out/'documents.jsonl');queries=read_jsonl(out/'queries.jsonl')
    assert len(docs)==2 and len(queries)==1
    assert {p['person_id'] for p in docs}=={'p1',digest('unknown')}
    assert all('label' not in p for p in docs)
    assert queries[0]['positive_people']==['p1']


def test_embedding_cache_reuses_only_same_model_role_and_text(tmp_path):
    from e5_local import cached_encode
    class Encoder:
        manifest={'revision':'a'}
        calls=0
        def encode(self,texts,role):
            self.calls+=len(texts)
            return np.ones((len(texts),384),dtype=np.float32)/np.sqrt(np.float32(384))
    enc=Encoder();cache=tmp_path/'cache.sqlite'
    x=cached_encode(enc,['text'],'passage',cache)
    assert enc.calls==1
    assert np.array_equal(x,cached_encode(enc,['text'],'passage',cache)) and enc.calls==1
    cached_encode(enc,['text'],'query',cache)
    assert enc.calls==2
    enc.manifest={'revision':'b'}
    cached_encode(enc,['text'],'passage',cache)
    assert enc.calls==3


def test_embedding_cache_keeps_completed_batch_after_interruption(tmp_path):
    from e5_local import cached_encode
    import sqlite3
    class Encoder:
        manifest={'revision':'checkpoint-fixture'}
        batches=0
        documents=0
        fail=True
        def encode(self,texts,role):
            self.batches+=1
            if self.fail and self.batches==2:raise RuntimeError('interrupted fixture')
            self.documents+=len(texts)
            return np.ones((len(texts),384),dtype=np.float32)/np.sqrt(np.float32(384))
    enc=Encoder();cache=tmp_path/'cache.sqlite';texts=[str(i) for i in range(25)]
    with pytest.raises(RuntimeError,match='interrupted'):
        cached_encode(enc,texts,'passage',cache)
    with sqlite3.connect(cache) as db:assert db.execute('SELECT COUNT(*) FROM embeddings').fetchone()[0]==10
    enc.fail=False
    result=cached_encode(enc,texts,'passage',cache)
    assert result.shape==(25,384) and enc.documents==25


def test_inference_contract_rejects_duplicate_ids_and_preserves_unknown():
    from model_v4 import rank
    need='Разработка и сопровождение серверных приложений на Python и PostgreSQL'
    with pytest.raises(ValueError,match='Duplicate'):
        rank({},need,[{'candidate_id':'x'},{'candidate_id':'x'}],None)
    with pytest.raises(ValueError,match='Need text'):
        rank({},'short',[{'candidate_id':'x'}],None)
    result=rank({'target':'recorded_reply'},need,[{'candidate_id':'x','candidate_base_text':'SQL'}],None)
    assert result['candidates']==[{'candidate_id':'x','score':None,'status':'insufficient_professional_text'}]
    assert result['production_promotion_allowed'] is False


def test_cv_loads_each_compressed_embedding_array_once(tmp_path,monkeypatch):
    import cv_v4
    rows=[]
    for split,n in [('train',50),('validation',2),('test',3)]:
        rows.extend(row(split+str(i),split=split) for i in range(n))
        np.savez_compressed(tmp_path/(split+'-embeddings.npz'),a=np.ones((n,384),dtype=np.float32),b=np.ones((n,384),dtype=np.float32))
    calls=[];original=np.lib.npyio.NpzFile.__getitem__
    def get(self,key):calls.append(key);return original(self,key)
    monkeypatch.setattr(np.lib.npyio.NpzFile,'__getitem__',get)
    em,hashes=cv_v4.load_embeddings(tmp_path,rows)
    assert len(em)==55 and len(hashes)==3 and calls==['a','b']*3

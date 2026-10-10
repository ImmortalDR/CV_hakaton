"""Independent artifact checks and descriptive slices; never selects a model."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import time
import joblib
import numpy as np
from threadpoolctl import threadpool_limits
from enrich import file_hash,read_jsonl
from prepare import write_json,technology_mentioned
from e5_local import LocalE5
from metrics_v4 import evaluate


def check(pairs,model,retrieval,encoder_path,out):
    report=json.loads((model/'training-report.json').read_text())
    rr=json.loads((retrieval/'retrieval-report.json').read_text())
    for name,h in rr['pool']['files'].items():
        if file_hash(retrieval/name)!=h:raise ValueError('Retrieval input changed')
    if file_hash(pairs)!=report['pairs_sha256']:raise ValueError('Pairs changed')
    docs=read_jsonl(retrieval/'documents.jsonl');qs=read_jsonl(retrieval/'queries.jsonl')
    emb=np.load(retrieval/'embeddings.npz');index={d['doc_id']:i for i,d in enumerate(docs)}
    vectorizer=joblib.load(model/'word_cosine.joblib')['features'].word
    wa=vectorizer.transform([d['candidate_text'] for d in docs]);wb=vectorizer.transform([q['need_text'] for q in qs])
    perjob={n:defaultdict(list) for n in ('e5','word_tfidf')}
    for qi,q in enumerate(qs):
        people=sorted(q['candidates']);ix=[index[q['candidates'][p]] for p in people]
        for name,score in [('e5',emb['documents'][ix]@emb['queries'][qi]),('word_tfidf',(wa[ix]@wb[qi].T).toarray().ravel())]:
            # Expected membership under uniform random ordering of tied candidates.
            hit=0.
            for i,person in enumerate(people):
                if person not in q['positive_people']:continue
                higher=int(np.count_nonzero(score>score[i]));equal=int(np.count_nonzero(score==score[i]))
                hit+=max(0.,min(1.,(100-higher)/equal))
            perjob[name][q['job_id']].append(hit/len(q['positive_people']))
    recalculated={n:float(np.mean([np.mean(v) for v in jobs.values()])) for n,jobs in perjob.items()}
    chance=defaultdict(list)
    for q in qs:chance[q['job_id']].append(min(1.,100/len(q['candidates'])))
    for n,value in recalculated.items():
        if not np.isclose(value,rr['scores'][n],atol=1e-12,rtol=0):raise ValueError('Independent retrieval calculation mismatch')
    enc=LocalE5(encoder_path);started=time.monotonic()
    sample=list(range(min(5,len(docs))))
    actual=enc.encode([docs[i]['candidate_text'] for i in sample])
    delta=float(np.max(abs(actual-emb['documents'][sample])))
    if not np.allclose(actual,emb['documents'][sample],atol=1e-6,rtol=1e-6):raise ValueError('Fresh encoder replay differs')
    rows=[p for p in read_jsonl(pairs) if p['split']=='test'];pred=np.load(model/'test-scores.npz')
    slices={}
    for term in ('python','sql'):
        ix=[i for i,p in enumerate(rows) if technology_mentioned(p['need_text'],term)]
        slices[term]={n:evaluate([rows[i] for i in ix],pred[n][ix]) for n in (report['winner'],'word_cosine','e5_cosine')}
    result={'independent_retrieval_recalculation_equal':True,'retrieval_scores':recalculated,
            'random_tie_expected_recall_at100':float(np.mean([np.mean(v) for v in chance.values()])),
            'fresh_encoder_documents':len(sample),'fresh_encoder_max_abs_error':delta,
            'fresh_encoder_seconds':time.monotonic()-started,
            'descriptive_test_slices_not_used_for_selection':slices,
            'encoder_weights_finetuned':False,'production_promotion_allowed':False,
            'code_sha256':file_hash(Path(__file__))}
    write_json(out,result);print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('pairs','model','retrieval','encoder','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    with threadpool_limits(limits=2):check(a.pairs,a.model,a.retrieval,a.encoder,a.out)

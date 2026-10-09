"""Offline ranking for a trusted locally trained V3 artifact; never changes MVP grades."""
import argparse
import json
from pathlib import Path

import joblib

from prepare import clean
from rank_features import predict_artifact


def rank(artifact, candidates, need):
    need = clean(need)
    prepared, valid, results = [], [], []
    for i, candidate in enumerate(candidates):
        fields = {k:clean(candidate.get(k, '')) for k in
                  ('candidate_base_text','work_text','education_text')}
        fields['candidate_text'] = clean(' '.join(fields.values()))
        fields['need_text'] = need
        result = {'candidate_id':candidate.get('candidate_id',str(i)),
                  'observed_reply_score':None,'rank':None}
        if len(fields['candidate_text']) < 30 or len(need) < 60:
            result['status'] = 'insufficient_professional_text'
        else:
            valid.append(i)
            prepared.append(fields)
            result['status'] = 'scored_offline'
        results.append(result)
    if prepared:
        scores = predict_artifact(artifact, prepared)
        for i,score in zip(valid,scores):
            results[i]['observed_reply_score'] = float(score)
        # Stable ordering breaks ties only for display, not for evaluation metrics.
        for position,i in enumerate(sorted(valid,key=lambda i:-results[i]['observed_reply_score']),1):
            results[i]['rank'] = position
    return {'target':artifact['target'],'model_family':artifact['family'],
            'production_promotion_allowed':False,'results':results,
            'meaning':'Relative historical reply score; not a calibrated probability, verified skill or grade.'}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--candidates',type=Path,required=True,help='JSONL of candidate_id/base/work/education fields')
    p.add_argument('--need-file',type=Path,required=True)
    a=p.parse_args()
    # Pickle/joblib can execute code: only load artifacts produced and verified locally.
    artifact=joblib.load(a.model)
    candidates=[json.loads(line) for line in a.candidates.read_text().splitlines() if line.strip()]
    print(json.dumps(rank(artifact,candidates,a.need_file.read_text()),ensure_ascii=False,indent=2))

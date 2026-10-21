"""Reusable offline ranker: checked artifact, lazy encoder, no app DB writes."""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
from threadpoolctl import threadpool_limits
from enrich import file_hash,read_jsonl
from prepare import clean
from model_v4 import scores
from rank_features import interactions
from e5_local import LocalE5,pair_embeddings


class Ranker:
    def __init__(self,root,family=None,encoder_path=None,cache=None):
        root=Path(root);report=json.loads((root/'training-report.json').read_text())
        self.family=family or report['winner']
        if self.family=='job_only':raise ValueError('Job-only is a diagnostic control, not a candidate ranker')
        if self.family not in report['models']:raise ValueError('Unknown measured model')
        self.sha=report['models'][self.family];path=root/(self.family+'.joblib')
        if file_hash(path)!=self.sha:raise ValueError('Model checksum mismatch')
        # Only locally trained, trusted joblib artifacts are allowed.
        self.artifact=joblib.load(path);self.encoder_path=encoder_path;self.cache=cache;self.encoder=None

    def predict(self,need,candidates):
        ids=[c['candidate_id'] for c in candidates]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate candidate IDs')
        need=clean(need)
        if len(need)<60:raise ValueError('Need text must contain at least 60 characters')
        rows=[];missing=[]
        for c in candidates:
            base=clean(c.get('candidate_base_text',''));work=clean(c.get('work_text',''));edu=clean(c.get('education_text',''))
            text=clean(' '.join((base,work,edu)))
            if len(text)<30:missing.append({'candidate_id':c['candidate_id'],'score':None,'status':'insufficient_professional_text'})
            else:rows.append({'candidate_id':c['candidate_id'],'candidate_text':text,'need_text':need,'work_text':work,'education_text':edu})
        result=[]
        if rows:
            view=self.artifact['view'];features=self.artifact['features']
            if view in ('word_cosine','char_cosine','broad_cosine','word_pair','broad_pair'):
                vectorizer=getattr(features,view.split('_')[0])
                a=vectorizer.transform([p['candidate_text'] for p in rows]);b=vectorizer.transform([need]*len(rows))
                x=np.asarray(a.multiply(b).sum(axis=1)).ravel() if view.endswith('cosine') else interactions(a,b)
                views={view:x}
            else:
                if self.encoder is None:
                    if self.encoder_path is None:raise ValueError('This model requires the pinned local encoder')
                    self.encoder=LocalE5(self.encoder_path)
                    if self.encoder.manifest!=self.artifact['encoder_manifest']:raise ValueError('Encoder version mismatch')
                embeddings=pair_embeddings(self.encoder,rows,self.cache)
                views=features.transform(rows,embeddings)
            values=scores(self.artifact,views)
            result=[{'candidate_id':p['candidate_id'],'score':float(v),'status':'scored'} for p,v in zip(rows,values)]
        result.sort(key=lambda r:(-r['score'],str(r['candidate_id'])))
        meaning='text similarity, evaluated against historical replies' if self.artifact['model'] is None else 'relative historical reply score; not a probability or verified suitability'
        return {'model_version':'trudvsem-v4','family':self.family,'artifact_sha256':self.sha,
                'target':self.artifact['target'],'score_meaning':meaning,'production_promotion_allowed':False,
                'candidates':result+missing}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','need','candidates'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--family');p.add_argument('--encoder',type=Path);p.add_argument('--cache',type=Path)
    a=p.parse_args()
    with threadpool_limits(limits=2):
        ranker=Ranker(a.root,a.family,a.encoder,a.cache)
        print(json.dumps(ranker.predict(a.need.read_text(),read_jsonl(a.candidates)),ensure_ascii=False,indent=2))

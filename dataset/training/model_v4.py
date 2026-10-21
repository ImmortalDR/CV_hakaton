"""Offline V4 features and reusable ranking interface; no verified-grade inference."""
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from rank_features import lexical_features,interactions as sparse_interactions
from e5_local import interactions as embedding_interactions,LocalE5,pair_embeddings


class Features:
    def fit(self,rows,corpus):
        docs=sorted({p[k] for p in rows for k in ('candidate_text','need_text')})
        self.word=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_features=16000,sublinear_tf=True,dtype=np.float32).fit(docs)
        self.char=TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),min_df=2,max_features=16000,sublinear_tf=True,dtype=np.float32).fit(docs)
        self.broad=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_features=24000,sublinear_tf=True,dtype=np.float32).fit(sorted(set(docs)|set(corpus)))
        return self

    def transform(self,rows,emb):
        a,b=emb
        cs=[p['candidate_text'] for p in rows];js=[p['need_text'] for p in rows]
        wa,wb=self.word.transform(cs),self.word.transform(js)
        ca,cb=self.char.transform(cs),self.char.transform(js)
        ba,bb=self.broad.transform(cs),self.broad.transform(js)
        cos=lambda x,y:np.asarray(x.multiply(y).sum(axis=1)).ravel()
        wc,cc,bc=cos(wa,wb),cos(ca,cb),cos(ba,bb);ec=(a*b).sum(axis=1)
        dense=np.column_stack([wc,cc,bc,ec,np.asarray([lexical_features(x,y) for x,y in zip(cs,js)])])
        for field in ('work_text','education_text'):
            dense=np.column_stack([dense,np.asarray([lexical_features(p.get(field,''),p['need_text']) for p in rows])])
        e=embedding_interactions(a,b)
        return {'word_cosine':wc,'char_cosine':cc,'broad_cosine':bc,'e5_cosine':ec,
                'word_pair':sparse_interactions(wa,wb),'broad_pair':sparse_interactions(ba,bb),
                'e5_pair':e,'dense':dense,'job_only':wb,
                'hybrid_pair':sparse.hstack([sparse_interactions(wa,wb),sparse.csr_matrix(e),sparse.csr_matrix(dense)],format='csr')}


def scores(artifact,views):
    view=views[artifact['view']]
    if artifact['model'] is None:return view
    if artifact.get('scaler') is not None:view=artifact['scaler'].transform(view)
    model=artifact['model']
    if hasattr(model,'decision_function'):return model.decision_function(view)
    return model.predict(view)


def rank(artifact,need,candidates,encoder_path):
    from prepare import clean
    ids=[p['candidate_id'] for p in candidates]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate candidate IDs')
    if len(clean(need))<60:raise ValueError('Need text must contain at least 60 characters')
    valid=[];missing=[]
    for c in candidates:
        base=clean(c.get('candidate_base_text',''));work=clean(c.get('work_text',''));edu=clean(c.get('education_text',''))
        text=clean(' '.join((base,work,edu)))
        if len(text)<30:
            missing.append({'candidate_id':c['candidate_id'],'score':None,'status':'insufficient_professional_text'})
        else:valid.append({'candidate_id':c['candidate_id'],'candidate_text':text,'need_text':clean(need),'work_text':work,'education_text':edu})
    result=[]
    if valid:
        encoder=LocalE5(encoder_path)
        if encoder.manifest!=artifact['encoder_manifest']:raise ValueError('Wrong encoder version')
        view=artifact['features'].transform(valid,pair_embeddings(encoder,valid))
        result=[{'candidate_id':p['candidate_id'],'score':float(s),'status':'scored'} for p,s in zip(valid,scores(artifact,view))]
    result.sort(key=lambda r:(-r['score'],str(r['candidate_id'])))
    return {'model_version':'trudvsem-v4','target':artifact['target'],'production_promotion_allowed':False,
            'score_meaning':'relative historical reply score, not probability/competence/grade',
            'candidates':result+missing}

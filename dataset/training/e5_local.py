"""Pinned local ONNX E5, no network/token/env use. Long documents use all chunks."""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
import sqlite3
import time
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from enrich import file_hash


def normalize(x):
    return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-12)


class LocalE5:
    def __init__(self, root):
        root=Path(root)
        self.manifest=json.loads((root/'manifest.json').read_text())
        for name,info in self.manifest['files'].items():
            if file_hash(root/name)!=info['sha256']:raise ValueError('Encoder checksum mismatch')
        self.tokenizer=Tokenizer.from_file(str(root/'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=256,stride=32)
        opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(root/'onnx/model_int8.onnx'),sess_options=opts,providers=['CPUExecutionProvider'])
        self.inputs={i.name for i in self.session.get_inputs()}
        self.stats={'documents':0,'chunks':0,'seconds':0.}

    def encode(self,texts,role='passage'):
        if role not in ('query','passage'):raise ValueError('Unsupported E5 prefix')
        start=time.monotonic();out=[]
        for text in texts:
            e=self.tokenizer.encode(role+': '+text)
            chunks=[e]+e.overflowing
            vectors=[]
            for offset in range(0,len(chunks),4):
                batch=chunks[offset:offset+4];size=max(len(x.ids) for x in batch)
                ids=np.zeros((len(batch),size),dtype=np.int64);mask=np.zeros_like(ids)
                for i,t in enumerate(batch):ids[i,:len(t.ids)]=t.ids;mask[i,:len(t.ids)]=1
                feed={'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)}
                hidden=self.session.run(None,{k:v for k,v in feed.items() if k in self.inputs})[0]
                pooled=(hidden*mask[:,:,None]).sum(axis=1)/np.maximum(mask.sum(axis=1)[:,None],1)
                vectors.extend(normalize(pooled))
            out.append(normalize(np.mean(vectors,axis=0)).astype(np.float32))
            self.stats['chunks']+=len(chunks)
        self.stats['documents']+=len(texts);self.stats['seconds']+=time.monotonic()-start
        return np.asarray(out,dtype=np.float32).reshape(len(texts),384)


def cached_encode(encoder,texts,role,cache_path):
    """Commit small batches so an interrupted CPU run does not lose its work."""
    cache_path=Path(cache_path);cache_path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(cache_path)
    db.execute('CREATE TABLE IF NOT EXISTS embeddings(key TEXT PRIMARY KEY,vector BLOB)')
    version=json.dumps(encoder.manifest,sort_keys=True)+'|chunks256-overlap32-mean-normalized-v1|'+role
    keys=[hashlib.sha256((version+'|'+t).encode()).hexdigest() for t in texts]
    result={};missing=[]
    for i,k in enumerate(keys):
        r=db.execute('SELECT vector FROM embeddings WHERE key=?',(k,)).fetchone()
        if r:
            a=np.frombuffer(r[0],dtype=np.float32).copy()
            if a.shape!=(384,) or not np.isfinite(a).all():raise ValueError('Corrupt embedding cache')
            result[i]=a
        else:missing.append(i)
    for start in range(0,len(missing),10):
        ix=missing[start:start+10];vectors=encoder.encode([texts[i] for i in ix],role=role)
        for i,v in zip(ix,vectors):
            result[i]=v;db.execute('INSERT OR REPLACE INTO embeddings VALUES(?,?)',(keys[i],v.astype(np.float32).tobytes()))
        db.commit()
        if start%100==0 or start+10>=len(missing):
            print(json.dumps({'e5_role':role,'encoded_new':min(start+10,len(missing)),'new_total':len(missing),'cache_hits':len(texts)-len(missing)}),flush=True)
    db.close()
    return np.asarray([result[i] for i in range(len(texts))],dtype=np.float32).reshape(len(texts),384)


def pair_embeddings(encoder,rows,cache_path=None):
    docs=sorted({p['candidate_text'] for p in rows});needs=sorted({p['need_text'] for p in rows})
    encode=lambda ts,role:cached_encode(encoder,ts,role,cache_path) if cache_path else encoder.encode(ts,role=role)
    cm=dict(zip(docs,encode(docs,'passage')));jm=dict(zip(needs,encode(needs,'query')))
    a=np.stack([cm[p['candidate_text']] for p in rows]);b=np.stack([jm[p['need_text']] for p in rows])
    return a,b


def interactions(a,b):
    return np.concatenate([a*b,abs(a-b),(a*b).sum(axis=1)[:,None]],axis=1)

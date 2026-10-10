"""Pinned local ONNX E5, no network/token/env use. Long documents use all chunks."""
from __future__ import annotations
import json
from pathlib import Path
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


def pair_embeddings(encoder,rows):
    docs=sorted({p['candidate_text'] for p in rows});needs=sorted({p['need_text'] for p in rows})
    cm=dict(zip(docs,encoder.encode(docs)));jm=dict(zip(needs,encoder.encode(needs,role='query')))
    a=np.stack([cm[p['candidate_text']] for p in rows]);b=np.stack([jm[p['need_text']] for p in rows])
    return a,b


def interactions(a,b):
    return np.concatenate([a*b,abs(a-b),(a*b).sum(axis=1)[:,None]],axis=1)

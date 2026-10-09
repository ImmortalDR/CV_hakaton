"""Local train-only text features; no labels, identifiers or inferred grades."""
from __future__ import annotations
import re
import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from prepare import clean

TECH = {
    'python': r'python|питон', 'sql': r'sql|postgresql|mysql|mssql|t-sql',
    'java': r'java', 'javascript': r'javascript|js|typescript', 'csharp': r'c#|csharp|\.net',
    'cpp': r'c\+\+', 'php': r'php', 'one_c': r'1с|1c',
    'linux': r'linux|ubuntu|debian|centos', 'windows': r'windows',
    'git': r'git|github|gitlab', 'docker': r'docker|контейнеризац\w*',
    'kubernetes': r'kubernetes|k8s', 'react': r'react', 'vue': r'vue',
    'django': r'django', 'flask': r'flask', 'pandas': r'pandas',
    'excel': r'excel', 'powerbi': r'power\s*bi', 'spark': r'spark',
    'hadoop': r'hadoop', 'testing': r'тестирован\w*|pytest|selenium|junit',
    'network': r'сет\w*|tcp|dns|dhcp', 'html': r'html|css',
    'rest': r'rest|api', 'ml': r'machine\s+learning|машинн\w*\s+обучен\w*',
}
TECH_RE = [re.compile(r'(?<!\w)(?:' + x + r')(?!\w)', re.I) for x in TECH.values()]


def tech_vector(text):
    return np.asarray([bool(r.search(text)) for r in TECH_RE], dtype=float)


def cosine(a, b):
    return np.asarray(a.multiply(b).sum(axis=1)).ravel()


def interactions(a, b):
    return sparse.hstack([a.multiply(b), abs(a-b), sparse.csr_matrix(cosine(a, b)[:, None])], format='csr')


def lexical_features(a, b):
    aa, bb = set(re.findall(r'\w+', a)), set(re.findall(r'\w+', b))
    common = aa & bb
    ta, tb = tech_vector(a), tech_vector(b)
    return [len(common)/max(1, len(bb)), len(common)/max(1, len(aa)),
            len(common)/max(1, len(aa | bb)),
            np.log1p(len(aa)), np.log1p(len(bb)),
            float((ta*tb).sum())/max(1., tb.sum()),
            float(((1-ta)*tb).sum())/max(1., tb.sum()),
            float(tb.sum() > 0), float(ta.sum() > 0)]


class Encoder:
    def fit(self, rows):
        self.base = TfidfVectorizer(ngram_range=(1,2), min_df=2, max_features=12000, sublinear_tf=True)
        self.word = TfidfVectorizer(ngram_range=(1,2), min_df=2, max_features=16000, sublinear_tf=True)
        self.char = TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), min_df=2,
                                    max_features=24000, sublinear_tf=True)
        self.base.fit(sorted({clean(p[k]) for p in rows for k in ('candidate_base_text','need_text')}))
        docs = sorted({clean(p[k]) for p in rows for k in ('candidate_text','need_text')})
        self.word.fit(docs)
        self.char.fit(docs)
        self.scaler = StandardScaler().fit(self.dense(rows))
        return self

    def dense(self, rows):
        needs = [clean(p['need_text']) for p in rows]
        wj, cj = self.word.transform(needs), self.char.transform(needs)
        blocks = []
        for field in ('candidate_base_text', 'candidate_text', 'work_text', 'education_text'):
            texts = [clean(p.get(field, '')) for p in rows]
            wc, cc = self.word.transform(texts), self.char.transform(texts)
            # IDF-weighted directional coverage, stable for zero vectors.
            denom = np.asarray(abs(wj).sum(axis=1)).ravel()
            coverage = np.asarray(wj.multiply(wc.sign()).sum(axis=1)).ravel()/np.maximum(denom, 1e-12)
            blocks.append(np.column_stack([cosine(wc,wj), cosine(cc,cj), coverage,
                                          np.asarray([lexical_features(a,b) for a,b in zip(texts, needs)])]))
        return np.hstack(blocks)

    def transform(self, rows):
        base = self.base.transform([clean(p['candidate_base_text']) for p in rows])
        bj = self.base.transform([clean(p['need_text']) for p in rows])
        wc = self.word.transform([clean(p['candidate_text']) for p in rows])
        wj = self.word.transform([clean(p['need_text']) for p in rows])
        cc = self.char.transform([clean(p['candidate_text']) for p in rows])
        cj = self.char.transform([clean(p['need_text']) for p in rows])
        dense = self.scaler.transform(self.dense(rows))
        enriched = interactions(wc,wj)
        return {
            'base_pair': interactions(base,bj), 'enriched_word': enriched,
            'dual_pair': sparse.hstack([enriched, interactions(cc,cj), sparse.csr_matrix(dense)], format='csr'),
            'dense_pair': dense,
            'job_only': sparse.hstack([wj,cj], format='csr'),
            'candidate_only': sparse.hstack([wc,cc], format='csr'),
            'base_cosine': cosine(base,bj), 'enriched_cosine': cosine(wc,wj),
            'char_cosine': cosine(cc,cj),
        }


def predict_artifact(artifact, rows):
    return artifact['model'].decision_function(artifact['encoder'].transform(rows)[artifact['view']]) \
        if hasattr(artifact['model'], 'decision_function') else \
        artifact['model'].predict_proba(artifact['encoder'].transform(rows)[artifact['view']])[:,1]

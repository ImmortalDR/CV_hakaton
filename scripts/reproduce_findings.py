from pathlib import Path
from types import SimpleNamespace as N
from uuid import uuid4
import argparse, ast, collections, csv, hashlib, json, math, re
from enum import StrEnum

parser=argparse.ArgumentParser(description='Isolated probes of archived source functions, not application tests')
default_source=Path(__file__).resolve().parents[1]/'Архив исходников для MVP обратного найма ФСП'
if (default_source/'fsp_mvp_bundle/github').is_dir():
    default_source=default_source/'fsp_mvp_bundle'
parser.add_argument('--source-root',type=Path,default=default_source)
parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'audit/reproduced_findings.json')
args=parser.parse_args()
ROOT=args.source_root.resolve()
results={}
score_path=ROOT/'github/ai-resume-screener-ats-platform/backend/resume_screener/application/scoring.py'
tree=ast.parse(score_path.read_text())
selected=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]
selected += [n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('TOKEN_PATTERN','RRF_K') for t in n.targets)]
selected += [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('score_candidate','cosine')]
Kind=StrEnum('CriterionKind', {'MUST_HAVE':'must_have','NICE_TO_HAVE':'nice_to_have'})
ns={'re':re,'math':math,'CriterionKind':Kind, 'assert_registered_features':lambda features:None}
exec(compile(ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[])),str(score_path),'exec'),ns)
def run_score(candidate_years,required_years):
    c=N(id=uuid4(),years_experience=candidate_years)
    r=N(id=uuid4(),matching_text='Python')
    p=N(skill_slugs=['python'],extraction_confidence=1)
    criterion=N(id=uuid4(),skill_slug='python',minimum_years=required_years,kind=Kind.MUST_HAVE,weight=1,label='Python experience')
    return ns['score_candidate'](c,r,p,[1.0],[criterion],'Python',{'python'},[1.0],{},1,rerank_override=0.0)
results['unknown_experience_counted_as_met']=run_score(None,5)[4]
try:
    run_score(0,0)
    results['zero_year_requirement']='no error'
except Exception as e:
    results['zero_year_requirement']=type(e).__name__+': '+str(e)
results['cyrillic_tokens']=ns['TOKEN_PATTERN'].findall('Разработка серверных приложений, анализ данных')

nb=json.loads((ROOT/'kaggle/siddigantm__task-resume-matching-with-job-descriptions.ipynb').read_text())
code='\n'.join(''.join(c.get('source',[])) for c in nb['cells'] if 'def get_embeddings' in ''.join(c.get('source',[])))
node=next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name=='get_embeddings')
fake_tokenizer=N(from_pretrained=lambda _:lambda *args,**kwargs:N(to=lambda x:x))
emb_ns={'AutoTokenizer':fake_tokenizer}
exec(compile(ast.Module(body=[node],type_ignores=[]),'get_embeddings','exec'),emb_ns)
try:
    emb_ns['get_embeddings']('Python','unused')
    results['notebook_embedding_scope']='no error'
except Exception as e:
    results['notebook_embedding_scope']=type(e).__name__+': '+str(e)
keys=[i+j for i in range(15) for j in range(5)]
results['notebook_result_key_collision_example']={'expected_rows':len(keys),'retained_keys':len(set(keys))}

import numpy as np
from sklearn.model_selection import GroupShuffleSplit
ids=np.repeat(np.arange(100),5)
df_groups=np.arange(len(ids)) # Notebook drops idCv and consequently uses this fallback.
train,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42).split(ids,groups=df_groups))
results['notebook_grouping_probe']={'overlapping_candidates':len(set(ids[train])&set(ids[test])), 'test_candidates':len(set(ids[test]))}

data=list(csv.DictReader((ROOT/'kaggle/resume-dataset-souptikghosh/resume_dataset_2.csv').open()))
results['kaggle_dataset']={'rows':len(data),'columns':list(data[0]),'roles':dict(collections.Counter(r['Job_Role'] for r in data)), 'duplicate_rows':len(data)-len({json.dumps(r,sort_keys=True) for r in data}), 'unique_resume_texts':len({r['Resume_Text'] for r in data})}
out=args.out.resolve()
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))

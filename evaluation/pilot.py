"""Prepare frozen anonymous pilot forms and evaluate actual submitted responses.

No invented observations, network access or application database writes.
Use an ignored local output directory for any participant data.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from fsp import bank


PEOPLE_COLUMNS = ['participant_id','specialization','grade','independent_expected_pass','label_source']
RESPONSE_COLUMNS = ['participant_id','form_id','question_id','answer']


def write_json(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def prepare(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('Pilot output must be empty; frozen forms and responses must not be overwritten')
    public, private = [], []
    for spec,grade in bank.BLUEPRINT:
        for form in ['A','B']:
            qs=bank.generate(spec,grade,f'human-pilot-v2-{form}',version=bank.VERSION)
            record=dict(form_id=f'{spec}-{grade}-{form}',specialization=spec,grade=grade,version=bank.VERSION,
                        rubric=bank.rubric(),fingerprint=bank.fingerprint(qs))
            public.append(record|dict(questions=[{k:q[k] for k in ['id','skill','text']} for q in qs]))
            private.append(record|dict(questions=qs))
    write_json(out/'forms.json',public)
    write_json(out/'answer-key.json',private)
    (out/'answer-key.json').chmod(0o600)
    for name,columns in [('participants.csv',PEOPLE_COLUMNS),('responses.csv',RESPONSE_COLUMNS)]:
        with (out/name).open('w',newline='') as f:
            csv.writer(f).writerow(columns)
    with (out/'expert-review.csv').open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['family','specialization','proposed_grade','content_correct','grade_appropriate','ambiguity','reviewer_code','notes'])
        for (spec,grade),families in bank.BLUEPRINT.items():
            for family in families: writer.writerow([family,spec,grade,'','','','',''])
    write_json(out/'manifest.json',dict(version=bank.VERSION,
        forms_sha256=hashlib.sha256((out/'forms.json').read_bytes()).hexdigest(),
        key_sha256=hashlib.sha256((out/'answer-key.json').read_bytes()).hexdigest(),
        bank_sha256=hashlib.sha256(Path(bank.__file__).read_bytes()).hexdigest(),
        real_participants=0))
    return dict(forms=len(public),families=len(bank.FAMILY_SKILL),participants=0)


def read_csv(path, columns):
    with Path(path).open(newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=columns: raise ValueError(f'Unexpected columns in {Path(path).name}')
        rows=list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError('Malformed CSV row')
        return rows


def evaluate(root):
    root=Path(root)
    manifest=json.loads((root/'manifest.json').read_text())
    for name,key in [('forms.json','forms_sha256'),('answer-key.json','key_sha256')]:
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=manifest[key]:
            raise ValueError(f'Frozen {name} was modified')
    if hashlib.sha256(Path(bank.__file__).read_bytes()).hexdigest()!=manifest['bank_sha256']:
        raise ValueError('Scoring code changed since forms were frozen; use the original version')
    forms={f['form_id']:f for f in json.loads((root/'answer-key.json').read_text())}
    people={}
    for p in read_csv(root/'participants.csv',PEOPLE_COLUMNS):
        pid=p['participant_id']
        if not pid or pid in people: raise ValueError('Empty or duplicate participant ID')
        if (p['specialization'],p['grade']) not in bank.BLUEPRINT: raise ValueError('Unknown category')
        if p['independent_expected_pass'] not in ['', 'true','false']: raise ValueError('Expected label must be true, false or blank')
        if p['independent_expected_pass'] and not p['label_source'].strip(): raise ValueError('Independent labels need a source')
        people[pid]=p
    attempts=defaultdict(dict)
    for r in read_csv(root/'responses.csv',RESPONSE_COLUMNS):
        pid,fid,qid=r['participant_id'],r['form_id'],r['question_id']
        if pid not in people or fid not in forms: raise ValueError('Unknown participant or form')
        p,f=people[pid],forms[fid]
        if (p['specialization'],p['grade'])!=(f['specialization'],f['grade']): raise ValueError('Participant/form category mismatch')
        if qid not in {q['id'] for q in f['questions']}: raise ValueError('Unknown question')
        if qid in attempts[pid,fid]: raise ValueError('Duplicate response')
        attempts[pid,fid][qid]=r['answer']
    outcomes,items=defaultdict(list),defaultdict(lambda:defaultdict(list))
    matrix=Counter()
    records=[]
    for (pid,fid),answers in sorted(attempts.items()):
        f=forms[fid]
        if set(answers)!={q['id'] for q in f['questions']}: raise ValueError('Incomplete attempt; submit explicit blank answers')
        result=bank.grade_answers(f['questions'],answers,version=f['version'])
        p=people[pid]
        expected={'true':True,'false':False,'':None}[p['independent_expected_pass']]
        if expected is not None: matrix[expected,result['passed']]+=1
        outcomes[pid].append(result['passed'])
        records.append(dict(participant_id=pid,form_id=fid,score=result['score'],passed=result['passed'],expected=expected))
        for q,d in zip(f['questions'],result['details']):
            if expected is not None: items[q['family']][expected].append(int(d['correct']))
    repeated=[ys for ys in outcomes.values() if len(ys)==2]
    judged=sum(matrix.values())
    return dict(status='measured' if records else 'not_run',participants_observed=len(outcomes),attempts=len(records),
        labels_used=judged,agreement_with_independent_labels=sum(n for (e,a),n in matrix.items() if e==a)/judged if judged else None,
        confusion=[dict(expected=e,actual=a,n=n) for (e,a),n in sorted(matrix.items())],
        paired_people=len(repeated),paired_agreement=mean(a==b for a,b in repeated) if repeated else None,
        family_discrimination=[dict(family=f,strong_n=len(g[True]),weak_n=len(g[False]),
            strong_minus_weak=mean(g[True])-mean(g[False]) if g[True] and g[False] else None) for f,g in sorted(items.items())],
        results=records,limitations=['No conclusion without actual independent labels.',
            'Repeated forms share a participant; item observations are not independent people.',
            'No automatic reassignment of professional grade; pilot is separate from the application.'])


def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['prepare','evaluate'])
    p.add_argument('--root',type=Path,default=Path('audit/human-pilot-v2'))
    a=p.parse_args()
    result=prepare(a.root) if a.command=='prepare' else evaluate(a.root)
    if a.command=='evaluate': write_json(a.root/'results.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))

if __name__=='__main__': main()

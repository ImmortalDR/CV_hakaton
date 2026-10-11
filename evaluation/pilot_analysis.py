"""Participant-level analysis of actual frozen pilot forms; never invent observations."""
import argparse
import csv
import json
import math
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

from .pilot import evaluate, read_csv, RESPONSE_COLUMNS
from fsp import bank

SESSION_COLUMNS = ['participant_id','form_id','started_at','submitted_at']


def interval(values, repeats=2000):
    if len(values) < 2: return None
    rng=random.Random(20261011)
    means=sorted(mean(rng.choices(values,k=len(values))) for _ in range(repeats))
    return [means[int(.025*repeats)],means[int(.975*repeats)]]


def correlation(x,y):
    if len(x)<3: return None
    mx,my=mean(x),mean(y)
    numerator=sum((a-mx)*(b-my) for a,b in zip(x,y))
    denominator=math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
    return numerator/denominator if denominator else None


def analyse(root):
    root=Path(root); base=evaluate(root)
    byperson=defaultdict(list)
    for r in base['results']: byperson[r['participant_id']].append(r)
    paired=[sorted(rs,key=lambda r:r['form_id']) for rs in byperson.values() if len(rs)==2]
    agreement=[int(a['passed']==b['passed']) for a,b in paired]
    forms={f['form_id']:f for f in json.loads((root/'answer-key.json').read_text())}
    answers=defaultdict(dict)
    for row in read_csv(root/'responses.csv',RESPONSE_COLUMNS):
        answers[row['participant_id'],row['form_id']][row['question_id']]=row['answer']
    # Only first form per person/category: do not count repeats as independent people.
    categories=defaultdict(list)
    for pid,rs in byperson.items():
        record=min(rs,key=lambda r:r['form_id']);f=forms[record['form_id']]
        result=bank.grade_answers(f['questions'],answers[pid,f['form_id']],version=f['version'])
        categories[f['specialization'],f['grade']].append((f,result,record['expected']))
    families=[]
    for category,people in sorted(categories.items()):
        allfamilies=sorted({q['family'] for f,_,_ in people for q in f['questions']})
        for family in allfamilies:
            own,rest,strong,weak=[],[],[],[]
            for f,result,expected in people:
                pairs=list(zip(f['questions'],result['details']))
                score=mean(int(d['correct']) for q,d in pairs if q['family']==family)
                remainder=mean(int(d['correct']) for q,d in pairs if q['family']!=family)
                own.append(score);rest.append(remainder)
                if expected is True: strong.append(score)
                elif expected is False: weak.append(score)
            families.append(dict(specialization=category[0],grade=category[1],family=family,
                participants=len(own),corrected_family_rest_correlation=correlation(own,rest),
                strong_n=len(strong),weak_n=len(weak),strong_minus_weak=mean(strong)-mean(weak) if strong and weak else None))
    timings={}
    session_path=root/'sessions.csv'
    if session_path.exists():
        for row in read_csv(session_path,SESSION_COLUMNS):
            key=row['participant_id'],row['form_id']
            if key not in answers or key in timings: raise ValueError('Unknown or duplicate session')
            start,end=[datetime.fromisoformat(row[k]) for k in ['started_at','submitted_at']]
            if not start.tzinfo or not end.tzinfo or end<start: raise ValueError('Session requires ordered timezone-aware dates')
            timings[key]=start,end
    gaps=[]
    for pair in paired:
        keys=[(r['participant_id'],r['form_id']) for r in pair]
        if all(k in timings for k in keys):
            first,second=sorted([timings[k] for k in keys])
            if second[0]<first[1]: raise ValueError('Repeated sessions overlap')
            gaps.append((second[0]-first[1]).total_seconds()/3600)
    review_path=root/'expert-review.csv'
    reviews=list(csv.DictReader(review_path.open())) if review_path.exists() else []
    reviewed=[r for r in reviews if r.get('reviewer_code','').strip() and r.get('content_correct') in ('true','false') and r.get('grade_appropriate') in ('true','false')]
    return dict(status=base['status'],participants=base['participants_observed'],paired_people=len(paired),
        recorded_sessions=len(timings),recorded_retest_intervals=len(gaps),
        retest_interval_hours_mean=mean(gaps) if gaps else None,
        paired_agreement=mean(agreement) if agreement else None,paired_agreement_ci95=interval(agreement),
        score_retest_correlation=correlation([a['score'] for a,b in paired],[b['score'] for a,b in paired]),
        absolute_score_change_mean=mean(abs(a['score']-b['score']) for a,b in paired) if paired else None,
        expert_families_reviewed=len({r['family'] for r in reviewed}),expert_families_total=len(bank.FAMILY_SKILL),
        expert_flags=[dict(family=r['family'],reviewer=r['reviewer_code'],content_correct=r['content_correct'],grade_appropriate=r['grade_appropriate']) for r in reviewed if r['content_correct']=='false' or r['grade_appropriate']=='false'],
        family_analysis=families,source_metrics={k:v for k,v in base.items() if k!='results'},
        limitations=['No participants or independent labels are manufactured.',
                    'Bootstrap resamples people; small samples do not establish professional validity.',
                    'Family/rest analysis uses first form per person within specialization/grade.',
                    'Pearson retest coefficient is descriptive; timing and outside help require a separate session log.',
                    'Reviewer identity and independence require human verification; a non-empty source field is not certification.'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    result=analyse(a.root);(a.root/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['family_analysis','source_metrics']},ensure_ascii=False))


if __name__=='__main__':main()

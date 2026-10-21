"""Separate deterministic synthetic A/B participants, not observed people."""
import itertools
import json
import random
from pathlib import Path
from fsp import bank
from evaluation.bank_v2_audit import audit, wilson


def retest():
    rows=[]
    for spec,grade in bank.BLUEPRINT:
        for slip in [.1,.2]:
            pairs=[]
            for person in range(200):
                outcomes=[]
                for form in ['A','B']:
                    qs=bank.generate(spec,grade,f'final-retest-{person}-{form}')
                    rng=random.Random(f'final-responses-{spec}-{grade}-{slip}-{person}-{form}')
                    answers={q['id']:q['answer'] if rng.random()>=slip else 'не знаю' for q in qs}
                    outcomes.append(bank.grade_answers(qs,answers)['passed'])
                pairs.append(outcomes)
            agreement=sum(a==b for a,b in pairs)
            rows.append(dict(specialization=spec,grade=grade,slip_probability=slip,synthetic_pairs=len(pairs),
                             agreement=agreement/len(pairs),wilson95=wilson(agreement,len(pairs)),
                             pass_a=sum(a for a,b in pairs)/len(pairs),pass_b=sum(b for a,b in pairs)/len(pairs)))
    return rows


def boundary():
    rows=[]
    for spec,grade in bank.BLUEPRINT:
        qs=bank.generate(spec,grade,'final-boundary')
        core='python' if spec=='python' else 'sql'
        for mask in itertools.product([False,True],repeat=8):
            answers={q['id']:q['answer'] for q,yes in zip(qs,mask) if yes}
            expected=sum(mask)>=6 and sum(yes and q['skill']==core for q,yes in zip(qs,mask))>=3
            actual=bank.grade_answers(qs,answers)['passed']
            if actual!=expected: rows.append(dict(spec=spec,grade=grade,mask=mask))
    return dict(masks_checked=6*256,mismatches=rows)


if __name__=='__main__':
    result=dict(version=bank.VERSION,kind='synthetic_not_human',bank_comparison=audit(),paired_retest=retest(),boundary=boundary(),
                real_participants=0,human_test_retest='not_run',empirical_discrimination='not_run',
                limitations=['Synthetic participants assume fixed knowledge and independent slips.',
                             'A/B pairs are independent simulated units; no all-pairs reuse.',
                             'Intervals quantify this model only, not professional-grade validity.'])
    out=Path('docs/delivery/evidence/final_2026-10-21/assessment.json')
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(version=bank.VERSION,oracles=result['bank_comparison']['oracle_checks'],oracle_mismatches=len(result['bank_comparison']['oracle_mismatches']),boundary=result['boundary'],synthetic_pairs=sum(r['synthetic_pairs'] for r in result['paired_retest'])),ensure_ascii=False))

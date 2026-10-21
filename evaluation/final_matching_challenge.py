"""Frozen author scenarios; diagnostics and invariants, never a hiring benchmark.

No fitting, no change to old labels/weights. Policy: total score within category;
partial matches are permitted but must be explicitly marked (user 2026-10-21).
"""
import hashlib
import itertools
import json
from pathlib import Path
from fsp.matching import VERSION, eligible, group_sort, rank_candidate
from evaluation.stage_a_matching import OLD, score

FIXTURE = Path('evaluation/final_matching_challenge.json')


def evaluate():
    data = json.loads(FIXTURE.read_text())
    rows = []
    assertions = []
    for case in data['cases']:
        criteria = case['criteria']
        candidates = case['candidates']
        pool = [dict(p, match=rank_candidate(p, criteria)) for p in candidates if eligible(p, criteria)]
        current = group_sort(pool)
        previous = group_sort([dict(p, match={'score': score(p, criteria, OLD)}) for p in pool])
        old_ids = [p['id'] for p in previous]
        ids = [p['id'] for p in current]
        lookup = {p['id']: p for p in current}
        changed_pairs = [(a, b) for a, b in itertools.combinations(ids, 2)
                         if old_ids.index(a) > old_ids.index(b)]
        for rule in case['assertions']:
            kind, a, *rest = rule
            if kind == 'before': ok = ids.index(a) < ids.index(rest[0])
            elif kind == 'equal': ok = lookup[a]['match']['score'] == lookup[rest[0]]['match']['score']
            elif kind == 'excluded': ok = a not in ids
            elif kind == 'missing': ok = rest[0] in lookup[a]['match']['missing_skills']
            elif kind == 'unmet': ok = rest[0] in lookup[a]['match']['unmet_skills']
            elif kind == 'zero_fsp': ok = lookup[a]['match']['breakdown']['fsp'] == 0
            elif kind == 'no_full': ok = all(not p['match']['required_skills_met'] for p in current)
            else: raise ValueError(kind)
            assertions.append(dict(case=case['id'], rule=rule, passed=ok))
        top = current[:5]
        rows.append(dict(case=case['id'], rationale=case['rationale'], old_order=old_ids, current_order=ids,
                         changed_pairs=changed_pairs, eligible=len(pool),
                         full_match_count=sum(p['match']['required_skills_met'] for p in current),
                         partial_top_fraction=sum(not p['match']['required_skills_met'] for p in top)/len(top) if top else None,
                         scores=[dict(id=p['id'], grade=p['verified_grade'], **p['match']) for p in current]))
    # Metamorphic checks: strengthen one evidence component; score must not decrease.
    for case in data['cases']:
        for p in case['candidates']:
            base = rank_candidate(p, case['criteria'])['score']
            stronger = dict(p, test_score=min(100, p['test_score']+5))
            assertions.append(dict(case=case['id'], rule=['test_monotonicity',p['id']], passed=rank_candidate(stronger,case['criteria'])['score'] >= base))
            changed_self = dict(p, skills=['python','http','testing'], experience_years=59)
            assertions.append(dict(case=case['id'], rule=['self_report_no_score',p['id']], passed=rank_candidate(changed_self,case['criteria'])['score'] == base))
    return dict(kind='author_scenarios_not_external_validation', methodology=VERSION,
                fixture_sha256=hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
                policy=data['policy'], cases=rows, assertions=assertions,
                passed=all(a['passed'] for a in assertions),
                changed_pairs=sum(len(r['changed_pairs']) for r in rows),
                precision_at_5=None, ndcg_at_5=None,
                limitations=['No independent relevance labels; P@5/NDCG are intentionally not computed.',
                             'Small designed scenarios detect tradeoffs, not market quality or statistical uplift.',
                             'No fitting on this set. Original holdout and labels unchanged.',
                             'Grade grouping precedes numeric score; no cross-grade score comparisons.'])


if __name__ == '__main__':
    r=evaluate()
    Path('evaluation/final_matching_challenge_results.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['passed','changed_pairs','methodology']},ensure_ascii=False))
    if not r['passed']: raise SystemExit(1)

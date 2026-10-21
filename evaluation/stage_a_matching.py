"""Dev-only weight selection against frozen author-labelled fixtures.

No human expert validation is claimed. Holdout is evaluated only after selection.
"""
import hashlib
import json
from pathlib import Path
from statistics import mean
from fsp.matching import eligible, rank_candidate

FIXTURE = Path('evaluation/matching_fixtures.json')
OLD = (60, 15, 20, 5)


def score(p, q, weights):
    # Obtain evidence fractions independently of the production weight values.
    ev = {e['skill']: e['state'] for e in p.get('evidence', [])}
    ratios = [sum(ev.get(s) == 'met' for s in q.get(k, [])) / len(q[k]) if q.get(k) else 0
              for k in ['required_skills', 'desired_skills']]
    sport = min(5, sum(a.get('points', 0) for a in p.get('achievements', []) if a.get('provider') == 'demo_fsp')) / 5
    return sum(x*y for x,y in zip(weights, [*ratios, p.get('test_score', 0)/100, sport]))


def measure(data, weights):
    rows = []
    for q in data['queries']:
        pool = [p for p in data['candidates'] if eligible(p, q['criteria'])]
        ranked = sorted(pool, key=lambda p: (-score(p, q['criteria'], weights), p['id']))[:5]
        ids = [p['id'] for p in ranked]
        rows.append(dict(query=q['id'], top5=ids, p_at_5=len(set(ids) & set(q['relevant_ids']))/5))
    return dict(candidates=len(data['candidates']), queries=len(rows), p_at_5=mean(r['p_at_5'] for r in rows), rows=rows)


def main():
    data = json.loads(FIXTURE.read_text())
    # Grid and tie-break fixed before observing holdout. Total=100; test+sport
    # outweigh binary skill coverage; FSP <=10, preserving modest within-grade bonus.
    grid = [(req, desired, test, sport) for req in [25,30,35,40]
            for desired in [5,10,15] for test in [40,45,50,55,60]
            for sport in [5,10] if req+desired+test+sport == 100 and test+sport > req+desired]
    dev = [(measure(data['dev'], w)['p_at_5'], w) for w in grid]
    best, chosen = min(dev, key=lambda x: (-x[0], sum(abs(a-b) for a,b in zip(x[1],OLD)), x[1]))
    result = dict(kind='synthetic_author_labels_not_expert_validation', fixture_sha256=hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
                  selection='max dev P@5; tie: minimum L1 distance to old weights, then tuple order',
                  grid=[dict(weights=w, dev_p_at_5=m) for m,w in dev], old_weights=OLD, selected_weights=chosen,
                  before={s:measure(data[s], OLD) for s in ['dev','test']},
                  after={s:measure(data[s], chosen) for s in ['dev','test']})
    Path('evaluation/stage_a_matching_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['old_weights','selected_weights','selection']}))
    for split in ['dev','test']:
        print(split, result['before'][split]['p_at_5'], '->', result['after'][split]['p_at_5'])

if __name__ == '__main__':
    main()

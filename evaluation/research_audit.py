"""Read-only regression audit of live source against frozen, team-authored labels."""
import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from fsp import bank
from fsp.matching import VERSION, eligible, group_sort, rank_candidate
from evaluation.oracles import solve


def records(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def matching(root):
    data = root / 'data/synthetic'
    candidates = {r['record_id']: r['payload'] for r in records(data / 'candidates.jsonl')}
    needs = {r['record_id']: r['payload'] for r in records(data / 'needs.jsonl')}
    # Labels never enter the candidate or ranking functions.
    predictions = []
    for row in records(data / 'pools.jsonl'):
        p = row['payload']
        criteria = needs[p['need_id']]['criteria']
        ranked = group_sort([dict(candidates[cid], id=cid, match=rank_candidate(candidates[cid], criteria))
                             for cid in p['candidate_ids'] if eligible(candidates[cid], criteria)])
        predictions.append((row, ranked))
    labels = {(r['payload']['need_id'], r['payload']['candidate_id']): r['payload']['decision']
              for r in records(root / 'labels/matching.jsonl')}
    rows = []
    for row, ranked in predictions:
        p = row['payload']
        gold = {cid: labels[p['need_id'], cid] for cid in p['candidate_ids']}
        relevant = {cid for cid, label in gold.items() if label == 'recommend'}
        full = [c for c in ranked if c['match']['required_skills_met']]
        scores = {}
        for name, items in [('mixed', ranked), ('full', full)]:
            ids = [c['id'] for c in items]
            top = ids[:5]
            hits = len(set(top) & relevant)
            scores[name] = dict(returned=len(ids), p_at_5=hits / 5,
                precision_served=hits / len(top) if top else None,
                recall_all=len(set(ids) & relevant) / len(relevant) if relevant else None,
                unknown_in_top5=sum(gold[i] == 'insufficient_evidence' for i in top),
                unmet_in_top5=sum(gold[i] == 'reject' for i in top),
                correct_abstention=not ids if not relevant else None)
        rows.append(dict(id=row['record_id'], split=row['split'], scenario=p['scenario'],
                         relevant=len(relevant), partial=len(ranked)-len(full), **scores))
    summary = {}
    for split in ['dev', 'test']:
        rs = [r for r in rows if r['split'] == split]
        summary[split] = {mode: dict(queries=len(rs), mean_p_at_5=mean(r[mode]['p_at_5'] for r in rs),
            unknown_in_top5=sum(r[mode]['unknown_in_top5'] for r in rs),
            unmet_in_top5=sum(r[mode]['unmet_in_top5'] for r in rs),
            correct_abstentions=sum(r[mode]['correct_abstention'] is True for r in rs),
            no_match_queries=sum(r['relevant'] == 0 for r in rs)) for mode in ['mixed', 'full']}
    return dict(summary=summary, queries=rows)


def assessment():
    rows, families = [], defaultdict(lambda: defaultdict(list))
    checks, mismatches = 0, []
    for spec, grade in bank.BLUEPRINT:
        frequent = defaultdict(Counter)
        for n in range(100):
            for q in bank.generate(spec, grade, f'audit-dev-{n}'):
                frequent[q['family']][q['answer']] += 1
        guesses = {f: counts.most_common(1)[0][0] for f, counts in frequent.items()}
        outcomes = defaultdict(list)
        scores = defaultdict(list)
        legacy = defaultdict(list)
        core = 'python' if spec == 'python' else 'sql'
        for n in range(100):
            qs = bank.generate(spec, grade, f'audit-probe-{n}')
            assert qs == bank.generate(spec, grade, f'audit-probe-{n}')
            rng = random.Random(f'audit-responses-{spec}-{grade}-{n}')
            answers = {kind: {} for kind in ['weak', 'core_only', 'strong', 'noisy', 'frequent_guess']}
            for q in qs:
                ref = str(solve(q))
                checks += 1
                if abs(float(ref)-float(q['answer'])) > .005:
                    mismatches.append(dict(spec=spec, grade=grade, variant=n, family=q['family']))
                for kind in answers:
                    knows = kind == 'strong' or kind == 'core_only' and q['skill'] == core
                    if kind == 'noisy': knows = rng.random() >= .2
                    answers[kind][q['id']] = guesses[q['family']] if kind == 'frequent_guess' else ref if knows else 'не знаю'
            for kind, response in answers.items():
                result = bank.grade_answers(qs, response)
                outcomes[kind].append(result['passed'])
                scores[kind].append(result['score'])
                legacy[kind].append(bank.grade_answers(qs, response, version='1.1.0')['passed'])
                for q, d in zip(qs, result['details']):
                    families[q['family']][kind].append(int(d['correct']))
        for kind, values in outcomes.items():
            counts = Counter(values)
            rows.append(dict(spec=spec, grade=grade, persona=kind, attempts=len(values),
                pass_rate=mean(values), old_rubric_pass_rate=mean(legacy[kind]), mean_score=mean(scores[kind]),
                pairwise_agreement=sum(v*(v-1) for v in counts.values())/(len(values)*(len(values)-1))))
    return dict(oracle_checks=checks, oracle_mismatches=mismatches, attempts=sum(r['attempts'] for r in rows),
        rows=rows, families=[dict(family=f, strong_minus_weak=mean(g['strong'])-mean(g['weak']),
            frequent_guess_correct=mean(g['frequent_guess']), noisy_correct=mean(g['noisy'])) for f,g in sorted(families.items())])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', type=Path, default=Path('dataset/builds/public-v1'))
    p.add_argument('--output', type=Path, default=Path('evaluation/research_results.json'))
    a = p.parse_args()
    files = [Path('evaluation/RESEARCH_PROTOCOL.md'), Path('evaluation/research_audit.py'),
             Path('evaluation/oracles.py'), Path('apps/api/fsp/bank.py'), Path('apps/api/fsp/matching.py')]
    files += [a.dataset / name for name in ['data/synthetic/candidates.jsonl','data/synthetic/needs.jsonl',
                                          'data/synthetic/pools.jsonl','labels/matching.jsonl']]
    result = dict(kind='synthetic_regression_not_human_validation', bank_version=bank.VERSION,
                  matching_version=VERSION, hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
                  matching=matching(a.dataset), assessment=assessment(), limitations=[
                      'Frozen test was examined before: regression, not blind generalization.',
                      'Team-authored programmatic labels, no human raters.',
                      'Strong/weak separation is built into simulator; no professional validation.',
                      'Same families remain recognizable; shuffling is not anti-cheat.',
                      'Four numeric questions do not cover a professional grade.'])
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(matching=result['matching']['summary'], oracle_mismatches=result['assessment']['oracle_mismatches'],
                         attempts=result['assessment']['attempts']),ensure_ascii=False))

if __name__ == '__main__': main()

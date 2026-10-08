"""Version comparison under fixed synthetic response models, not expert validation."""
import hashlib
import itertools
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from fsp import bank
from evaluation.oracles import solve

DEV_N = 200
PROBE_N = 500
STRATEGIES = ('weak', 'core_only', 'old_families_only', 'strong', 'noise_10', 'noise_20', 'frequent_guess')


def wilson(successes, total):
    z = 1.959963984540054
    p = successes / total
    d = 1 + z*z/total
    center = (p + z*z/(2*total))/d
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total))/d
    return [max(0, center-half), min(1, center+half)]


def exact_iid_pass(version, probability):
    qs = bank.generate('python', 'Junior', 'analytic-form', version=version)
    total = 0.0
    for mask in itertools.product([False, True], repeat=len(qs)):
        answers = {q['id']: q['answer'] if correct else 'не знаю' for q, correct in zip(qs, mask)}
        if bank.grade_answers(qs, answers, version=version)['passed']:
            n = sum(mask)
            total += probability**n * (1-probability)**(len(qs)-n)
    return total


def audit():
    rows, by_family = [], defaultdict(lambda: defaultdict(list))
    oracle_count, mismatches = 0, []
    for version in ['1.2.0', bank.VERSION]:
        for spec, grade in bank.BLUEPRINT:
            counts = defaultdict(Counter)
            for i in range(DEV_N):
                for q in bank.generate(spec, grade, f'v2-dev-{i}', version=version):
                    counts[q['family']][q['answer']] += 1
            modes = {f: c.most_common(1)[0][0] for f,c in counts.items()}
            results, scores = defaultdict(list), defaultdict(list)
            fingerprints = set()
            for i in range(PROBE_N):
                qs = bank.generate(spec, grade, f'v2-probe-{i}', version=version)
                fingerprints.add(bank.fingerprint(qs))
                answers = {strategy:{} for strategy in STRATEGIES}
                seen = Counter()
                for q in qs:
                    reference = str(solve(q))
                    oracle_count += 1
                    if abs(float(reference)-float(q['answer'])) > .005:
                        mismatches.append([version,spec,grade,i,q['family']])
                    slot = seen[q['family']]
                    seen[q['family']] += 1
                    # Same known-family noise for both versions; order does not affect it.
                    draw = random.Random(f'v2-response-{spec}-{grade}-{i}-{q["family"]}-{slot}').random()
                    for strategy in STRATEGIES:
                        knows = strategy == 'strong'
                        knows |= strategy == 'core_only' and q['skill'] == ('python' if spec == 'python' else 'sql')
                        knows |= strategy == 'old_families_only' and q['family'] in bank.LEGACY_BLUEPRINT[spec,grade]
                        knows |= strategy == 'noise_10' and draw >= .1
                        knows |= strategy == 'noise_20' and draw >= .2
                        answers[strategy][q['id']] = modes[q['family']] if strategy == 'frequent_guess' else reference if knows else 'не знаю'
                for strategy, response in answers.items():
                    r = bank.grade_answers(qs,response,version=version)
                    results[strategy].append(r['passed'])
                    scores[strategy].append(r['score'])
                    for q,d in zip(qs,r['details']):
                        by_family[version,q['family']][strategy].append(int(d['correct']))
            for strategy in STRATEGIES:
                ys = results[strategy]
                c = Counter(ys)
                expected = True if strategy == 'strong' or strategy == 'old_families_only' and version == '1.2.0' else False if strategy in ['weak','core_only','old_families_only'] else None
                rows.append(dict(version=version,specialization=spec,grade=grade,strategy=strategy,
                    n=len(ys),pass_count=sum(ys),pass_rate=mean(ys),mean_score=mean(scores[strategy]),
                    pass_rate_wilson95=wilson(sum(ys),len(ys)), expected_pass=expected,
                    agreement_with_expected=mean(y == expected for y in ys) if expected is not None else None,
                    pairwise_agreement=sum(n*(n-1) for n in c.values())/(len(ys)*(len(ys)-1)),
                    unique_forms=len(fingerprints),score_histogram=dict(sorted(Counter(scores[strategy]).items()))))
    families = [dict(version=v,family=f,strong_minus_weak=mean(g['strong'])-mean(g['weak']),
                     mode_guess_correct_fraction=mean(g['frequent_guess']),noise20_correct_fraction=mean(g['noise_20']),
                     observations_per_strategy=len(g['strong'])) for (v,f),g in sorted(by_family.items())]
    return dict(rows=rows,families=families,oracle_checks=oracle_count,oracle_mismatches=mismatches,
                simulated_attempts=sum(r['n'] for r in rows),
                analytic_iid=[dict(version=v,probability_correct=p,pass_probability=exact_iid_pass(v,p))
                              for v in ['1.2.0',bank.VERSION] for p in [.8,.9]])


def main():
    paths=['evaluation/BANK_V2_PROTOCOL.md','evaluation/bank_v2_audit.py','evaluation/oracles.py','apps/api/fsp/bank.py']
    r=dict(kind='synthetic_model_comparison_not_human_validation',dev_variants_per_category=DEV_N,
           probe_variants_per_category=PROBE_N,sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
           **audit(),limitations=[
               'The response model assumes independent slips and fixed knowledge; no real people.',
               'Wilson intervals describe this synthetic sampling process, not market performance.',
               'Pairwise comparisons share attempts and are not independent observations.',
               'Strong/weak separation is defined by construction, not empirical discrimination.',
               'Remembering solution methods or using external help is still possible.',
               'Eight numeric questions do not certify a professional grade.'])
    Path('evaluation/bank_v2_results.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['oracle_checks','oracle_mismatches','simulated_attempts','analytic_iid']},ensure_ascii=False))
    for v in ['1.2.0',bank.VERSION]:
        for strategy in ['frequent_guess','noise_10','noise_20','old_families_only']:
            rs=[row for row in r['rows'] if row['version']==v and row['strategy']==strategy]
            print(v,strategy,'mean pass',round(mean(row['pass_rate'] for row in rs),4),'pair agreement',round(mean(row['pairwise_agreement'] for row in rs),4))

if __name__=='__main__': main()

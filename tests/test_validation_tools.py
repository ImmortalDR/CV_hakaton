import csv
import json
from pathlib import Path
import pytest
from evaluation.pilot import prepare as pilot_prepare
from evaluation.pilot_analysis import analyse
from evaluation.relevance_benchmark import prepare, evaluate, COLUMNS


def source(tmp_path,n=2):
    data={'queries':[{'id':str(q),'component':str(q),'text':'Synthetic query', 'candidates':[{'id':str(c),'text':'Synthetic candidate','scores':{'baseline':float(10-c),'challenger':float(c)}} for c in range(10)]} for q in range(n)]}
    p=tmp_path/'source.json';p.write_text(json.dumps(data));return p


def labels(root,n,unknown=False):
    with (root/'judgments.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(COLUMNS)
        for q in range(n):
            for c in range(10):
                for r in ['unit-a','unit-b']:
                    w.writerow([str(q),str(c),r,'' if unknown and c==0 else int(c>=5)*2,'Synthetic unit test, not human observations'])


def test_empty_pilot_analysis_has_no_invented_statistics(tmp_path):
    pilot_prepare(tmp_path)
    r=analyse(tmp_path)
    assert r['status']=='not_run' and r['paired_agreement_ci95'] is None
    assert r['score_retest_correlation'] is None and r['expert_families_reviewed']==0


def test_blind_export_removes_model_scores_and_empty_labels_do_not_pass(tmp_path):
    root=tmp_path/'study';prepare(source(tmp_path),root)
    assert 'scores' not in (root/'blind-review.json').read_text()
    r=evaluate(root);assert r['status']=='not_run' and not r['production_promotion_allowed']
    with pytest.raises(ValueError,match='empty'):prepare(source(tmp_path),root)


def test_ranking_gate_requires_size_and_complete_labels(tmp_path):
    root=tmp_path/'study';prepare(source(tmp_path),root);labels(root,2)
    r=evaluate(root)
    assert r['queries_evaluated']==2 and r['delta']>0 and not r['production_promotion_allowed']
    labels(root,2,unknown=True)
    r=evaluate(root);assert r['queries_evaluated']==0 and r['baseline_ndcg10'] is None


def test_ranking_gate_groups_correlated_queries_and_detects_tampering(tmp_path):
    root=tmp_path/'study';p=source(tmp_path,20);data=json.loads(p.read_text())
    for q in data['queries']:q['component']='same-component'
    p.write_text(json.dumps(data));prepare(p,root);labels(root,20)
    r=evaluate(root);assert r['independent_components']==1 and r['delta_ci95'] is None and not r['production_promotion_allowed']
    (root/'private-scores.json').write_text('{}')
    with pytest.raises(ValueError,match='modified'):evaluate(root)


def test_ranking_gate_can_pass_on_explicit_synthetic_fixture(tmp_path):
    root=tmp_path/'study';prepare(source(tmp_path,20),root);labels(root,20)
    r=evaluate(root);assert r['statistical_gate_passed'] and not r['production_promotion_allowed'] and r['delta_ci95'][0]>0
    # This only tests gate mathematics. It is not a real model promotion result.


def test_pilot_session_times_and_independent_family_analysis(tmp_path):
    from evaluation.pilot import PEOPLE_COLUMNS, RESPONSE_COLUMNS
    from evaluation.pilot_analysis import SESSION_COLUMNS
    pilot_prepare(tmp_path)
    forms=json.loads((tmp_path/'answer-key.json').read_text())[:2]
    def write(name,columns,rows):
        with (tmp_path/name).open('w',newline='') as f:
            w=csv.writer(f);w.writerow(columns);w.writerows(rows)
    write('participants.csv',PEOPLE_COLUMNS,[['fixture','python','Junior','true','Synthetic unit fixture']])
    write('responses.csv',RESPONSE_COLUMNS,[['fixture',f['form_id'],q['id'],q['answer']] for f in forms for q in f['questions']])
    write('sessions.csv',SESSION_COLUMNS,[['fixture',forms[0]['form_id'],'2026-10-01T10:00:00+00:00','2026-10-01T10:30:00+00:00'],['fixture',forms[1]['form_id'],'2026-10-08T10:30:00+00:00','2026-10-08T11:00:00+00:00']])
    r=analyse(tmp_path)
    assert r['recorded_retest_intervals']==1 and r['retest_interval_hours_mean']==168
    assert r['paired_agreement']==1 and r['paired_agreement_ci95'] is None
    assert all(x['participants']==1 for x in r['family_analysis'])
    write('sessions.csv',SESSION_COLUMNS,[['fixture',forms[0]['form_id'],'2026-10-01T10:00:00','2026-10-01T10:30:00']])
    with pytest.raises(ValueError,match='timezone'):analyse(tmp_path)

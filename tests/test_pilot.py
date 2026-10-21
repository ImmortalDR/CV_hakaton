import csv
import json

import pytest

from evaluation.pilot import PEOPLE_COLUMNS, RESPONSE_COLUMNS, evaluate, prepare


def fill(path, columns, rows):
    with path.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(columns);w.writerows(rows)


def test_empty_pilot_does_not_invent_people_or_metrics(tmp_path):
    prepare(tmp_path)
    r=evaluate(tmp_path)
    assert r['status']=='not_run' and r['participants_observed']==0
    assert r['agreement_with_independent_labels'] is None and r['paired_agreement'] is None
    public=json.loads((tmp_path/'forms.json').read_text())
    assert all(set(q)=={'id','skill','text'} for f in public for q in f['questions'])
    with pytest.raises(ValueError,match='must be empty'): prepare(tmp_path)


def test_pilot_correctly_scores_observed_pairs_and_independent_labels(tmp_path):
    prepare(tmp_path)
    forms=json.loads((tmp_path/'answer-key.json').read_text())
    selected=[f for f in forms if f['specialization']=='python' and f['grade']=='Junior']
    fill(tmp_path/'participants.csv',PEOPLE_COLUMNS,[['p1','python','Junior','true','synthetic unit test'],['p2','python','Junior','false','synthetic unit test']])
    rows=[[pid,f['form_id'],q['id'],q['answer'] if pid=='p1' else ''] for pid in ['p1','p2'] for f in selected for q in f['questions']]
    fill(tmp_path/'responses.csv',RESPONSE_COLUMNS,rows)
    r=evaluate(tmp_path)
    assert r['attempts']==4 and r['participants_observed']==2
    assert r['agreement_with_independent_labels']==1 and r['paired_agreement']==1
    assert all(f['strong_minus_weak']==1 for f in r['family_discrimination'])
    fill(tmp_path/'responses.csv',RESPONSE_COLUMNS,rows+[rows[0]])
    with pytest.raises(ValueError,match='Duplicate response'): evaluate(tmp_path)


def test_pilot_rejects_fabricated_label_provenance_and_modified_forms(tmp_path):
    prepare(tmp_path)
    fill(tmp_path/'participants.csv',PEOPLE_COLUMNS,[['p1','python','Junior','true','']])
    with pytest.raises(ValueError,match='source'): evaluate(tmp_path)
    (tmp_path/'forms.json').write_text('[]')
    with pytest.raises(ValueError,match='modified'): evaluate(tmp_path)

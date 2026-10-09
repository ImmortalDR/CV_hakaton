import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from enrich import anchored_split, history_asof, index
from test_training import row, small_source
from prepare import build as scan


def history(key='job', day='2020-01-01', text='разработка python', rownum=1, **kw):
    return dict(key=key, day=day, text=text, rownum=rownum, start='2019-01-01', end='', **kw)


def test_history_only_prior_versions_and_no_future_graduation():
    rs = [history(), history(day='2020-01-03', text='future', rownum=2),
          history(day='2020-01-02', text='same day', rownum=3)]
    chosen, amb = history_asof(rs, '2020-01-02', 'work')
    assert [r['rownum'] for r in chosen] == [1] and amb == 0
    rs = [history(graduate_year=2020), history(key='old', graduate_year=2019, rownum=2)]
    chosen, _ = history_asof(rs, '2020-11-01', 'edu')
    assert [r['rownum'] for r in chosen] == [2]


def test_history_ambiguous_and_repeated_versions_do_not_inflate_text():
    rs = [history(), history(rownum=2), history(day='2020-01-03', rownum=3),
          history(key='second', rownum=4), history(key='conflict', text='a', rownum=5),
          history(key='conflict', text='b', rownum=6)]
    chosen, amb = history_asof(rs, '2020-02-01', 'work')
    assert amb == 1 and len(chosen) == 1 and chosen[0]['rownum'] == 3


def test_different_tenures_do_not_overwrite_each_other():
    first=history(text='old duties')
    second=history(text='new duties', rownum=2) | {'start':'2019-06-01'}
    chosen,amb=history_asof([first,second], '2020-02-01','work')
    assert amb==0 and len(chosen)==2


def test_anchor_entities_cannot_move_to_training_and_bridges_quarantined():
    anchors = [row(1, split='test'), row(2, split='train')]
    rows = [row(3, person_id='p1'), row(4)]
    result, dropped = anchored_split(rows, anchors)
    assert result[0]['split'] == 'test' and dropped == 0
    # A new observation connecting old train/test must not move either anchor.
    rows = [row(3, person_id='p1', job_id='j2')]
    assert anchored_split(rows, anchors) == ([], 1)


def test_enriched_copy_links_to_old_base_text():
    anchor = row(1, split='validation', candidate_text='professional python developer with sql and systems')
    fresh = row(2, candidate_text=anchor['candidate_text'], candidate_base_text='new base')
    result, dropped = anchored_split([fresh], [anchor])
    assert dropped == 0 and result[0]['split'] == 'validation'


def test_short_shared_titles_are_not_full_cv_copies():
    anchors=[row(1, split='train'), row(2, split='test')]
    a=row(3,person_id='p1',candidate_base_text='программист')
    b=row(4,person_id='p2',candidate_base_text='программист')
    kept,dropped=anchored_split([a,b],anchors)
    assert dropped==0 and [r['split'] for r in kept]==['train','test']


def test_index_real_schema_does_not_keep_names_and_rejects_future_start(tmp_path):
    import csv
    source = small_source(tmp_path)
    # The existing fixture has no creation_mistake column; source allows empty.
    path = source / 'invitations.csv'
    with path.open() as f:
        apps = list(csv.DictReader(f, delimiter=';'))
    for a in apps:
        a['date_creation_mistake'] = '0'
    with path.open('w') as f:
        w = csv.DictWriter(f, fieldnames=apps[0], delimiter=';'); w.writeheader(); w.writerows(apps)
    root = tmp_path / 'base'
    scan(source, root)
    work = dict(achievements='python', achievements_modified='', company_name='PRIVATE_COMPANY',
                date_from='2019-01-01', date_last_updated='2020-01-01', date_to='',
                date_mistake='0', demands='разработка SQL', id_cv='c0', job_title='разработчик')
    edu = dict(date_last_updated='2020-01-01', faculty='информатика', graduate_year='2018',
               id_cv='c0', legal_name='PRIVATE_SCHOOL', qualification='инженер',
               speciality='программирование', grad_year_mistake='0')
    for name, records in [('workexp.csv', [work, work | {'date_from': '2021-01-01'}]), ('edu.csv', [edu])]:
        with (source / name).open('w') as f:
            w = csv.DictWriter(f, fieldnames=records[0], delimiter=';'); w.writeheader(); w.writerows(records)
    out = tmp_path / 'history'
    index(source, root, out)
    assert len((out / 'workexp.csv.jsonl').read_text().splitlines()) == 1
    assert 'PRIVATE_' not in (out / 'workexp.csv.jsonl').read_text()
    assert 'PRIVATE_' not in (out / 'edu.csv.jsonl').read_text()
    report = json.loads((out / 'complete.json').read_text())
    assert report['inputs']['workexp.csv']['counts']['invalid_work_dates'] == 1

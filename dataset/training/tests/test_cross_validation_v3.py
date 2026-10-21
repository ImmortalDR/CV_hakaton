import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cross_validate_v3 import run
from enrich import file_hash
from test_rank_v3 import fixture_rows


def test_grouped_oof_has_one_prediction_per_development_pair_and_never_test(tmp_path):
    root=tmp_path/'input'; root.mkdir()
    rows=fixture_rows()
    (root/'pairs.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in rows))
    (root/'pairs-report.json').write_text(json.dumps({'pairs_sha256':file_hash(root/'pairs.jsonl'),
                                                   'target':'artificial_software_fixture'}))
    out=tmp_path/'cv'
    run(root,out)
    report=json.loads((out/'training-report.json').read_text())
    assert report['counts']=={'dev':64,'test':32,'oof':64}
    oof=[json.loads(line) for line in (out/'oof-predictions.jsonl').read_text().splitlines()]
    observed=[p for p in oof if p['family']=='base_pair' and p['parameter']==.1]
    assert len(observed)==len({p['pair_id'] for p in observed})==64
    assert not any(p['pair_id'].startswith('test') for p in observed)
    original={p['pair_id']:p for p in rows}
    group_folds={}
    for p in observed:
        group=original[p['pair_id']]['group_id']
        group_folds.setdefault(group,set()).add(p['fold'])
    assert all(len(fs)==1 for fs in group_folds.values())
    assert json.loads((out/'replay.json').read_text())['predictions_and_metrics_equal']
    assert report['adaptive_after_v3'] and report['test_is_pristine'] is False

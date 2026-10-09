from pathlib import Path
import sys
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import predict_v3


def test_offline_rank_skips_empty_profiles_and_keeps_explicit_target(monkeypatch):
    seen=[]
    def score(artifact, rows):
        seen.extend(rows)
        return np.array([.2,.8])
    monkeypatch.setattr(predict_v3,'predict_artifact',score)
    candidates=[{'candidate_id':'a','candidate_base_text':'python разработчик серверных приложений',
                 'work_text':'разработка API'},
                {'candidate_id':'empty'},
                {'candidate_id':'b','candidate_base_text':'python sql разработчик серверных приложений'}]
    result=predict_v3.rank({'target':'recorded_reply','family':'fixture'},candidates,
                           'python sql разработчик серверных приложений и тестирование систем данных')
    assert result['results'][0]['rank']==2
    assert result['results'][1]['observed_reply_score'] is None
    assert result['results'][2]['rank']==1
    assert 'разработка api' in seen[0]['candidate_text']
    assert result['production_promotion_allowed'] is False

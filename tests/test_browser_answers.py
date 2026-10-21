import pytest

from fsp import bank
from browser_requirements import solve_visible
from evaluation.oracles import solve


@pytest.mark.parametrize('grade',['Junior','Senior'])
def test_browser_answers_use_only_visible_text_across_both_bank_versions(grade):
    for version in ['1.2.0','2.0.0']:
        for seed in range(30):
            for q in bank.generate('python',grade,seed,version=version):
                assert solve_visible(q['text']) == solve(q)

from evaluation.final_matching_challenge import evaluate


def test_declared_policy_and_matching_invariants():
    report = evaluate()
    assert report['passed'], [a for a in report['assertions'] if not a['passed']]
    assert report['changed_pairs'] > 0, 'Challenge must exercise competing evidence'
    assert report['precision_at_5'] is None  # no independent relevance labels

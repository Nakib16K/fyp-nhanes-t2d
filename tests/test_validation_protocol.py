"""Synthetic offline tests of validation-only threshold selection."""
import numpy as np
import pytest
from sklearn.metrics import f1_score
from src.validation_protocol import (
    FrozenThreshold, three_way_split, choose_validation_threshold,
    classify_at_threshold, evaluate_frozen_threshold, subgroup_fairness,
)


def test_original_outer_holdout_size():
    y = np.array([0] * 12983 + [1] * 2774)
    parts = three_way_split(y)
    assert {n: len(indices) for n, indices in parts.items()} == {
        'fit': 10084, 'validation': 2521, 'test': 3152
    }


def test_indices_disjoint_and_complete():
    y = np.array([0] * 80 + [1] * 20)
    p = three_way_split(y)
    all_ids = np.concatenate(list(p.values()))
    assert len(all_ids) == len(np.unique(all_ids)) == len(y)
    assert set(all_ids) == set(range(len(y)))


def test_deterministic_splits():
    y = [0] * 90 + [1] * 30
    a, b = three_way_split(y), three_way_split(y)
    for k in a:
        assert np.array_equal(a[k], b[k])


def test_stratified_ratio():
    y = np.array([0] * 900 + [1] * 100)
    parts = three_way_split(y)
    for ids in parts.values():
        assert abs(y[ids].mean() - 0.1) < 0.012


@pytest.mark.parametrize('bad', [0, 1, -0.01, 1.1])
def test_invalid_split_fractions(bad):
    y = [0] * 90 + [1] * 30
    with pytest.raises(ValueError):
        three_way_split(y, test_size=bad)


def test_no_one_class_split():
    with pytest.raises(ValueError):
        three_way_split([0] * 30)


def test_threshold_matches_bruteforce_f1():
    labels = np.array([0, 1, 1, 0, 1, 0, 0, 1])
    probs = np.array([.1, .82, .5, .65, .27, .16, .48, .52])
    sel = choose_validation_threshold(labels, probs)
    brute = [(f1_score(labels, classify_at_threshold(probs, t)), t) for t in np.unique(probs)]
    best_f1 = max(x[0] for x in brute)
    best_threshold = max(t for score, t in brute if np.isclose(score, best_f1))
    assert sel.threshold == best_threshold
    assert sel.validation_f1 == pytest.approx(best_f1)
    assert sel.selected_from == 'validation'


def test_threshold_tie_picks_higher():
    labels = [1, 0, 1, 0]
    probs = [.9, .8, .7, .1]
    sel = choose_validation_threshold(labels, probs)
    scores = [f1_score(labels, classify_at_threshold(probs, t)) for t in sorted(set(probs))]
    assert sel.validation_f1 == pytest.approx(max(scores))


def test_exact_threshold_is_positive():
    assert classify_at_threshold([0.49, .5, .501], .5).tolist() == [0, 1, 1]


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -0.1, 1.01])
def test_reject_invalid_thresholds(bad):
    with pytest.raises(ValueError):
        classify_at_threshold([.2], bad)


@pytest.mark.parametrize('bad', [[.2, np.nan], [-.1, .5], [.4, 1.01]])
def test_reject_invalid_probabilities(bad):
    with pytest.raises(ValueError):
        choose_validation_threshold([0, 1], bad)


def test_reject_one_class_validation():
    with pytest.raises(ValueError):
        choose_validation_threshold([1, 1, 1], [.2, .8, .3])


def test_reject_misaligned_probabilities():
    with pytest.raises(ValueError):
        choose_validation_threshold([0, 1, 0], [.2, .3])


def test_metrics_use_preselected_threshold_not_test_optimized():
    selection = FrozenThreshold(.8, .5)
    result = evaluate_frozen_threshold([0, 1, 1, 0], [.1, .7, .9, .2], selection)
    assert result['validation_selected_threshold'] == .8
    assert result['confusion_matrix'] == {'tn': 2, 'fp': 0, 'fn': 1, 'tp': 1}
    assert result['sensitivity'] == .5
    assert result['f1'] == pytest.approx(2 / 3)


def test_test_labels_do_not_change_frozen_threshold():
    selection = FrozenThreshold(.65, .8)
    one = evaluate_frozen_threshold([0, 1, 1, 0], [.1, .4, .9, .2], selection)
    other = evaluate_frozen_threshold([1, 0, 0, 1], [.1, .4, .9, .2], selection)
    assert one['validation_selected_threshold'] == other['validation_selected_threshold'] == .65
    assert one['f1'] != other['f1']


def test_reject_non_validation_selection():
    with pytest.raises(ValueError):
        evaluate_frozen_threshold([0, 1], [.4, .6], FrozenThreshold(.5, .5, 'test'))


def test_fairness_report_denominators():
    sel = FrozenThreshold(.65, .8)
    rows = subgroup_fairness([0, 1, 0, 1, 0, 1], [.9, .4, .3, .9, .7, .8], ['A', 'A', 'A', 'B', 'B', 'B'], sel)
    a, b = rows
    assert (a['support'], a['actual_positive'], a['actual_negative']) == (3, 1, 2)
    assert a['false_negative_rate'] == 1
    assert a['false_positive_rate'] == .5
    assert (b['support'], b['actual_positive'], b['actual_negative']) == (3, 2, 1)
    assert b['false_negative_rate'] == 0
    assert b['false_positive_rate'] == 1


def test_fairness_handles_missing_group():
    rows = subgroup_fairness([0, 1, 0, 1], [.1, .8, .9, .6], ['A', None, np.nan, 'A'], FrozenThreshold(.5, .7))
    assert {x['group'] for x in rows} == {'A', '<missing>'}


def test_fairness_empty_positive_denominator_is_not_zero():
    rows = subgroup_fairness([0, 0, 1, 1], [.1, .2, .3, .9], ['A', 'A', 'B', 'B'], FrozenThreshold(.6, .7))
    assert rows[0]['false_negative_rate'] is None
    assert rows[1]['false_positive_rate'] is None


def test_brier_score_present():
    r = evaluate_frozen_threshold([0, 0, 1, 1], [.1, .2, .9, .8], FrozenThreshold(.5, .9))
    assert r['brier_score'] == pytest.approx(.025)

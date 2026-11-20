"""Offline tests for explicit thresholds (no model training or private data)."""
import math
import pytest
from src.decisions import DecisionError, classify_probability, validate_model_thresholds


@pytest.mark.parametrize("prob,threshold,label", [
    (0.20, 0.28, "Low Risk"), (0.28, 0.28, "High Risk"),
    (0.28000001, 0.28, "High Risk"), (0.27999999, 0.28, "Low Risk"),
    (0.40, 0.28, "High Risk"), (0.40, 0.50, "Low Risk"),
    (0.00, 0.00, "High Risk"), (1.00, 1.00, "High Risk"),
    (0.99, 1.00, "Low Risk"), (0.01, 0.00, "High Risk"),
    # Verify original unrounded probability is used, not 4dp display value:
    (0.279999999, 0.28, "Low Risk"), (0.280000001, 0.28, "High Risk"),
])
def test_decision_at_boundary(prob, threshold, label):
    assert classify_probability(prob, threshold) == label


@pytest.mark.parametrize("value", [float('nan'), float('inf'), float('-inf'), -0.001, 1.01, "0.28", None, True, False, [], {}])
def test_rejects_bad_model_probability(value):
    with pytest.raises(DecisionError):
        classify_probability(value, 0.28)


@pytest.mark.parametrize("value", [float('nan'), float('inf'), float('-inf'), -0.001, 1.01, "0.28", None, True, False, [], {}])
def test_rejects_bad_threshold(value):
    with pytest.raises(DecisionError):
        classify_probability(0.40, value)


def test_model_specific_thresholds():
    models = {k: object() for k in ('XGB', 'LGBM', 'RF', 'LR')}
    incoming = {'XGB': 0.2966, 'LGBM': 0.2938, 'RF': 0.2982, 'LR': 0.2510}
    assert validate_model_thresholds(models, incoming) == incoming
    assert classify_probability(0.28, incoming['LR']) == 'High Risk'
    assert classify_probability(0.28, incoming['XGB']) == 'Low Risk'


@pytest.mark.parametrize("thresholds", [None, {}, {'XGB': 0.3}, {'XGB': 0.3, 'LR': 0.2},
     {'XGB': 0.3, 'LR': 0.2, 'RF': 0.4, 'LGBM': 0.5, 'EXTRA': 0.1},
     {'XGB': float('nan'), 'LR': 0.2, 'RF': 0.4, 'LGBM': 0.5},
     {'XGB': 0.3, 'LR': True, 'RF': 0.4, 'LGBM': 0.5},
     {'XGB': 0.3, 'LR': '0.4', 'RF': 0.4, 'LGBM': 0.5},
])
def test_missing_or_malformed_registry_fails_closed(thresholds):
    models = {k: object() for k in ('XGB', 'LGBM', 'RF', 'LR')}
    with pytest.raises(DecisionError):
        validate_model_thresholds(models, thresholds)


def test_no_models_rejected():
    with pytest.raises(DecisionError):
        validate_model_thresholds({}, {})


def test_lowercase_models_rejected():
    with pytest.raises(DecisionError):
        validate_model_thresholds({'xgb': object()}, {'xgb': 0.3})

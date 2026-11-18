"""Strict, standard-library-only binary decision rules for verified model outputs.

A classification boundary must come from a verified run manifest (or be
explicitly supplied by a test fixture). Do not infer or assume a 0.5 fallback.
Probabilities are educational model scores, not a clinical diagnosis.
"""
from __future__ import annotations

import math
from collections.abc import Mapping


class DecisionError(ValueError):
    """Prediction metadata or a model probability is invalid."""


def _valid_unit(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DecisionError(f"{label} must be a real numeric value")
    num = float(value)
    if not math.isfinite(num) or not (0.0 <= num <= 1.0):
        raise DecisionError(f"{label} must be finite and within [0, 1]")
    return num


def validate_model_thresholds(models: Mapping, thresholds: Mapping | None) -> dict[str, float]:
    """Require one explicitly supplied valid threshold per loaded model.

    Both dictionaries are keyed with uppercase model names (XGB, LGBM, RF,
    LR). Reject missing, extraneous, ambiguous and invalid thresholds before
    using any model for inference. This provides no implicit 0.5 default.
    """
    if not isinstance(models, Mapping) or not models:
        raise DecisionError("No loaded models")
    if not isinstance(thresholds, Mapping):
        raise DecisionError("No threshold mapping")
    expected = set(models)
    if not all(isinstance(k, str) and k == k.upper() and k for k in expected):
        raise DecisionError("Model names must be nonempty uppercase identifiers")
    if set(thresholds) != expected:
        missing = sorted(expected - set(thresholds))
        unexpected = sorted(set(thresholds) - expected)
        raise DecisionError(f"Threshold/model mismatch: missing={missing}, unexpected={unexpected}")
    return {name: _valid_unit(thresholds[name], f"Threshold for {name}") for name in expected}


def classify_probability(probability: float, threshold: float) -> str:
    """Classify using the *unrounded* model score and frozen threshold."""
    p = _valid_unit(probability, "Model probability")
    t = _valid_unit(threshold, "Decision threshold")
    return "High Risk" if p >= t else "Low Risk"

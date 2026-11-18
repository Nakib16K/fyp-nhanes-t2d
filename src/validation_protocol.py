"""Validation-only threshold selection and fixed-threshold evaluation.

The research pipeline uses disjoint fit/validation/test indices and freezes
operating thresholds before evaluating the retained test partition.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split


@dataclass(frozen=True)
class FrozenThreshold:
    threshold: float
    validation_f1: float
    selected_from: str = "validation"


def _binary_labels(y: Any, *, require_both: bool=False) -> np.ndarray:
    labels = np.asarray(y).reshape(-1)
    if len(labels) == 0 or not np.isin(labels, [0, 1]).all():
        raise ValueError("Labels must be a non-empty vector of binary 0/1 values")
    if require_both and np.unique(labels).size != 2:
        raise ValueError("Both classes are needed for this evaluation")
    return labels.astype(int)


def _probabilities(values: Any, n: int) -> np.ndarray:
    probs = np.asarray(values, dtype=float).reshape(-1)
    if probs.shape != (n,) or not np.isfinite(probs).all() or ((probs < 0) | (probs > 1)).any():
        raise ValueError("Probabilities must be finite 0..1 values aligned with labels")
    return probs


def _valid_threshold(threshold: float) -> float:
    threshold = float(threshold)
    if not np.isfinite(threshold) or threshold < 0 or threshold > 1:
        raise ValueError("Threshold must be a finite number between 0 and 1")
    return threshold


def three_way_split(
    labels: Any,
    *,
    test_size: float=0.2,
    validation_fraction_of_remainder: float=0.2,
    random_state: int=42,
) -> dict[str, np.ndarray]:
    """Stratified *indices*, with the original 20% outer holdout preserved.

    Assumes row order is identical to the original dataset, and each class has
    enough observations to stratify all three partitions. Returned indices are
    disjoint and cover every input record exactly once.
    """
    labels = _binary_labels(labels, require_both=True)
    if not 0 < test_size < 1 or not 0 < validation_fraction_of_remainder < 1:
        raise ValueError("Split fractions must be strictly between zero and one")
    positions = np.arange(len(labels))
    trainval_ids, test_ids = train_test_split(
        positions, test_size=test_size, stratify=labels, random_state=random_state
    )
    fit_ids, validation_ids = train_test_split(
        trainval_ids,
        test_size=validation_fraction_of_remainder,
        stratify=labels[trainval_ids],
        random_state=random_state,
    )
    return {"fit": fit_ids, "validation": validation_ids, "test": test_ids}


def choose_validation_threshold(validation_y: Any, validation_proba: Any) -> FrozenThreshold:
    """Select an F1-maximising operating threshold using validation labels only.

    The terminal PR point has no corresponding threshold and must be excluded.
    Ties are broken toward the *highest* threshold to avoid arbitrary changes
    when adjacent candidates have the same F1. The test split is not accepted.
    """
    labels = _binary_labels(validation_y, require_both=True)
    probs = _probabilities(validation_proba, len(labels))
    precisions, recalls, thresholds = precision_recall_curve(labels, probs)
    if thresholds.size == 0:
        raise ValueError("Validation PR curve produced no candidate thresholds")
    f1_values = 2 * precisions[:-1] * recalls[:-1] / (
        precisions[:-1] + recalls[:-1] + 1e-12
    )
    maximum = np.max(f1_values)
    best = np.flatnonzero(np.isclose(f1_values, maximum, rtol=1e-12, atol=1e-12))
    idx = int(best[-1])
    return FrozenThreshold(
        threshold=float(thresholds[idx]),
        validation_f1=float(f1_values[idx]),
    )


def classify_at_threshold(probabilities: Any, threshold: float) -> np.ndarray:
    threshold = _valid_threshold(threshold)
    probs = np.asarray(probabilities, dtype=float).reshape(-1)
    if not np.isfinite(probs).all() or ((probs < 0) | (probs > 1)).any():
        raise ValueError("Probabilities must be finite values from 0 to 1")
    return (probs >= threshold).astype(int)


def evaluate_frozen_threshold(
    test_y: Any, test_proba: Any, selection: FrozenThreshold
) -> dict[str, Any]:
    """Evaluate an *already frozen* threshold; never optimise on test labels."""
    if selection.selected_from != "validation":
        raise ValueError("Threshold must be frozen from validation")
    labels = _binary_labels(test_y, require_both=True)
    probs = _probabilities(test_proba, len(labels))
    pred = classify_at_threshold(probs, selection.threshold)
    tn, fp, fn, tp = confusion_matrix(labels, pred, labels=[0, 1]).ravel()
    return {
        "roc_auc": float(roc_auc_score(labels, probs)),
        "average_precision": float(average_precision_score(labels, probs)),
        "f1": float(f1_score(labels, pred, zero_division=0)),
        "precision": float(precision_score(labels, pred, zero_division=0)),
        "sensitivity": float(recall_score(labels, pred, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
        "accuracy": float(accuracy_score(labels, pred)),
        "brier_score": float(brier_score_loss(labels, probs)),
        "validation_selected_threshold": float(selection.threshold),
        "validation_f1": float(selection.validation_f1),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def subgroup_fairness(
    test_y: Any, test_proba: Any, group_values: Any, selection: FrozenThreshold
) -> list[dict[str, Any]]:
    """Fixed-threshold subgroup error rates, with denominators reported."""
    if selection.selected_from != "validation":
        raise ValueError("Fairness audit must use validation-selected threshold")
    labels = _binary_labels(test_y)
    probs = _probabilities(test_proba, len(labels))
    groups = np.asarray(group_values, dtype=object).reshape(-1)
    if len(groups) != len(labels):
        raise ValueError("Group labels and test records must align")
    pred = classify_at_threshold(probs, selection.threshold)
    rows = []
    # Treat missing groups as their own category rather than quietly erasing data.
    keys = ["<missing>" if x is None or (isinstance(x, (float, np.floating)) and np.isnan(x)) else str(x) for x in groups]
    for group in sorted(set(keys)):
        mask = np.asarray([g == group for g in keys])
        tn, fp, fn, tp = [int(n) for n in confusion_matrix(labels[mask], pred[mask], labels=[0, 1]).ravel()]
        rows.append({
            "group": group,
            "support": int(mask.sum()),
            "actual_positive": tp + fn,
            "actual_negative": tn + fp,
            "false_negative_rate": float(fn / (fn + tp)) if fn + tp else None,
            "false_positive_rate": float(fp / (fp + tn)) if fp + tn else None,
        })
    return rows

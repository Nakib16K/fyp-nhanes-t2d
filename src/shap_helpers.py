"""Validate SHAP value shapes and truthfully label what is explained.

Important: the source pipeline uses SHAP on one uncalibrated base estimator
from CalibratedClassifierCV, NOT the full isotonic-calibrated ensemble.
"""
import numpy as np

LOCAL_EXPLANATION_SCOPE = (
    "One uncalibrated base estimator from a cross-validation calibration fold; "
    "not the calibrated ensemble probability or its validation-threshold decision."
)
LOCAL_EXPLANATION_SCALE = (
    "Model-specific raw estimator output (e.g. margin/log-odds or tree probability); "
    "SHAP values are not calibrated percentage-point changes."
)


class ExplanationError(ValueError):
    """Unsupported or inconsistent explanation output."""


def positive_class_shap(values, expected_features: int):
    """Return 1D impacts for one sample from SHAP legacy or multi-output form."""
    if isinstance(values, list):
        if len(values) != 2:
            raise ExplanationError("Expected binary SHAP list")
        values = values[1]
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 3 and arr.shape[-1] == 2:
        arr = arr[:, :, 1]
    if arr.ndim != 2 or arr.shape != (1, expected_features):
        raise ExplanationError("Unexpected SHAP feature/sample shape")
    if not np.isfinite(arr).all():
        raise ExplanationError("SHAP values not finite")
    return arr[0]


def positive_class_base(value):
    if isinstance(value, list):
        if len(value) != 2:
            raise ExplanationError("Unexpected SHAP expected value list")
        value = value[1]
    arr = np.asarray(value, dtype=float)
    if arr.size not in (1, 2):
        raise ExplanationError("Unexpected SHAP base value shape")
    result = float(arr.reshape(-1)[-1])
    if not np.isfinite(result):
        raise ExplanationError("Nonfinite SHAP base value")
    return result

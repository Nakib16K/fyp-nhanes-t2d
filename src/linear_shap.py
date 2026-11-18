"""Run-bound training reference for local logistic-regression explanations."""
from pathlib import Path
import hashlib
import json
import math
import os

import numpy as np
import shap

from src.shap_helpers import ExplanationError, positive_class_base, positive_class_shap

LINEAR_SCALE = (
    "Uncalibrated LR log-odds for the positive survey label; "
    "not calibrated probability-point changes."
)


def _read_file(folder, name):
    path = folder / name
    if not folder.is_dir() or any(p.is_symlink() for p in (folder, *folder.parents)):
        raise ExplanationError("Explanation reference directory is unsafe")
    if not path.is_file() or path.is_symlink():
        raise ExplanationError("Explanation reference is missing or unsafe")
    return path


def load_linear_background(run_dir, run_manifest):
    """Verify a separate reference without changing the frozen run manifest."""
    run_dir = Path(run_dir)
    folder = Path(os.getenv("FYP_LOCAL_EXPLANATIONS_DIR", str(run_dir / "local_explanations")))
    manifest = json.loads(_read_file(folder, "manifest.json").read_text(encoding="utf-8"))
    frozen_hash = hashlib.sha256((run_dir / "f1c_manifest.json").read_bytes()).hexdigest()
    model_hash = run_manifest["models"]["lr"]["artifact"]["sha256"]
    if (
        manifest.get("schema") != "fyp-local-explanations-v1"
        or manifest.get("run_id") != run_manifest["run_id"]
        or manifest.get("frozen_manifest_sha256") != frozen_hash
        or manifest.get("lr_model_sha256") != model_hash
    ):
        raise ExplanationError("Explanation reference belongs to a different model run")
    entry = manifest.get("lr_background", {})
    if entry.get("path") != "lr_background.json":
        raise ExplanationError("Unexpected explanation reference path")
    path = _read_file(folder, "lr_background.json")
    if hashlib.sha256(path.read_bytes()).hexdigest() != entry.get("sha256"):
        raise ExplanationError("Explanation reference checksum mismatch")
    data = json.loads(path.read_text(encoding="utf-8"))
    names = data.get("feature_names")
    if (
        data.get("schema") != "fyp-linear-background-v1"
        or data.get("run_id") != run_manifest["run_id"]
        or data.get("lr_model_sha256") != model_hash
        or type(data.get("calibration_fold")) is not int
        or data["calibration_fold"] != 0
        or data.get("reference_kind") != "calibration_fold_training_mean"
        or type(data.get("sample_count")) is not int
        or data["sample_count"] <= 0
        or not isinstance(names, list)
        or not names
        or any(not isinstance(n, str) or not n for n in names)
        or len(set(names)) != len(names)
    ):
        raise ExplanationError("Invalid explanation reference metadata")
    mean = np.asarray(data.get("mean"), dtype=float)
    if mean.shape != (len(names),) or not np.isfinite(mean).all():
        raise ExplanationError("Invalid explanation reference mean")
    return data


def explain_linear(model, transformed, background):
    """Explain one positive-class LR margin using a fixed training mean."""
    if background is None:
        raise ExplanationError("Verified LR explanation reference is unavailable")
    names = list(transformed.columns)
    if names != background["feature_names"] or not np.array_equal(model.classes_, [0, 1]):
        raise ExplanationError("LR class or feature order does not match its reference")
    values = np.asarray(transformed, dtype=float)
    mean = np.asarray(background["mean"], dtype=float)
    if values.shape != (1, len(names)) or not np.isfinite(values).all():
        raise ExplanationError("Invalid transformed LR input")
    if mean.shape != (len(names),) or not np.isfinite(mean).all():
        raise ExplanationError("Invalid LR reference mean")
    # Independent linear SHAP needs only the training mean, not respondent rows.
    explainer = shap.LinearExplainer(model, shap.maskers.Independent(mean.reshape(1, -1)))
    impacts = positive_class_shap(explainer.shap_values(transformed), len(names))
    base = positive_class_base(explainer.expected_value)
    margin = float(np.asarray(model.decision_function(transformed)).reshape(-1)[0])
    total = base + float(impacts.sum())
    if not math.isfinite(margin) or not math.isclose(total, margin, rel_tol=1e-8, abs_tol=1e-8):
        raise ExplanationError("LR explanation does not reconstruct the estimator output")
    return impacts, base, margin, abs(total - margin)

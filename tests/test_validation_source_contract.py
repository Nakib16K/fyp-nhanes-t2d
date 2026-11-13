"""Static validation-protocol integration contracts for the research pipeline.

These read the actual patched src/pipeline.py; do not train or mutate any data.
"""
import ast
from pathlib import Path



def source_contract(source: str) -> dict[str, bool]:
    """Self-contained static checks, runnable inside the isolated FYP copy."""
    ast.parse(source)
    return {
        "validation_split": "X_fit, X_validation, y_fit, y_validation = train_test_split(" in source,
        "outer_holdout_preserved": "X, y, test_size=0.2, stratify=y, random_state=42" in source,
        "cv_training_only": "cross_val_score(pipeline, X_fit, y_fit, cv=cv_split" in source,
        "model_fit_training_only": "best_est.fit(X_fit, y_fit)" in source,
        "calibration_training_only": "calibrated_model.fit(X_fit, y_fit)" in source,
        "training_cache_isolated": "_f1b_train64_seed42.json" in source,
        "threshold_uses_validation": "choose_validation_threshold(y_validation, validation_proba)" in source,
        "test_f1_at_frozen_threshold": "best_f1 = f1_score(y_test, y_pred, zero_division=0)" in source,
        "fairness_uses_frozen_threshold": "subgroup_fairness(\n                y_test, y_proba, X_test[column].to_numpy(), selection" in source,
        "no_test_threshold_optimisation": "_optimize_threshold(" not in source,
    }


def _pipeline():
    p = Path(__file__).resolve().parents[1] / "modified-source" / "src" / "pipeline.py"
    # In prepared local development copy, tests/ is one folder below the FYP root.
    if not p.exists():
        p = Path(__file__).resolve().parents[1] / "src" / "pipeline.py"
    if not p.is_file():
        import pytest
        pytest.skip("Patched FYP workspace is not available in this offline package")
    return p.read_text(encoding="utf-8")


def test_pipeline_parses():
    ast.parse(_pipeline())


def test_training_only_cross_validation_and_calibration():
    c = source_contract(_pipeline())
    assert c["cv_training_only"]
    assert c["model_fit_training_only"]
    assert c["calibration_training_only"]
    assert c["training_cache_isolated"]


def test_validation_threshold_and_frozen_test_metrics():
    c = source_contract(_pipeline())
    assert c["threshold_uses_validation"]
    assert c["test_f1_at_frozen_threshold"]
    assert c["no_test_threshold_optimisation"]


def test_original_holdout_and_fairness():
    c = source_contract(_pipeline())
    assert c["outer_holdout_preserved"]
    assert c["validation_split"]
    assert c["fairness_uses_frozen_threshold"]


def test_api_uses_model_specific_decision_rule():
    # Regression check for the corrected, model-specific decision rule.
    root = Path(__file__).resolve().parents[1]
    api = root / "api" / "main.py"
    if not api.exists():
        import pytest
        pytest.skip("API is only present after installation into the isolated FYP copy")
    assert 'classify_probability(prob, thresholds[model_name])' in api.read_text(encoding="utf-8")

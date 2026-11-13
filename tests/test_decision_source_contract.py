"""Decision source contracts against the current application."""
from pathlib import Path
import ast
import pytest


def _source(rel):
    root=Path(__file__).resolve().parents[1]
    path=root/rel
    if not path.is_file():
        pytest.skip("Source check requires locally installed project source")
    return path.read_text(encoding='utf-8')


def test_api_syntax():
    ast.parse(_source('api/main.py'))


def test_api_reads_run_bound_thresholds():
    s=_source('api/main.py')
    assert 'ready, rejected = choose_latest_complete(REPORTS_DIR)' in s
    assert '"thresholds": {name.upper(): meta["models"][name]["threshold"]' in s
    assert 'validate_model_thresholds(ml_registry["models"], ml_registry.get("thresholds"))' in s


def test_api_does_not_fall_back_to_half():
    s=_source('api/main.py')
    assert 'classify_probability(prob, thresholds[model_name])' in s
    assert '"High Risk" if prob >= 0.5 else "Low Risk"' not in s
    assert 'detail="Verified model thresholds unavailable."' in s


def test_pipeline_protocol_untouched():
    s=_source('src/pipeline.py')
    assert 'choose_validation_threshold(y_validation, validation_proba)' in s
    assert 'best_f1 = f1_score(y_test, y_pred, zero_division=0)' in s
    assert 'write_manifest(' in s


def test_presets_and_custom_disclose_decision_rule():
    preset=_source('frontend/src/components/Exploratory/PresetCard.tsx')
    custom=_source('frontend/src/components/Exploratory/ExploratoryMode.tsx')
    assert "Each threshold was selected on validation data" in preset
    assert "not a medical cutoff" in preset
    assert "Each flag compares the model's full-precision estimate" in custom
    assert "clinically validated" in custom


def test_typescript_interface_includes_optional_fields():
    ts=_source('frontend/src/types/index.ts')
    assert 'decision_threshold?: number' in ts
    assert 'threshold_source?: "validation"' in ts

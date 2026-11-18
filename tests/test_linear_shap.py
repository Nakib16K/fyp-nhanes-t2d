"""Synthetic linear explanation and reference-integrity checks; no model fitting."""
import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from src.linear_shap import explain_linear, load_linear_background
from src.shap_helpers import ExplanationError


def model():
    result = LogisticRegression()
    result.classes_ = np.array([0, 1])
    result.coef_ = np.array([[2.0, -0.5]])
    result.intercept_ = np.array([-1.0])
    result.n_features_in_ = 2
    result.feature_names_in_ = np.array(['a', 'b'])
    return result


def reference():
    return {'feature_names': ['a', 'b'], 'mean': [0.25, 2.0], 'sample_count': 4}


def test_linear_impacts_reconstruct_margin_and_use_fixed_reference():
    first = pd.DataFrame([[1.0, 4.0]], columns=['a', 'b'])
    second = pd.DataFrame([[2.0, 1.0]], columns=['a', 'b'])
    a, base, margin, error = explain_linear(model(), first, reference())
    b, second_base, second_margin, _ = explain_linear(model(), second, reference())
    np.testing.assert_allclose(a, [1.5, -1.0])
    assert base == pytest.approx(-1.5)
    assert base + a.sum() == pytest.approx(margin)
    assert error < 1e-12
    assert second_base == base
    assert not np.array_equal(a, b)
    assert second_margin != margin


@pytest.mark.parametrize('fault', ['order', 'class', 'nan_mean', 'shape', 'nonfinite_input', 'additivity'])
def test_inconsistent_linear_explanations_fail(fault):
    fitted = model()
    background = reference()
    frame = pd.DataFrame([[1.0, 4.0]], columns=['a', 'b'])
    if fault == 'order':
        background['feature_names'].reverse()
    elif fault == 'class':
        fitted.classes_ = np.array([1, 0])
    elif fault == 'nan_mean':
        background['mean'][0] = float('nan')
    elif fault == 'shape':
        background['mean'] = [0.0]
    elif fault == 'nonfinite_input':
        frame.iloc[0, 0] = float('inf')
    else:
        fitted.decision_function = lambda _: np.array([100.0])
    with pytest.raises(ExplanationError):
        explain_linear(fitted, frame, background)


def write_reference(tmp_path):
    run = tmp_path / 'run_synthetic'
    folder = run / 'local_explanations'
    folder.mkdir(parents=True)
    manifest = {'run_id': run.name, 'models': {'lr': {'artifact': {'sha256': 'a' * 64}}}}
    (run / 'f1c_manifest.json').write_text(json.dumps(manifest))
    data = {
        'schema': 'fyp-linear-background-v1', 'run_id': run.name,
        'lr_model_sha256': 'a' * 64, 'calibration_fold': 0,
        'reference_kind': 'calibration_fold_training_mean', **reference(),
    }
    path = folder / 'lr_background.json'
    path.write_text(json.dumps(data))
    metadata = {
        'schema': 'fyp-local-explanations-v1', 'run_id': run.name,
        'frozen_manifest_sha256': hashlib.sha256((run / 'f1c_manifest.json').read_bytes()).hexdigest(),
        'lr_model_sha256': 'a' * 64,
        'lr_background': {'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()},
    }
    (folder / 'manifest.json').write_text(json.dumps(metadata))
    return run, manifest, data, metadata


def test_reference_is_bound_to_model_run_and_hash(tmp_path, monkeypatch):
    monkeypatch.delenv('FYP_LOCAL_EXPLANATIONS_DIR', raising=False)
    run, manifest, _, _ = write_reference(tmp_path)
    result = load_linear_background(run, manifest)
    assert result['feature_names'] == ['a', 'b']
    assert result['mean'] == [.25, 2.0]


@pytest.mark.parametrize('fault', ['corrupt', 'run', 'model', 'fold', 'population', 'nan', 'duplicate', 'path', 'frozen_manifest'])
def test_background_artifact_rejects_drift(tmp_path, monkeypatch, fault):
    monkeypatch.delenv('FYP_LOCAL_EXPLANATIONS_DIR', raising=False)
    run, manifest, data, metadata = write_reference(tmp_path)
    path = run / 'local_explanations/lr_background.json'
    if fault == 'corrupt':
        path.write_text(path.read_text() + ' ')
    elif fault == 'path':
        metadata['lr_background']['path'] = '../outside.json'
    elif fault == 'frozen_manifest':
        (run / 'f1c_manifest.json').write_text('{}')
    else:
        changes = {'run': ('run_id', 'other'), 'model': ('lr_model_sha256', 'b' * 64), 'fold': ('calibration_fold', 1), 'population': ('reference_kind', 'current_request'), 'nan': ('mean', [float('nan'), 2.0]), 'duplicate': ('feature_names', ['a', 'a'])}
        key, value = changes[fault]
        data[key] = value
        path.write_text(json.dumps(data))
        metadata['lr_background']['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    (run / 'local_explanations/manifest.json').write_text(json.dumps(metadata))
    with pytest.raises(ExplanationError):
        load_linear_background(run, manifest)

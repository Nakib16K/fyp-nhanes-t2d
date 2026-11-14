"""Real FastAPI regression tests using mocks and no NHANES or model files."""
from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
import api.main as api

PAYLOAD = {
    'age_years': 45,
    'gender_code': 1,
    'ethnicity_code': 3,
    'education_level': 3,
    'poverty_ratio': 2.5,
    'height_cm': 175.0,
    'weight_kg': 85.0,
    'waist_circumference': 95.0,
    'systolic_bp': 128,
    'diastolic_bp': 82,
    'pulse_60s': 72,
    'smoked_100_cigs': 1,
    'vigorous_activity': 2,
    'family_history_diabetes': 1,
    'history_high_bp': 1,
}

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'REPORTS_DIR', str(tmp_path))
    api.ml_registry.update({'models': {}, 'metrics': [], 'thresholds': {}, 'latest_run_dir': None, 'active_run_id': None})
    # Route-level tests deliberately do not enter the production model-loading
    # lifespan. Dedicated lifecycle tests validate real startup and fail-fast paths.
    client = TestClient(api.app)
    try:
        yield client
    finally:
        client.close()
        api.ml_registry.update({'models': {}, 'metrics': [], 'thresholds': {}, 'latest_run_dir': None, 'active_run_id': None})


def test_no_store_headers_and_local_origin(client):
    r = client.get('/api/exploratory/presets', headers={'Origin': 'http://localhost:5173'})
    assert r.status_code == 200
    assert r.headers['cache-control'] == 'private, no-store'
    assert r.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert r.headers['pragma'] == 'no-cache'


def test_untrusted_origin_disallowed(client):
    r = client.get('/api/exploratory/presets', headers={'Origin': 'https://untrusted.example'})
    assert r.status_code == 200
    assert 'access-control-allow-origin' not in r.headers


def test_prediction_no_cache_and_threshold_preserved(client):
    m = MagicMock()
    m.predict_proba.return_value = [[.6, .4]]
    api.ml_registry['models'] = {'XGB': m}
    api.ml_registry['thresholds'] = {'XGB': .28}
    r = client.post('/api/exploratory/predict/custom', json=PAYLOAD)
    assert r.status_code == 200
    assert r.headers['cache-control'] == 'private, no-store'
    assert r.json()['predictions']['XGB']['prediction_class'] == 'High Risk'
    assert r.json()['predictions']['XGB']['threshold_source'] == 'validation'


def test_local_shap_explicitly_not_calibrated(client, monkeypatch):
    estimator = MagicMock()
    estimator.named_steps = {'preprocessor': MagicMock(), 'model': MagicMock()}
    estimator.named_steps['preprocessor'].transform.return_value = pd.DataFrame([[1., 2.]], columns=['a', 'b'])
    estimator.named_steps['preprocessor'].feature_names_out = ['a', 'b']
    ensemble = MagicMock()
    ensemble.calibrated_classifiers_ = [MagicMock(estimator=estimator)]
    api.ml_registry['models'] = {'XGB': ensemble}
    explainer = MagicMock()
    explainer.shap_values.return_value = np.array([[.2, -.1]])
    explainer.expected_value = -.2
    monkeypatch.setattr(api.shap, 'TreeExplainer', lambda _: explainer)
    r = client.post('/api/exploratory/predict/custom/shap/XGB', json=PAYLOAD)
    assert r.status_code == 200, r.text
    obj = r.json()
    assert obj['explains_calibrated_probability'] is False
    assert 'not the calibrated ensemble probability' in obj['explanation_scope']
    assert obj['base_value'] == -.2
    assert obj['shap_values_sorted'][0]['feature'] == 'a'


def test_local_shap_failure_does_not_return_exception_or_patient_input(client, monkeypatch):
    calibrated = MagicMock()
    calibrated.calibrated_classifiers_ = [MagicMock(estimator=MagicMock())]
    api.ml_registry['models'] = {'XGB': calibrated}
    monkeypatch.setattr(api.shap, 'TreeExplainer', lambda _: (_ for _ in ()).throw(ValueError('secret-123')))
    r = client.post('/api/exploratory/predict/custom/shap/XGB', json=PAYLOAD)
    assert r.status_code == 500
    assert 'secret-123' not in r.text
    assert 'Feature explanation unavailable' in r.text


def test_local_rf_multioutput_shape_and_base_value(client, monkeypatch):
    preprocessor = MagicMock()
    preprocessor.transform.return_value = pd.DataFrame([[.3, .7]], columns=['a', 'b'])
    preprocessor.feature_names_out = ['a', 'b']
    estimator = MagicMock()
    estimator.named_steps = {'preprocessor': preprocessor, 'model': MagicMock()}
    ensemble = MagicMock()
    ensemble.calibrated_classifiers_ = [MagicMock(estimator=estimator)]
    api.ml_registry['models'] = {'RF': ensemble}
    explainer = MagicMock()
    explainer.shap_values.return_value = np.array([[[.1, .3], [.2, -.4]]])
    explainer.expected_value = np.array([.2, .8])
    monkeypatch.setattr(api.shap, 'TreeExplainer', lambda _: explainer)
    response = client.post('/api/exploratory/predict/custom/shap/RF', json=PAYLOAD)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['base_value'] == .8
    assert data['shap_values_sorted'][0]['impact'] == -.4
    assert data['explains_calibrated_probability'] is False


def test_inference_exception_returns_503_without_leaking_payload(client, caplog):
    model = MagicMock()
    model.predict_proba.side_effect = ValueError('private-input-marker-123')
    api.ml_registry['models'] = {'XGB': model}
    api.ml_registry['thresholds'] = {'XGB': .28}
    r = client.post('/api/exploratory/predict/custom', json=PAYLOAD)
    assert r.status_code == 503
    assert 'private-input-marker-123' not in r.text
    assert 'private-input-marker-123' not in caplog.text
    assert 'Prediction unavailable.' in r.text

"""Prediction API contracts: offline mocked models, no private data."""
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
import api.main as api

VALID = {
    'age_years': 45,
    'gender_code': 1,
    'ethnicity_code': 7,
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

def _client():
    mock = MagicMock()
    mock.predict_proba.return_value = [[0.6, 0.4]]
    api.ml_registry.update({'models': {'XGB': mock},
        'metrics': [{'Model': 'XGB', 'AUC': 0.84}], 'thresholds': {'XGB': 0.28},
        'latest_run_dir': None, 'active_run_id': None})
    return TestClient(api.app)

def test_corrected_code7_allowed_for_prediction():
    with _client() as c:
        r = c.post('/api/exploratory/predict/custom', json=VALID)
    assert r.status_code == 200, r.text
    assert r.json()['predictions']['XGB']['threshold_source'] == 'validation'

def test_invalid_ethnicity_code5_rejected():
    with _client() as c:
        r = c.post('/api/exploratory/predict/custom', json={**VALID, 'ethnicity_code': 5})
    assert r.status_code == 422

def test_retired_alcohol_not_required_or_accepted():
    with _client() as c:
        assert c.post('/api/exploratory/predict/custom', json=VALID).status_code == 200
        r = c.post('/api/exploratory/predict/custom', json={**VALID, 'alcohol_frequency': 50})
    assert r.status_code == 422

def test_presets_exclude_unused_predictor():
    with _client() as c:
        presets = c.get('/api/exploratory/presets')
    assert presets.status_code == 200
    assert all('alcohol_frequency' not in p for p in presets.json().values())

def test_exact_corrected_predictor_input_contract():
    keys = set(api.PatientInput.model_fields)
    assert len(keys) == 15
    assert 'alcohol_frequency' not in keys
    assert set(api.PatientInput.model_fields['ethnicity_code'].annotation.__args__) == {1, 2, 3, 4, 6, 7}

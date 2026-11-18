from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression

import api.main as api

PAYLOAD = {
    'age_years': 45, 'gender_code': 1, 'ethnicity_code': 7, 'education_level': 3,
    'poverty_ratio': 2.5, 'height_cm': 175.0, 'weight_kg': 85.0,
    'waist_circumference': 95.0, 'systolic_bp': 128, 'diastolic_bp': 82,
    'pulse_60s': 72, 'smoked_100_cigs': 1, 'vigorous_activity': 2,
    'family_history_diabetes': 1, 'history_high_bp': 1,
}


@pytest.fixture
def routes_client(monkeypatch):
    # Route tests avoid entering the real artifact-loading lifespan.
    monkeypatch.setattr(api, 'ml_registry', {
        'models': {}, 'metrics': [], 'thresholds': {}, 'latest_run_dir': None,
        'active_run_id': None, 'linear_background': None,
    })
    monkeypatch.setattr(api, '_build_label_map', lambda _: {})
    result = TestClient(api.app)
    yield result
    result.close()


def linear_model():
    fitted = LogisticRegression()
    fitted.classes_ = np.array([0, 1])
    fitted.coef_ = np.array([[0.1, 0.2]])
    fitted.intercept_ = np.array([-4.0])
    fitted.n_features_in_ = 2
    fitted.feature_names_in_ = np.array(['age_years', 'education_level'])
    preprocessor = SimpleNamespace(
        feature_names_out=['age_years', 'education_level'],
        transform=lambda frame: frame[['age_years', 'education_level']].fillna(3),
    )
    raw = SimpleNamespace(named_steps={'preprocessor': preprocessor, 'model': fitted})
    return SimpleNamespace(calibrated_classifiers_=[SimpleNamespace(estimator=raw)])


def test_lr_local_endpoint_returns_additive_log_odds(routes_client):
    api.ml_registry['models'] = {'LR': linear_model()}
    api.ml_registry['linear_background'] = {'feature_names': ['age_years', 'education_level'], 'mean': [40.0, 3.0], 'sample_count': 4}
    result = routes_client.post('/api/exploratory/predict/custom/shap/LR', json=PAYLOAD)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['model'] == 'LR'
    assert data['explanation_method'] == 'linear_interventional'
    assert data['explains_calibrated_probability'] is False
    assert 'log-odds' in data['explanation_scale']
    assert data['additivity_error'] < 1e-12
    assert data['base_value'] + sum(x['impact'] for x in data['shap_values_sorted']) == pytest.approx(data['estimator_output'])


def test_lr_missing_reference_is_clear_unavailability(routes_client):
    api.ml_registry['models'] = {'LR': linear_model()}
    result = routes_client.post('/api/exploratory/predict/custom/shap/lr', json=PAYLOAD)
    assert result.status_code == 503
    assert 'reference unavailable' in result.json()['detail']


def test_unknown_education_uses_same_missing_frame_for_prediction_and_shap(routes_client):
    frames = []

    def predict(frame):
        frames.append(frame.copy())
        return np.array([[.7, .3]])

    lr = linear_model()
    original_transform = lr.calibrated_classifiers_[0].estimator.named_steps['preprocessor'].transform

    def transform(frame):
        frames.append(frame.copy())
        return original_transform(frame)

    lr.calibrated_classifiers_[0].estimator.named_steps['preprocessor'].transform = transform
    lr.predict_proba = predict
    api.ml_registry['models'] = {name: lr for name in ['LR', 'XGB', 'LGBM', 'RF']}
    api.ml_registry['thresholds'] = {name: .25 for name in api.ml_registry['models']}
    api.ml_registry['linear_background'] = {'feature_names': ['age_years', 'education_level'], 'mean': [40.0, 3.0], 'sample_count': 4}
    payload = {**PAYLOAD, 'education_level': None}
    prediction = routes_client.post('/api/exploratory/predict/custom', json=payload)
    explanation = routes_client.post('/api/exploratory/predict/custom/shap/LR', json=payload)
    assert prediction.status_code == explanation.status_code == 200
    assert set(prediction.json()['predictions']) == {'LR', 'XGB', 'LGBM', 'RF'}
    assert prediction.json()['imputed_features'] == explanation.json()['imputed_features'] == ['education_level']
    assert len(frames) == 5
    assert all(pd.isna(frame.iloc[0]['education_level']) for frame in frames)
    for frame in frames[1:]:
        pd.testing.assert_frame_equal(frame, frames[0])


@pytest.mark.parametrize('level', [0, 6, 7, 9, 10])
def test_raw_nonresponse_codes_are_not_attainment_levels(routes_client, level):
    response = routes_client.post('/api/exploratory/predict/custom', json={**PAYLOAD, 'education_level': level})
    assert response.status_code == 422


@pytest.mark.parametrize('level', [1, 2, 3, 4, 5, None])
def test_supported_education_schema(level):
    assert api.PatientInput(**{**PAYLOAD, 'education_level': level}).education_level == level

from types import SimpleNamespace
from unittest.mock import MagicMock

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
def routes_client(client, monkeypatch):
    monkeypatch.setattr(api, '_build_label_map', lambda _: {})
    return client


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


def test_shap_one_hot_indicator_status_labels_absence(client, patient_input, monkeypatch):
    names = ['ethnicity_code_3.0', 'ethnicity_code_7.0', 'age_years']
    preproc = MagicMock()
    preproc.transform.return_value = pd.DataFrame([[0.0, 1.0, 0.3]], columns=names)
    preproc.feature_names_out = names
    raw = MagicMock()
    raw.named_steps = {'preprocessor': preproc, 'model': MagicMock()}
    ens = MagicMock()
    ens.calibrated_classifiers_ = [MagicMock(estimator=raw)]
    explainer = MagicMock()
    explainer.shap_values.return_value = np.array([[0.2, -0.5, 0.1]])
    explainer.expected_value = 0.0
    monkeypatch.setattr(api.shap, 'TreeExplainer', lambda model: explainer)
    previous = api.ml_registry.copy()
    try:
        api.ml_registry.update({'models': {'XGB': ens}, 'metrics': [{'Model': 'XGB', 'AUC': .8}],
                                'latest_run_dir': None, 'thresholds': {}})
        r = client.post('/api/exploratory/predict/custom/shap/XGB', json=patient_input)
        assert r.status_code == 200, r.text
        d = r.json()['shap_values_sorted']
        states = {item['feature']: item.get('indicator_state') for item in d}
        assert states['Ethnicity: Non-Hispanic White'] == 'absent'
        assert states['Ethnicity: Other Race (including Multi-Racial)'] == 'present'
        assert states['Age (years)'] is None
        assert r.json()['explains_calibrated_probability'] is False
    finally:
        api.ml_registry.clear()
        api.ml_registry.update(previous)


def test_local_shap_explicitly_not_calibrated(client, patient_input, monkeypatch):
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
    r = client.post('/api/exploratory/predict/custom/shap/XGB', json=patient_input)
    assert r.status_code == 200, r.text
    obj = r.json()
    assert obj['explains_calibrated_probability'] is False
    assert 'not the calibrated ensemble probability' in obj['explanation_scope']
    assert obj['base_value'] == -.2
    assert obj['shap_values_sorted'][0]['feature'] == 'a'


def test_local_rf_multioutput_shape_and_base_value(client, patient_input, monkeypatch):
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
    response = client.post('/api/exploratory/predict/custom/shap/RF', json=patient_input)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['base_value'] == .8
    assert data['shap_values_sorted'][0]['impact'] == -.4
    assert data['explains_calibrated_probability'] is False


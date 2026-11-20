"""Real FastAPI regression tests using mocks and no NHANES or model files."""
from unittest.mock import MagicMock
import api.main as api




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


def test_prediction_no_cache_and_threshold_preserved(client, patient_input):
    m = MagicMock()
    m.predict_proba.return_value = [[.6, .4]]
    api.ml_registry['models'] = {'XGB': m}
    api.ml_registry['thresholds'] = {'XGB': .28}
    r = client.post('/api/exploratory/predict/custom', json=patient_input)
    assert r.status_code == 200
    assert r.headers['cache-control'] == 'private, no-store'
    assert r.json()['predictions']['XGB']['prediction_class'] == 'High Risk'
    assert r.json()['predictions']['XGB']['threshold_source'] == 'validation'




def test_local_shap_failure_does_not_return_exception_or_patient_input(client, patient_input, monkeypatch, caplog, capsys):
    calibrated = MagicMock()
    calibrated.calibrated_classifiers_ = [MagicMock(estimator=MagicMock())]
    api.ml_registry['models'] = {'XGB': calibrated}
    monkeypatch.setattr(api.shap, 'TreeExplainer', lambda _: (_ for _ in ()).throw(ValueError('secret-123')))
    r = client.post('/api/exploratory/predict/custom/shap/XGB', json=patient_input)
    assert r.status_code == 500
    assert 'secret-123' not in r.text
    assert 'secret-123' not in caplog.text
    assert 'secret-123' not in capsys.readouterr().err
    assert 'Feature explanation unavailable' in r.text




def test_inference_exception_returns_503_without_leaking_payload(client, patient_input, caplog):
    model = MagicMock()
    model.predict_proba.side_effect = ValueError('private-input-marker-123')
    api.ml_registry['models'] = {'XGB': model}
    api.ml_registry['thresholds'] = {'XGB': .28}
    r = client.post('/api/exploratory/predict/custom', json=patient_input)
    assert r.status_code == 503
    assert 'private-input-marker-123' not in r.text
    assert 'private-input-marker-123' not in caplog.text
    assert 'Prediction unavailable.' in r.text

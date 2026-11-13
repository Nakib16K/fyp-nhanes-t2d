"""FastAPI decision regressions using mocked models.

Mocked models only; no NHANES data downloads, model deserialization or retraining.
"""
import math
from unittest.mock import MagicMock
import pytest


PAYLOAD={
    "age_years":45,"gender_code":1,"ethnicity_code":3,"education_level":3,
    "poverty_ratio":2.5,"height_cm":175.0,"weight_kg":85.0,
    "waist_circumference":95.0,"systolic_bp":128,"diastolic_bp":82,
    "pulse_60s":72,"smoked_100_cigs":1,
    "vigorous_activity":2,"family_history_diabetes":1,"history_high_bp":1,
}


def _ctx():
    try:
        import api.main as app_module
        from fastapi.testclient import TestClient
    except ImportError:
        pytest.skip("Requires installed project source and FastAPI dependencies")
    return app_module,TestClient


def _model(prob):
    m=MagicMock()
    m.predict_proba.return_value=[[1-prob,prob]]
    return m


def _seed(app_module, probs=None, thresholds=None):
    probs=probs or {"XGB":0.4,"RF":0.4,"LGBM":0.4,"LR":0.4}
    app_module.ml_registry.update({
        "models":{name:_model(p) for name,p in probs.items()},
        "thresholds":thresholds if thresholds is not None else
            {"XGB":0.28,"RF":0.35,"LGBM":0.42,"LR":0.5},
        "metrics":[{"Model":name,"AUC":0.8} for name in probs],
        "latest_run_dir":None,"active_run_id":None,
    })


def test_per_model_classifications_are_independent():
    api,Client=_ctx()
    _seed(api)
    with Client(api.app) as client:
        r=client.post('/api/exploratory/predict/custom',json=PAYLOAD)
        assert r.status_code==200, r.text
        p=r.json()['predictions']
        assert {n:v['prediction_class'] for n,v in p.items()}=={
            "XGB":"High Risk","RF":"High Risk","LGBM":"Low Risk","LR":"Low Risk"
        }
        assert p['XGB']['risk_percentage']=='40.0%'
        assert p['XGB']['probability_score']==0.4
        assert p['XGB']['decision_threshold']==0.28
        assert p['RF']['decision_threshold']==0.35
        assert all(v['threshold_source']=='validation' for v in p.values())


def test_exact_boundary_is_high_risk():
    api,Client=_ctx()
    _seed(api,{"XGB":0.28},{"XGB":0.28})
    with Client(api.app) as client:
        r=client.post('/api/exploratory/predict/custom',json=PAYLOAD)
        assert r.status_code==200, r.text
        assert r.json()['predictions']['XGB']['prediction_class']=='High Risk'


def test_risk_is_decided_before_rounding():
    api,Client=_ctx()
    _seed(api,{"XGB":0.2799999},{"XGB":0.28})
    with Client(api.app) as client:
        p=client.post('/api/exploratory/predict/custom',json=PAYLOAD).json()['predictions']['XGB']
        assert p['probability_score']==0.28
        assert p['prediction_class']=='Low Risk'


@pytest.mark.parametrize("bad", [None,{}, {"XGB":0.28},
       {"XGB":float('nan'),"RF":0.3,"LGBM":0.4,"LR":0.5},
       {"XGB":0.28,"RF":0.3,"LGBM":0.4,"LR":0.5,"GHOST":0.1}])
def test_metadata_missing_or_invalid_is_503(bad):
    api,Client=_ctx()
    _seed(api)
    api.ml_registry['thresholds']=bad
    with Client(api.app) as client:
        r=client.post('/api/exploratory/predict/custom',json=PAYLOAD)
        assert r.status_code==503
        assert 'threshold' in r.json()['detail'].lower()


def test_presets_use_the_same_prediction_endpoint():
    api,Client=_ctx()
    _seed(api)
    with Client(api.app) as client:
        presets=client.get('/api/exploratory/presets')
        assert presets.status_code==200
        for payload in presets.json().values():
            r=client.post('/api/exploratory/predict/custom',json=payload)
            assert r.status_code==200, r.text
            assert r.json()['predictions']['XGB']['decision_threshold']==0.28


def test_no_model_remains_offline():
    api, Client = _ctx()

    # Preseed explicit mocks before the verified-startup gate.
    # This test covers models becoming unavailable after successful startup.
    _seed(api)
    with Client(api.app) as client:
        # Simulate the models becoming unavailable AFTER startup.
        api.ml_registry.update({
            'models': {},
            'metrics': [],
            'thresholds': {},
            'latest_run_dir': None,
            'active_run_id': None
        })

        r = client.post(
            '/api/exploratory/predict/custom',
            json=PAYLOAD
        )

        assert r.status_code == 503

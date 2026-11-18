"""API regression tests with mocked model registry; no real patient/model files."""
from fastapi.testclient import TestClient
from pathlib import Path
import api.main as api
import pytest

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
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(api, 'REPORTS_DIR', str(tmp_path))
    # Middleware and route tests do not invoke the model-loading lifespan.
    # Real startup and fail-fast are tested separately in lifecycle tests.
    api.ml_registry.update({'models': {}, 'metrics': [], 'thresholds': {}, 'latest_run_dir': None, 'active_run_id': None})
    client = TestClient(api.app)
    try:
        yield client
    finally:
        client.close()
        api.ml_registry.update({'models': {}, 'metrics': [], 'thresholds': {}, 'latest_run_dir': None, 'active_run_id': None})


def test_refuse_unknown_host(client):
    r = client.get('/health', headers={'host': 'hostile.example'})
    assert r.status_code == 400


def test_local_preflight_accepts_signed_json_headers(client):
    r = client.options('/api/exploratory/predict/custom', headers={
        'origin': 'http://localhost:5173',
        'access-control-request-method': 'POST',
        'access-control-request-headers': 'content-type,x-amz-content-sha256',
    })
    assert r.status_code == 200
    assert r.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert 'x-amz-content-sha256' in r.headers['access-control-allow-headers'].lower()


def test_signed_header_does_not_relax_origin_allowlist(client):
    r = client.options('/api/exploratory/predict/custom', headers={
        'origin': 'https://untrusted.example',
        'access-control-request-method': 'POST',
        'access-control-request-headers': 'content-type,x-amz-content-sha256',
    })
    assert r.status_code == 400
    assert 'access-control-allow-origin' not in r.headers


def test_prediction_json_required(client):
    r = client.post('/api/exploratory/predict/custom', data='x', headers={'content-type': 'text/plain'})
    assert r.status_code == 415
    assert r.headers['cache-control'] == 'private, no-store'


def test_prediction_too_large(client):
    r = client.post('/api/exploratory/predict/custom', json={'filler': 'x' * 9000})
    assert r.status_code == 413
    assert 'filler' not in r.text


def test_normal_payload_uses_existing_endpoint(client):
    # Models absent: a syntactically valid request reaches the normal
    # unavailable-model check. No new threshold or inference path introduced.
    api.ml_registry.update({'models': {}, 'metrics': [], 'thresholds': {}, 'latest_run_dir': None, 'active_run_id': None})
    r = client.post('/api/exploratory/predict/custom', json=PAYLOAD)
    assert r.status_code == 503
    assert r.headers['x-content-type-options'] == 'nosniff'
    assert r.headers['referrer-policy'] == 'no-referrer'


@pytest.mark.parametrize('endpoint', [ '/api/models/UNKNOWN/shap/global', '/api/models/UNKNOWN/interpretation'])
def test_model_path_name_allowlisted(client, endpoint):
    r = client.get(endpoint)
    assert r.status_code == 404
    assert r.json()['detail'] == 'Unknown model.'

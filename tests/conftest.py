import pytest
from fastapi.testclient import TestClient

import api.main as api


@pytest.fixture
def patient_input():
    return {
        'age_years': 45, 'gender_code': 1, 'ethnicity_code': 7,
        'education_level': 3, 'poverty_ratio': 2.5, 'height_cm': 175.0,
        'weight_kg': 85.0, 'waist_circumference': 95.0,
        'systolic_bp': 128, 'diastolic_bp': 82, 'pulse_60s': 72,
        'smoked_100_cigs': 1, 'vigorous_activity': 2,
        'family_history_diabetes': 1, 'history_high_bp': 1,
    }


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Route tests do not enter model-loading startup; lifecycle tests do.
    monkeypatch.setattr(api, 'REPORTS_DIR', str(tmp_path))
    monkeypatch.setattr(api, 'ml_registry', {
        'models': {}, 'metrics': [], 'thresholds': {},
        'latest_run_dir': None, 'active_run_id': None,
        'linear_background': None,
    })
    with_client = TestClient(api.app)
    try:
        yield with_client
    finally:
        with_client.close()

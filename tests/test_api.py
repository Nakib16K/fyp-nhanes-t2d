# ============================================================
# API INTEGRATION TESTS — FASTAPI BACKEND
# ============================================================
# Uses FastAPI's TestClient with a mocked ml_registry so tests
# run without trained model files or a completed pipeline run.
#
# Four endpoint groups are covered:
#   1. Health check         — /health
#   2. Metrics endpoint     — /api/models/metrics
#   3. Presets endpoint     — /api/exploratory/presets
#   4. Prediction endpoint  — /api/exploratory/predict/custom
#
# Run from project root:
#   pytest tests/test_api.py -v
# ============================================================

import pytest
import numpy as np
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

import api.main as main_module


# ------------------------------------------------------------
# SHARED FIXTURES & HELPERS
# ------------------------------------------------------------

# Minimal valid PatientInput payload — all fields within accepted ranges
VALID_PAYLOAD = {
    "age_years": 45,
    "gender_code": 1,
    "ethnicity_code": 3,
    "education_level": 3,
    "poverty_ratio": 2.5,
    "height_cm": 175.0,
    "weight_kg": 85.0,
    "waist_circumference": 95.0,
    "systolic_bp": 128,
    "diastolic_bp": 82,
    "pulse_60s": 72,
    "smoked_100_cigs": 1,
    "alcohol_frequency": 100,
    "vigorous_activity": 2,
    "family_history_diabetes": 1,
    "history_high_bp": 1,
}


def _make_mock_model():
    # Mock calibrated pipeline that returns a fixed probability of 0.7
    model = MagicMock()
    model.predict_proba.return_value = np.array([[0.3, 0.7]])
    return model


@pytest.fixture
def client():
    # -----------------------------------------------------------
    # TEST CLIENT SETUP
    # Injects mock models and metrics directly into ml_registry.
    # The lifespan startup is bypassed — no .pkl files or run
    # directories are required on the host machine.
    # -----------------------------------------------------------
    main_module.ml_registry["models"] = {
        "XGB":  _make_mock_model(),
        "LGBM": _make_mock_model(),
        "RF":   _make_mock_model(),
        "LR":   _make_mock_model(),
    }
    main_module.ml_registry["metrics"] = [
        {"Model": "XGB",  "AUC": 0.847, "F1_Score": 0.564,
         "Precision": 0.484, "Recall_Sensitivity": 0.676, "Accuracy": 0.816},
        {"Model": "LGBM", "AUC": 0.845, "F1_Score": 0.560,
         "Precision": 0.483, "Recall_Sensitivity": 0.667, "Accuracy": 0.816},
        {"Model": "RF",   "AUC": 0.840, "F1_Score": 0.555,
         "Precision": 0.472, "Recall_Sensitivity": 0.674, "Accuracy": 0.810},
        {"Model": "LR",   "AUC": 0.835, "F1_Score": 0.537,
         "Precision": 0.430, "Recall_Sensitivity": 0.715, "Accuracy": 0.783},
    ]
    main_module.ml_registry["latest_run_dir"] = None

    with TestClient(main_module.app, raise_server_exceptions=True) as c:
        yield c


# ------------------------------------------------------------
# TEST CLASS 1 — HEALTH CHECK
# Verifies that the application starts and correctly reports
# the number of models loaded into the registry.
# ------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_health_reports_four_models_loaded(self, client):
        data = client.get("/health").json()
        assert "models_loaded" in data
        assert len(data["models_loaded"]) == 4


# ------------------------------------------------------------
# TEST CLASS 2 — METRICS ENDPOINT
# Verifies response structure: four model entries, each with
# the required keys matching the React ModelMetrics interface.
# ------------------------------------------------------------

class TestMetricsEndpoint:

    def test_metrics_returns_200(self, client):
        assert client.get("/api/models/metrics").status_code == 200

    def test_metrics_returns_four_models(self, client):
        assert len(client.get("/api/models/metrics").json()) == 4

    def test_metrics_each_entry_has_required_keys(self, client):
        # Each entry must contain the keys expected by the React frontend
        required_keys = {"model_name", "auc_roc", "f1", "precision", "recall", "accuracy"}
        for entry in client.get("/api/models/metrics").json():
            assert required_keys.issubset(entry.keys()), (
                f"Entry missing required keys: {required_keys - entry.keys()}"
            )


# ------------------------------------------------------------
# TEST CLASS 3 — PRESETS ENDPOINT
# Verifies that exactly three risk profiles are returned and
# that all preset age values satisfy the study population gate.
# ------------------------------------------------------------

class TestPresetsEndpoint:

    def test_presets_returns_200(self, client):
        assert client.get("/api/exploratory/presets").status_code == 200

    def test_presets_returns_exactly_three_profiles(self, client):
        data = client.get("/api/exploratory/presets").json()
        assert set(data.keys()) == {"healthy", "elevated_risk", "high_risk"}, (
            f"Expected 3 preset keys, got: {set(data.keys())}"
        )

    def test_each_preset_age_satisfies_minimum(self, client):
        # All presets must have age_years >= 20 to match the study population gate
        for name, preset in client.get("/api/exploratory/presets").json().items():
            assert preset["age_years"] >= 20, (
                f"Preset '{name}' has age_years={preset['age_years']} — below minimum of 20"
            )


# ------------------------------------------------------------
# TEST CLASS 4 — PREDICTION ENDPOINT
# Verifies input validation, server-side BMI/WHtR derivation,
# and that all four models return predictions.
# ------------------------------------------------------------

class TestPredictionEndpoint:

    def test_valid_input_returns_200(self, client):
        assert client.post(
            "/api/exploratory/predict/custom", json=VALID_PAYLOAD
        ).status_code == 200

    def test_bmi_and_whtr_computed_server_side(self, client):
        # -----------------------------------------------------------
        # DERIVED METRIC VERIFICATION
        # height=175cm, weight=85kg  -> BMI  = 85 / 1.75^2 = 27.76
        # waist=95cm,  height=175cm  -> WHtR = 95 / 175    = 0.543
        # These are computed in the API — not passed by the caller.
        # -----------------------------------------------------------
        computed = client.post(
            "/api/exploratory/predict/custom", json=VALID_PAYLOAD
        ).json()["computed_metrics"]
        assert abs(computed["bmi"] - 27.76) < 0.1, (
            f"Expected BMI ~27.76, got {computed['bmi']}"
        )
        assert abs(computed["waist_to_height_ratio"] - 0.543) < 0.01, (
            f"Expected WHtR ~0.543, got {computed['waist_to_height_ratio']}"
        )

    def test_all_four_model_predictions_returned(self, client):
        predictions = client.post(
            "/api/exploratory/predict/custom", json=VALID_PAYLOAD
        ).json()["predictions"]
        assert set(predictions.keys()) == {"XGB", "LGBM", "RF", "LR"}

    def test_age_below_20_rejected_with_422(self, client):
        # Pydantic enforces age_years >= 20 (ge=20 field constraint)
        # Inputs below this must be rejected with HTTP 422 Unprocessable Entity
        payload = {**VALID_PAYLOAD, "age_years": 15}
        assert client.post(
            "/api/exploratory/predict/custom", json=payload
        ).status_code == 422

    def test_missing_required_field_rejected_with_422(self, client):
        # Omitting a required field must return HTTP 422
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "height_cm"}
        assert client.post(
            "/api/exploratory/predict/custom", json=payload
        ).status_code == 422
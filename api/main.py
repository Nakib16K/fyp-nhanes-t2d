import os
import glob
import logging
import pandas as pd
import numpy as np
import joblib
import shap
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from src.security import BodyLimitMiddleware, deployment_config
from src.privacy import allowed_origins
from src.shap_helpers import (
    positive_class_shap,
    positive_class_base,
    LOCAL_EXPLANATION_SCOPE,
    LOCAL_EXPLANATION_SCALE,
)
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, List, Literal
from src.artifacts import choose_latest_complete
from src.decisions import DecisionError, classify_probability, validate_model_thresholds

# -------------------------------------------------------------------
# CONFIGURATION & LOGGING
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ml_backend")

# main.py is in api/ folder, so go up one level to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports", "results")

ml_registry = {
    "models": {},
    "metrics": [],
    "latest_run_dir": None,
    "thresholds": {},  # Model-specific validation thresholds, verified from one manifest.
    "active_run_id": None,
}

# -------------------------------------------------------------------
# LIFESPAN MANAGER (Loads ML artifacts into memory on boot)
# -------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load only models and files from one verified post-evaluation run.

    Existing unit tests preseed ml_registry with mock models and metrics;
    preserve those explicit test doubles when there is no active run.
    Production starts with an empty registry and uses the manifest path.
    """
    logger.info("Initializing ML backend & checking run manifests...")
    preseeded_test_registry = (
        bool(ml_registry["models"])
        and bool(ml_registry["metrics"])
        and ml_registry["latest_run_dir"] is None
    )
    if preseeded_test_registry:
        logger.info("Using explicitly preseeded models and metrics (test fixture)")
    else:
        ml_registry.update({"models": {}, "metrics": [], "latest_run_dir": None, "thresholds": {}, "active_run_id": None})
        ready, rejected = choose_latest_complete(REPORTS_DIR)
        for msg in rejected:
            logger.warning("Skipping incomplete or inconsistent run: %s", msg)
        if ready is None:
            logger.error("No complete verified run found; aborting startup")
            raise RuntimeError(
                "Backend startup failed: no complete verified model run"
            )
        else:
            # Only load locally generated trusted pickle artifacts. The checksum
            # binds them to this run; it does not authenticate an untrusted file.
            try:
                loaded_models = {
                    name: joblib.load(path)
                    for name, path in ready["model_paths"].items()
                }
                loaded_metrics = pd.read_csv(ready["metrics_path"]).to_dict(orient="records")
                meta = ready["manifest"]
                ml_registry.update({
                    "models": loaded_models,
                    "metrics": loaded_metrics,
                    "latest_run_dir": str(ready["run_dir"]),
                    "thresholds": {name.upper(): meta["models"][name]["threshold"] for name in meta["models"]},
                    "active_run_id": meta["run_id"],
                })
                logger.info("Loaded %d models and matching metrics from %s", len(loaded_models), meta["run_id"])
            except Exception as e:
                logger.exception("Failed to load complete model set")
                ml_registry.update({
                    "models": {},
                    "metrics": [],
                    "latest_run_dir": None,
                    "thresholds": {},
                    "active_run_id": None,
                })
                raise RuntimeError(
                    "Backend startup failed: verified model set could not be loaded"
                ) from e

    try:
        yield
    finally:
        logger.info("Shutting down ML backend; clearing in-memory registry")
        ml_registry.update({"models": {}, "metrics": [], "latest_run_dir": None, "thresholds": {}, "active_run_id": None})

DEPLOYMENT_CONFIG = deployment_config()
app = FastAPI(
    lifespan=lifespan, title="T2D Exploratory API", version="1.0.0",
    docs_url="/docs" if DEPLOYMENT_CONFIG["docs_enabled"] else None,
    redoc_url="/redoc" if DEPLOYMENT_CONFIG["docs_enabled"] else None,
    openapi_url="/openapi.json" if DEPLOYMENT_CONFIG["docs_enabled"] else None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=DEPLOYMENT_CONFIG["hosts"], www_redirect=False)
app.add_middleware(BodyLimitMiddleware, max_body_bytes=8192)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(os.getenv("FYP_CORS_ORIGINS")),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "x-amz-content-sha256"],
)

@app.middleware("http")
async def prevent_sensitive_response_caching(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/") or request.url.path == "/health":
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
    return response

# -------------------------------------------------------------------
# STRICT DATA VALIDATION SCHEMA
# -------------------------------------------------------------------
class PatientInput(BaseModel):
    """
    Validate field types, supported categories and configured numeric bounds.
    These checks do not establish clinical plausibility or diagnostic validity.
    """
    model_config = ConfigDict(extra="forbid")
    gender_code: int = Field(..., ge=1, le=2, description="1=Male, 2=Female")
    age_years: int = Field(..., ge=20, le=120)
    ethnicity_code: Literal[1, 2, 3, 4, 6, 7]
    education_level: int = Field(..., ge=1, le=5)
    poverty_ratio: float = Field(..., ge=0.0, le=5.0)
    height_cm: float = Field(..., ge=100.0, le=250.0)
    weight_kg: float = Field(..., ge=30.0, le=300.0)
    waist_circumference: float = Field(..., ge=50.0, le=200.0)
    systolic_bp: int = Field(..., ge=70, le=250)
    diastolic_bp: int = Field(..., ge=40, le=150)
    pulse_60s: int = Field(..., ge=30, le=200)
    history_high_bp: int = Field(..., ge=1, le=2, description="1=Yes, 2=No")
    smoked_100_cigs: int = Field(..., ge=1, le=2)
    family_history_diabetes: int = Field(..., ge=1, le=2)
    vigorous_activity: int = Field(..., ge=1, le=2)

# -------------------------------------------------------------------
# CORE API ENDPOINTS
# -------------------------------------------------------------------


# ---------------------------------------------------------------------------
# SHAP LABEL MAPPING HELPER
# ---------------------------------------------------------------------------
def _build_label_map(run_dir: str) -> dict:
    """Build complete readable name map for all features (numerical + categorical)."""
    import csv as _csv, json as _json

    NUMERICAL_NAMES = {
        "age_years":              "Age (years)",
        "bmi":                    "BMI",
        "waist_circumference":    "Waist Circumference (cm)",
        "waist_to_height_ratio":  "Waist-to-Height Ratio",
        "systolic_bp":            "Systolic BP (mmHg)",
        "diastolic_bp":           "Diastolic BP (mmHg)",
        "pulse_60s":              "Resting Pulse (bpm)",
        "poverty_ratio":          "Poverty Ratio",
        "education_level":        "Education Level",
    }
    CATEGORICAL_OVERRIDES = {
        "history_high_bp":           "High BP History",
        "smoked_100_cigs":           "Smoked 100+ Cigarettes",
        "family_history_diabetes":   "Family Diabetes History",
        "vigorous_activity":         "Vigorous Activity",
        "gender_code":               "Gender",
        "ethnicity_code":            "Ethnicity",
    }

    label_map = dict(NUMERICAL_NAMES)
    # Trusted model-source codebook; no respondent-level data needed.
    from src.data_dictionary import CODE_DESCRIPTIONS
    for col in (
        "ethnicity_code",
        "gender_code",
        "history_high_bp",
        "smoked_100_cigs",
        "family_history_diabetes",
        "vigorous_activity",
    ):
        for code, meaning in CODE_DESCRIPTIONS[col].items():
            if col == "ethnicity_code" and code not in (1, 2, 3, 4, 6, 7):
                continue
            if col != "ethnicity_code" and col != "gender_code" and code not in (1, 2):
                continue
            label = CATEGORICAL_OVERRIDES[col] + ": " + meaning
            label_map[f"{col}_{code}"] = label
            label_map[f"{col}_{float(code)}"] = label
    if not run_dir:
        return label_map
    dd_path = os.path.join(run_dir, "data_dictionary_master_dataset.csv")
    if not os.path.exists(dd_path):
        return label_map
    try:
        with open(dd_path) as f:
            reader = _csv.DictReader(f)
            for row in reader:
                col = row["column"]
                cats_raw = row.get("categories_json", "").strip()
                if cats_raw:
                    cats = _json.loads(cats_raw)
                    for cat in cats:
                        code = cat["code"]
                        meaning = cat.get("meaning", "")
                        if meaning:
                            prefix = CATEGORICAL_OVERRIDES.get(
                                col, col.replace("_code", "").replace("_", " ").title()
                            )
                            readable = f"{prefix}: {meaning}"
                            label_map[f"{col}_{float(code)}"] = readable
                            if float(code) == int(float(code)):
                                label_map[f"{col}_{int(float(code))}"] = readable
    except Exception as e:
        logger.warning(f"Could not build SHAP label map: {e}")
    return label_map

@app.get("/health")
async def health_check():
    return {"status": "online", "models_loaded": list(ml_registry["models"].keys())}

@app.get("/api/models/metrics")
async def get_all_models_metrics():
    if not ml_registry["metrics"]:
        raise HTTPException(status_code=404, detail="Metrics not found.")

    # Mapping dictionary: CSV Header -> React TypeScript Key
    key_mapping = {
        "AUC": "auc_roc",
        "Precision": "precision",
        "Recall_Sensitivity": "recall",
        "F1_Score": "f1",
        "Accuracy": "accuracy"
    }

    normalized = []
    for record in ml_registry["metrics"]:
        row = dict(record)

        # 1. Normalize the model name
        if "model_name" not in row:
            for candidate in ("Model", "model", "Name", "name", "MODEL", "MODEL_NAME"):
                if candidate in row:
                    row["model_name"] = row.pop(candidate)
                    break

        # 2. Map the metric keys to match React's ModelMetrics interface
        mapped_row = {"model_name": row.get("model_name", "Unknown")}

        for csv_key, react_key in key_mapping.items():
            if csv_key in row:
                mapped_row[react_key] = float(row[csv_key])
            else:
                mapped_row[react_key] = 0.0 # Fallback safety

        # Handle sensitivity separately since it shares the Recall column in CSV
        if "Recall_Sensitivity" in row:
             mapped_row["sensitivity"] = float(row["Recall_Sensitivity"])

        normalized.append(mapped_row)

    return normalized

@app.get("/api/models/{model_name}/shap/global")
async def get_global_shap_image(model_name: str):
    """Serves the static Global SHAP Summary plot generated during training."""
    model_name = model_name.lower()
    if model_name not in {"lr", "rf", "lgbm", "xgb"}:
        raise HTTPException(status_code=404, detail="Unknown model.")
    run_dir = ml_registry.get("latest_run_dir")

    if not run_dir:
        raise HTTPException(status_code=404, detail="No training run found.")

    image_path = os.path.join(run_dir, f"{model_name}_shap_summary.png")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Global SHAP image for {model_name} not found.")

    return FileResponse(
        image_path,
        media_type="image/png",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"}
    )

@app.get("/api/exploratory/presets")
async def get_presets() -> Dict[str, Any]:
    """Returns synthetic illustrative presets for the Exploratory Dashboard."""
    return {
        "healthy": {
            "age_years": 28, "gender_code": 2, "ethnicity_code": 3,
            "education_level": 5, "poverty_ratio": 3.5,
            "height_cm": 165.0, "weight_kg": 62.0, "waist_circumference": 75.0,
            "systolic_bp": 110, "diastolic_bp": 70, "pulse_60s": 65,
            "smoked_100_cigs": 2,
            "vigorous_activity": 1, "family_history_diabetes": 2,
            "history_high_bp": 2
        },
        "elevated_risk": {
            "age_years": 45, "gender_code": 1, "ethnicity_code": 1,
            "education_level": 3, "poverty_ratio": 2.0,
            "height_cm": 175.0, "weight_kg": 85.0, "waist_circumference": 95.0,
            "systolic_bp": 128, "diastolic_bp": 82, "pulse_60s": 72,
            "smoked_100_cigs": 1,
            "vigorous_activity": 2, "family_history_diabetes": 1,
            "history_high_bp": 1
        },
        "high_risk": {
            "age_years": 62, "gender_code": 1, "ethnicity_code": 4,
            "education_level": 2, "poverty_ratio": 1.2,
            "height_cm": 170.0, "weight_kg": 105.0, "waist_circumference": 115.0,
            "systolic_bp": 145, "diastolic_bp": 90, "pulse_60s": 85,
            "smoked_100_cigs": 1,
            "vigorous_activity": 2, "family_history_diabetes": 1,
            "history_high_bp": 1
        }
    }


@app.get("/api/models/{model_name}/interpretation")
async def get_model_interpretation(model_name: str):
    """Serves the plain-text interpretation file for a given model."""
    model_name = model_name.lower()
    if model_name not in {"lr", "rf", "lgbm", "xgb"}:
        raise HTTPException(status_code=404, detail="Unknown model.")
    run_dir = ml_registry.get("latest_run_dir")
    if not run_dir:
        raise HTTPException(status_code=404, detail="No training run found.")
    interp_path = os.path.join(run_dir, f"{model_name}_interpretation.txt")
    if not os.path.exists(interp_path):
        raise HTTPException(status_code=404, detail=f"Interpretation for {model_name} not found.")
    from fastapi.responses import PlainTextResponse
    with open(interp_path) as f:
        return PlainTextResponse(f.read())

@app.post("/api/exploratory/predict/custom")
async def predict_custom(input_data: PatientInput) -> Dict[str, Any]:
    """Computes derived metrics and returns predictions from all models."""
    if not ml_registry["models"]:
        raise HTTPException(status_code=503, detail="Models offline.")
    # Fail closed when model/threshold metadata is incomplete. No 0.5 fallback.
    try:
        thresholds = validate_model_thresholds(ml_registry["models"], ml_registry.get("thresholds"))
    except DecisionError as error:
        logger.error("Prediction blocked: %s", error)
        raise HTTPException(status_code=503, detail="Verified model thresholds unavailable.") from error

    height_m = input_data.height_cm / 100.0
    computed_bmi = input_data.weight_kg / (height_m ** 2)
    computed_wth_ratio = input_data.waist_circumference / input_data.height_cm

    ml_input_dict = input_data.model_dump(exclude={'height_cm', 'weight_kg'})
    ml_input_dict.update({
        "bmi": computed_bmi,
        "waist_to_height_ratio": computed_wth_ratio
    })

    df_input = pd.DataFrame([ml_input_dict])
    predictions = {}

    for model_name, pipeline in ml_registry["models"].items():
        try:
            prob = float(pipeline.predict_proba(df_input)[0][1])
            predictions[model_name] = {
                "probability_score": round(prob, 4),
                "risk_percentage": f"{round(prob * 100, 1)}%",
                "prediction_class": classify_probability(prob, thresholds[model_name]),
                "decision_threshold": round(thresholds[model_name], 6),
                "threshold_source": "validation",
                # Compute from unrounded probability; never infer status from
                # the 1-decimal percentage shown to the user.
                "above_threshold": bool(prob >= thresholds[model_name]),
                "decision_margin_pp": round((prob - thresholds[model_name]) * 100, 4)
            }
        except Exception as error:
            # No partial predictions and no user inputs or exception payloads in logs.
            logger.warning("Prediction unavailable; model=%s error_type=%s", model_name, type(error).__name__)
            raise HTTPException(status_code=503, detail="Prediction unavailable.") from None

    return {
        "status": "success",
        "computed_metrics": {"bmi": round(computed_bmi, 2), "waist_to_height_ratio": round(computed_wth_ratio, 3)},
        "predictions": predictions
    }

@app.post("/api/exploratory/predict/custom/shap/{model_name}")
async def get_local_shap(model_name: str, input_data: PatientInput) -> Dict[str, Any]:
    """
    Dynamically calculates Local SHAP values for a single prediction.
    Extracts the uncalibrated base estimator from the CalibratedClassifierCV
    ensemble to achieve compatibility with shap.TreeExplainer.
    """
    model_name = model_name.upper()
    if model_name not in ml_registry["models"]:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not loaded.")
    if model_name == "LR":
        raise HTTPException(status_code=400, detail="Local SHAP is only supported for tree-based models (XGB, LGBM, RF).")

    # 1. Data Preparation
    height_m = input_data.height_cm / 100.0
    ml_input_dict = input_data.model_dump(exclude={'height_cm', 'weight_kg'})
    ml_input_dict.update({
        "bmi": input_data.weight_kg / (height_m ** 2),
        "waist_to_height_ratio": input_data.waist_circumference / input_data.height_cm
    })
    df_input = pd.DataFrame([ml_input_dict])

    try:
        calibrated_ensemble = ml_registry["models"][model_name]

        # Extract base pipeline from the calibrator
        raw_pipeline = calibrated_ensemble.calibrated_classifiers_[0].estimator
        preprocessor = raw_pipeline.named_steps['preprocessor']
        base_model = raw_pipeline.named_steps['model']

        # Transform the single record
        X_transformed = preprocessor.transform(df_input)

        # Extract feature names
        if hasattr(preprocessor, 'feature_names_out'):
            raw_names = list(preprocessor.feature_names_out)
        else:
            raw_names = list(df_input.columns)

        # Apply readable labels for DISPLAY (not for computation)
        run_dir = ml_registry.get("latest_run_dir", "")
        label_map = _build_label_map(run_dir)
        # Map from encoded names to readable names (for frontend display only)
        display_names = [label_map.get(n, n) for n in raw_names]

        # IMPORTANT: Compute SHAP on the raw encoded DataFrame so XGBoost
        # feature names match what it was trained with. Applying readable
        # names before this causes a silent name-mismatch and XGBoost
        # returns background/default SHAP values instead of per-sample values.
        explainer = shap.TreeExplainer(base_model)
        shap_values = explainer.shap_values(X_transformed)

        # Handle different output structures for RF/XGB/LGBM
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        shap_list = np.round(positive_class_shap(shap_values, len(display_names)), 4).tolist()

        # Sort features by absolute impact magnitude for frontend rendering
        # Include the state of each one-hot indicator alongside its contribution.
        # An absent indicator can still have a nonzero SHAP value.
        indicator_prefixes = (
            "gender_code_", "ethnicity_code_", "history_high_bp_",
            "smoked_100_cigs_", "family_history_diabetes_",
            "vigorous_activity_",
        )
        impact_data = []
        for raw_name, readable_name, contribution in zip(raw_names, display_names, shap_list):
            entry = {"feature": readable_name, "impact": contribution}
            if str(raw_name).startswith(indicator_prefixes):
                encoded_value = float(X_transformed.iloc[0][raw_name])
                if encoded_value in (0.0, 1.0):
                    entry["indicator_state"] = "present" if encoded_value == 1.0 else "absent"
            impact_data.append(entry)
        impact_data = sorted(impact_data, key=lambda x: abs(x["impact"]), reverse=True)

        return {
            "model": model_name,
            "shap_values_sorted": impact_data,
            "base_value": positive_class_base(explainer.expected_value),
            "explanation_scope": LOCAL_EXPLANATION_SCOPE,
            "explanation_scale": LOCAL_EXPLANATION_SCALE,
            "explains_calibrated_probability": False
        }

    except Exception as error:
        # Never log the patient input or exception payload in a public API.
        logger.warning("Local explanation failed; model=%s error_type=%s", model_name, type(error).__name__)
        raise HTTPException(status_code=500, detail="Feature explanation unavailable.") from None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

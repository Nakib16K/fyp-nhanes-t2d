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
from pydantic import BaseModel, Field
from typing import Dict, Any, List

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
    "latest_run_dir": None
}

# -------------------------------------------------------------------
# LIFESPAN MANAGER (Loads ML artifacts into memory on boot)
# -------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing ML Backend & Loading Artifacts...")

    # 1. Load Trained Pipelines
    model_files = glob.glob(os.path.join(MODELS_DIR, "*_pipeline.pkl"))
    if not model_files:
        logger.warning(f"No .pkl files found in models directory: {MODELS_DIR}")

    for file_path in model_files:
        model_name = os.path.basename(file_path).split('_')[0].upper()
        try:
            ml_registry["models"][model_name] = joblib.load(file_path)
            logger.info(f"Successfully loaded model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load {model_name}: {e}")

    # 2. Load Metrics & Locate Global SHAP Images
    try:
        run_folders = sorted(glob.glob(os.path.join(REPORTS_DIR, "run_*")), reverse=True)
        if run_folders:
            latest_run = run_folders[0]
            ml_registry["latest_run_dir"] = latest_run

            metrics_path = os.path.join(latest_run, "summary_metrics.csv")
            if os.path.exists(metrics_path):
                df_metrics = pd.read_csv(metrics_path)
                ml_registry["metrics"] = df_metrics.to_dict(orient='records')
                logger.info(f"Loaded Metrics from: {os.path.basename(latest_run)}")
    except Exception as e:
        logger.error(f"Could not load metrics: {e}")

    yield

    logger.info("Shutting down ML Backend and clearing memory...")
    ml_registry["models"].clear()

app = FastAPI(lifespan=lifespan, title="T2D Exploratory API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# STRICT DATA VALIDATION SCHEMA
# -------------------------------------------------------------------
class PatientInput(BaseModel):
    """
    Strict boundary validation ensures the ML pipeline never receives
    impossible clinical values, preventing mathematical errors during imputation.
    """
    gender_code: int = Field(..., ge=1, le=2, description="1=Male, 2=Female")
    age_years: int = Field(..., ge=20, le=120)
    ethnicity_code: int = Field(..., ge=1, le=7)
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
    alcohol_frequency: int = Field(..., ge=0, le=365)

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
        "alcohol_frequency":      "Alcohol Frequency (days/year)",
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
    """Returns hardcoded clinical presets for the Exploratory Dashboard."""
    return {
        "healthy": {
            "age_years": 28, "gender_code": 2, "ethnicity_code": 3,
            "education_level": 5, "poverty_ratio": 3.5,
            "height_cm": 165.0, "weight_kg": 62.0, "waist_circumference": 75.0,
            "systolic_bp": 110, "diastolic_bp": 70, "pulse_60s": 65,
            "smoked_100_cigs": 2, "alcohol_frequency": 50,
            "vigorous_activity": 1, "family_history_diabetes": 2,
            "history_high_bp": 2
        },
        "elevated_risk": {
            "age_years": 45, "gender_code": 1, "ethnicity_code": 1,
            "education_level": 3, "poverty_ratio": 2.0,
            "height_cm": 175.0, "weight_kg": 85.0, "waist_circumference": 95.0,
            "systolic_bp": 128, "diastolic_bp": 82, "pulse_60s": 72,
            "smoked_100_cigs": 1, "alcohol_frequency": 150,
            "vigorous_activity": 2, "family_history_diabetes": 1,
            "history_high_bp": 1
        },
        "high_risk": {
            "age_years": 62, "gender_code": 1, "ethnicity_code": 4,
            "education_level": 2, "poverty_ratio": 1.2,
            "height_cm": 170.0, "weight_kg": 105.0, "waist_circumference": 115.0,
            "systolic_bp": 145, "diastolic_bp": 90, "pulse_60s": 85,
            "smoked_100_cigs": 1, "alcohol_frequency": 0,
            "vigorous_activity": 2, "family_history_diabetes": 1,
            "history_high_bp": 1
        }
    }


@app.get("/api/models/{model_name}/interpretation")
async def get_model_interpretation(model_name: str):
    """Serves the plain-text interpretation file for a given model."""
    model_name = model_name.lower()
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
                "prediction_class": "High Risk" if prob >= 0.5 else "Low Risk"
            }
        except Exception as e:
            logger.error(f"Inference error on {model_name}: {e}")
            predictions[model_name] = {"error": "Inference failed"}

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

        shap_list = np.round(shap_values[0], 4).tolist()

        # Sort features by absolute impact magnitude for frontend rendering
        impact_data = [{"feature": f, "impact": v} for f, v in zip(display_names, shap_list)]
        impact_data = sorted(impact_data, key=lambda x: abs(x["impact"]), reverse=True)

        return {
            "model": model_name,
            "shap_values_sorted": impact_data,
            "base_value": float(explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value)
        }

    except Exception as e:
        logger.error(f"Local SHAP generation failed for {model_name}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to compute SHAP explanation.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
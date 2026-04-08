import os
import json
import numpy as np
import pandas as pd

from src.config import (
    ID_COLS,
    TARGET_SOURCE_COLS,
    FEATURE_MAPPING,
    TARGET_COL,
    CATEGORICAL_VARS,
    NUMERICAL_VARS,
)

# =============================================================================
# 1. VARIABLE LABELS (Human-Readable Definitions)
# =============================================================================
# Sourced from CDC NHANES Documentation (2013-2018 cycles)
VARIABLE_LABELS = {
    # --- Identifiers ---
    "respondent_id": "Unique Subject Identifier (SEQN)",
    "interview_weight": "Full Sample 2-Year Interview Weight (WTINT2YR)",
    "survey_cycle": "NHANES Data Collection Cycle (e.g., 2013-2014)",

    # --- Targets / Ground Truth Sources ---
    "t2d_label": "Computed Type 2 Diabetes Label (0=Healthy, 1=Diabetic)",
    "hba1c_percent": "Glycohemoglobin (HbA1c) percentage (%)",
    "doctor_told_diabetes": "Doctor ever told you that you had diabetes?",
    "taking_insulin": "Taking insulin now?",
    "taking_diabetes_pills": "Taking diabetic pills to lower blood sugar?",

    # --- Demographics ---
    "gender_code": "Gender of the participant",
    "age_years": "Age in years at screening",
    "ethnicity_code": "Race/Hispanic origin (re-coded)",
    "education_level": "Highest grade or level of school completed",
    "poverty_ratio": "Ratio of family income to poverty guidelines (0.0 to 5.0)",

    # --- Anthropometry (Body Measures) ---
    "bmi": "Body Mass Index (kg/m**2)",
    "waist_circumference": "Waist Circumference (cm)",
    "weight_kg": "Weight (kg)",
    "height_cm": "Standing Height (cm)",
    "leg_length_upper_cm": "Upper Leg Length (cm)",
    "arm_length_upper_cm": "Upper Arm Length (cm)",
    "arm_circumference_cm": "Arm Circumference (cm)",
    "highest_weight_ever_kg": "Self-reported highest weight ever (excluding pregnancy)",

    # --- Vitals / Blood Pressure ---
    "systolic_bp": "Systolic Blood Pressure (mmHg) - 1st reading",
    "diastolic_bp": "Diastolic Blood Pressure (mmHg) - 1st reading",
    "pulse_60s": "60-second Pulse (beats/min)",
    "history_high_bp": "Doctor ever told you that you had high blood pressure?",

    # --- Lifestyle & History ---
    "smoked_100_cigs": "Smoked at least 100 cigarettes in entire life?",
    "family_history_diabetes": "Close biological relatives had diabetes?",
    "vigorous_activity": "Does vigorous-intensity work activity?",
    "alcohol_frequency": "Frequency of alcohol consumption (past 12 months)",

    # --- Dietary Intake (Day 1) ---
    "diet_energy_kcal": "Energy (kcal) - Total nutrient intake",
    "diet_sodium_mg": "Sodium (mg) - Total nutrient intake",
    "diet_carbs_gm": "Carbohydrate (gm) - Total nutrient intake",
    "diet_caffeine_mg": "Caffeine (mg) - Total nutrient intake",
}

# =============================================================================
# 2. CODE DESCRIPTIONS (Categorical Mappings)
# =============================================================================
CODE_DESCRIPTIONS = {
    "gender_code": {
        1: "Male",
        2: "Female",
    },
    "ethnicity_code": {
        1: "Mexican American",
        2: "Other Hispanic",
        3: "Non-Hispanic White",
        4: "Non-Hispanic Black",
        6: "Non-Hispanic Asian",
        7: "Other Race (including Multi-Racial)",
    },
    "education_level": {
        1: "Less than 9th grade",
        2: "9-11th grade (Includes 12th grade with no diploma)",
        3: "High school graduate/GED or equivalent",
        4: "Some college or AA degree",
        5: "College graduate or above",
        7: "Refused",
        9: "Don't know",
    },
    "alcohol_frequency": {
        0: "Never in the last year",
        999: "Don't know",
        777: "Refused"
        # Note: Values 1-365 represent actual number of days.
        # This mapping covers the special codes.
    },
    # --- Binary Yes/No Variables (Standard NHANES Coding) ---
    "history_high_bp": {1: "Yes", 2: "No", 7: "Refused", 9: "Don't know"},
    "smoked_100_cigs": {1: "Yes", 2: "No", 7: "Refused", 9: "Don't know"},
    "family_history_diabetes": {1: "Yes", 2: "No", 7: "Refused", 9: "Don't know"},
    "vigorous_activity": {1: "Yes", 2: "No", 7: "Refused", 9: "Don't know"},
    "doctor_told_diabetes": {1: "Yes", 2: "No", 7: "Refused", 9: "Don't know"},
    "taking_insulin": {1: "Yes", 2: "No", 7: "Refused", 9: "Don't know"},
    "taking_diabetes_pills": {1: "Yes", 2: "No", 7: "Refused", 9: "Don't know"},
    "t2d_label": {0: "Healthy / Non-Diabetic", 1: "Diabetic (Type 2)"}
}

def _invert_mapping(d: dict) -> dict:
    # Helper to map renamed_col back to original NHANES_code
    return {v: k for k, v in d.items()}

def generate_data_dictionary(master_csv_path: str, output_csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(master_csv_path)

    inv_id = _invert_mapping(ID_COLS)
    inv_target = _invert_mapping(TARGET_SOURCE_COLS)
    inv_feat = _invert_mapping(FEATURE_MAPPING)

    rows = []
    for col in df.columns:
        # 1. Determine Role & Original NHANES Code
        if col in inv_id:
            nhanes_code = inv_id[col]
            role = "id"
        elif col in inv_target:
            nhanes_code = inv_target[col]
            role = "label_source"
        elif col in inv_feat:
            nhanes_code = inv_feat[col]
            role = "feature"
        elif col == TARGET_COL:
            nhanes_code = "Computed"
            role = "label"
        elif col == "survey_cycle":
            nhanes_code = "Metadata"
            role = "metadata"
        else:
            nhanes_code = ""
            role = "derived_or_other"

        # 2. Get Statistics
        series = df[col]
        missing_count = int(series.isna().sum())
        missing_pct = float(series.isna().mean() * 100)

        # 3. Determine Variable Type
        is_cat = (col in CATEGORICAL_VARS) or (col == TARGET_COL)
        is_num = (col in NUMERICAL_VARS) or (pd.api.types.is_numeric_dtype(series) and not is_cat)

        min_val = ""
        max_val = ""
        categories = ""

        # 4. Numerical Stats
        if is_num:
            s = pd.to_numeric(series, errors="coerce")
            if s.notna().any():
                min_val = float(np.nanmin(s.values))
                max_val = float(np.nanmax(s.values))

        # 5. Categorical Mappings (JSON)
        if is_cat:
            # Get unique values present in the data
            uniq = series.dropna().unique().tolist()
            cleaned_uniq = []
            for v in uniq:
                try:
                    # Convert floats like 1.0 to int 1 for cleaner lookup
                    iv = int(v)
                    if float(v) == float(iv):
                        cleaned_uniq.append(iv)
                    else:
                        cleaned_uniq.append(v)
                except Exception:
                    cleaned_uniq.append(v)

            cleaned_uniq = sorted(cleaned_uniq, key=lambda x: (isinstance(x, str), x))

            mapping = CODE_DESCRIPTIONS.get(col, {})
            cat_rows = []
            for v in cleaned_uniq:
                # If a specific mapping exists, use it. 
                # Otherwise, for values like 1-365 in alcohol, leave blank or generic.
                meaning = mapping.get(v, "")
                freq = int((series == v).sum())
                cat_rows.append({"code": v, "meaning": meaning, "count": freq})
            categories = json.dumps(cat_rows, ensure_ascii=False)

        # 6. Append Row
        rows.append({
            "column": col,
            "description": VARIABLE_LABELS.get(col, "Description not found"),
            "nhanes_code": nhanes_code,
            "role": role,
            "type": "categorical" if is_cat else ("numerical" if is_num else "other"),
            "missing_pct": round(missing_pct, 2),
            "min": min_val,
            "max": max_val,
            "categories_json": categories,
        })

    # Sort by Role then Column name for readability
    out = pd.DataFrame(rows).sort_values(by=["role", "column"]).reset_index(drop=True)
    
    # Save
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    out.to_csv(output_csv_path, index=False)
    return out

if __name__ == "__main__":
    from src.config import PROCESSED_DATA_PATH, REPORTS_DIR

    master = os.path.join(PROCESSED_DATA_PATH, "master_dataset.csv")
    out_csv = os.path.join(REPORTS_DIR, "data_dictionary", "data_dictionary_master_dataset.csv")
    
    if os.path.exists(master):
        generate_data_dictionary(master, out_csv)
        print(f"Dictionary generated: {out_csv}")
    else:
        print(f"Master dataset not found at {master}. Run pipeline first.")
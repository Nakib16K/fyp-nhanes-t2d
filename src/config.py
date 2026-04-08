import os

# ============================================================
# 1. PATH CONFIGURATION
# ============================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DATA_PATH = os.path.join(DATA_DIR, "raw")
PROCESSED_DATA_PATH = os.path.join(DATA_DIR, "processed")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

# Ensure all necessary directories exist for artifact generation
for d in [RAW_DATA_PATH, PROCESSED_DATA_PATH, FIGURES_DIR, MODELS_DIR]:
    os.makedirs(d, exist_ok=True)

# ============================================================
# 2. NHANES FILE MANIFEST
# ============================================================
BASE_URLS = {
    "2013-2014": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles",
    "2015-2016": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles",
    "2017-2018": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles",
}

NHANES_FILE_MANIFEST = {
    "2013-2014": {
        "DEMO": "DEMO_H.xpt", "BMX": "BMX_H.xpt", "DIQ": "DIQ_H.xpt",
        "SMQ": "SMQ_H.xpt",   "GHB": "GHB_H.xpt", "BPQ": "BPQ_H.xpt",
        "MCQ": "MCQ_H.xpt",   "PAQ": "PAQ_H.xpt", "ALQ": "ALQ_H.xpt",
        "BPX": "BPX_H.xpt",   "WHQ": "WHQ_H.xpt", "DR1TOT": "DR1TOT_H.xpt"
    },
    "2015-2016": {
        "DEMO": "DEMO_I.xpt", "BMX": "BMX_I.xpt", "DIQ": "DIQ_I.xpt",
        "SMQ": "SMQ_I.xpt",   "GHB": "GHB_I.xpt", "BPQ": "BPQ_I.xpt",
        "MCQ": "MCQ_I.xpt",   "PAQ": "PAQ_I.xpt", "ALQ": "ALQ_I.xpt",
        "BPX": "BPX_I.xpt",   "WHQ": "WHQ_I.xpt", "DR1TOT": "DR1TOT_I.xpt"
    },
    "2017-2018": {
        "DEMO": "DEMO_J.xpt", "BMX": "BMX_J.xpt", "DIQ": "DIQ_J.xpt",
        "SMQ": "SMQ_J.xpt",   "GHB": "GHB_J.xpt", "BPQ": "BPQ_J.xpt",
        "MCQ": "MCQ_J.xpt",   "PAQ": "PAQ_J.xpt", "ALQ": "ALQ_J.xpt",
        "BPX": "BPX_J.xpt",   "WHQ": "WHQ_J.xpt", "DR1TOT": "DR1TOT_J.xpt"
    },
}

# ============================================================
# 3. VARIABLE MAPPING & DOMAIN-DRIVEN FEATURE SELECTION
# ============================================================
ID_COLS = {'SEQN': 'respondent_id', 'WTINT2YR': 'interview_weight'}

TARGET_SOURCE_COLS = {
    'LBXGH': 'hba1c_percent',
    'DIQ010': 'doctor_told_diabetes',
    'DIQ050': 'taking_insulin',
    'DIQ070': 'taking_diabetes_pills'  
}

# Feature Mapping retains all raw columns for initial data ingestion.
# The actual filtering happens in the NOMINAL/ORDINAL/NUMERICAL lists below.
FEATURE_MAPPING = {
    'RIAGENDR': 'gender_code',
    'RIDAGEYR': 'age_years',
    'RIDRETH3': 'ethnicity_code',
    'DMDEDUC2': 'education_level',
    'INDFMPIR': 'poverty_ratio',
    'BMXBMI': 'bmi',
    'BMXWAIST': 'waist_circumference',
    'BMXWT': 'weight_kg',
    'BMXHT': 'height_cm',
    'BMXLEG': 'leg_length_upper_cm',
    'BMXARML': 'arm_length_upper_cm',
    'BMXARMC': 'arm_circumference_cm',
    'BPXSY1': 'systolic_bp',
    'BPXDI1': 'diastolic_bp',
    'BPXPLS': 'pulse_60s',
    'BPQ020': 'history_high_bp',
    'SMQ020': 'smoked_100_cigs',
    'MCQ300C': 'family_history_diabetes',
    'PAQ650': 'vigorous_activity',
    'ALQ120Q': 'alcohol_frequency',
    'WHD140': 'highest_weight_ever_kg',
    'DR1TKCAL': 'diet_energy_kcal',
    'DR1TSODI': 'diet_sodium_mg',
    'DR1TCARB': 'diet_carbs_gm',
    'DR1TCAFF': 'diet_caffeine_mg'
}

ALL_RAW_COLS = (
    list(ID_COLS.keys()) +
    list(TARGET_SOURCE_COLS.keys()) +
    list(FEATURE_MAPPING.keys())
)

TARGET_COL = 't2d_label'

# -------------------------------------------------------------------
# DOMAIN-DRIVEN PIPELINE FILTERS
# Only variables in the following three lists will be passed to the models.
# -------------------------------------------------------------------

NOMINAL_VARS = [
    'gender_code', 
    'ethnicity_code', 
    'history_high_bp', 
    'smoked_100_cigs', 
    'family_history_diabetes', 
    'vigorous_activity'
]

ORDINAL_VARS = [
    'education_level', 
    'alcohol_frequency'
]

NUMERICAL_VARS = [
    'age_years', 
    'poverty_ratio', 
    'bmi', 
    'waist_circumference', 
    'waist_to_height_ratio', 
    'systolic_bp', 
    'diastolic_bp',
    'pulse_60s',
    
    # ----------------------------------------------------------------
    # EXCLUDED FEATURES: MULTICOLLINEARITY & NOISE REDUCTION
    # ----------------------------------------------------------------
    # The following features are intentionally commented out based on EDA 
    # and clinical literature review. Including them alongside BMI and 
    # Waist Circumference introduces severe multicollinearity, artificially 
    # skewing model weights (especially for Logistic Regression).
    
    # 'weight_kg',                 # Redundant: Captured by BMI
    # 'height_cm',                 # Redundant: Captured by BMI
    # 'arm_circumference_cm',      # Redundant: Correlates heavily with overall adiposity/BMI
    # 'arm_length_upper_cm',       # Low correlation (0.04) with target; introduces noise
    # 'leg_length_upper_cm',       # Low clinical relevance to T2D compared to visceral fat
    # 'highest_weight_ever_kg',    # Prone to self-reporting bias and redundant with current BMI
    
    # Dietary variables excluded due to self-reporting bias in 24-hour dietary recall (not missingness)
    # 'diet_energy_kcal', 
    # 'diet_sodium_mg', 
    # 'diet_carbs_gm', 
    # 'diet_caffeine_mg'
]

CATEGORICAL_VARS = NOMINAL_VARS + ORDINAL_VARS

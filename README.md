# Predicting Diabetes using Anthropometric, Lifestyle and Demographic Data

BSc Computer Science Final Year Project (CS3072/CS3605)
Brunel University London   
Student ID: 2220769

## Overview

A comparative machine learning framework that predicts Type 2 Diabetes risk using strictly non-invasive variables from the National Health and Nutrition Examination Survey (NHANES, 2013 to 2018). Four classifiers (Logistic Regression, Random Forest, XGBoost, LightGBM) are trained under three class-balancing strategies (SMOTE, random undersampling, class-weight adjustment) with Bayesian hyperparameter optimisation. The system includes SHAP-based explainability, a demographic fairness audit, and an interactive web application built with React and FastAPI.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| ML Libraries | scikit-learn, XGBoost, LightGBM, imbalanced-learn |
| Optimisation | Optuna (Bayesian, 50 trials per model) |
| Explainability | SHAP (TreeExplainer, LinearExplainer) |
| Backend | FastAPI, Uvicorn |
| Frontend | React, TypeScript, Vite |
| Testing | pytest |
| Data Source | CDC NHANES (2013-2014, 2015-2016, 2017-2018) |

## Project Structure

```
root/
├── main.py                         # Pipeline entry point
├── conftest.py                     # Pytest path configuration
├── requirements.txt                # Python dependencies
├── api/
│   ├── __init__.py
│   └── main.py                     # FastAPI application
├── src/
│   ├── __init__.py
│   ├── config.py                   # Feature lists, paths, NHANES mappings
│   ├── data_loader.py              # NHANES data acquisition and merging
│   ├── features.py                 # NHANESPreprocessor (fit/transform)
│   ├── models.py                   # ModelFactory (Factory Design Pattern)
│   └── pipeline.py                 # DiabetesPipeline orchestrator
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── App.tsx                  # Root application component
│       ├── components/
│       │   ├── ModelComparison/
│       │   │   ├── ModelCard.tsx     # Per-model metric card
│       │   │   └── ...              # Additional comparison components
│       │   └── Exploratory/
│       │       ├── ExploratoryMode.tsx
│       │       ├── CustomPredictionForm.tsx
│       │       ├── PresetCard.tsx
│       │       ├── SHAPVisualization.tsx
│       │       └── ...              # Additional exploratory components
│       ├── hooks/
│       │   └── usePresets.ts        # Preset state management
│       │   └── ...        
│       └── utils/
│       │   └── api.ts               # API client utilities
│       └── ...              
├── tests/
│   ├── __init__.py
│   ├── test_pipeline.py            # 18 ML pipeline unit tests
│   └── test_api.py                 # 13 FastAPI integration tests
├── data/
│   ├── raw/                        # Downloaded NHANES .xpt files
│   │   └── ...                     # Multiple .xpt files per cycle
│   └── processed/
│       └── master_dataset.csv      # Merged and labelled dataset
├── models/
│   ├── best_params_*.json          # Cached hyperparameters
│   └── ...                         # Serialised .pkl model files
├── reports/
│   └── run_YYYY-MM-DD_HH-MM-SS_<mode>/
│       ├── summary_metrics.csv
│       ├── algorithmic_fairness_report.csv
│       ├── *_confusion_matrix.png
│       ├── *_roc_curve.png
│       ├── *_shap_summary.png
│       ├── *_report.csv
│       ├── *_interpretation.txt
│       └── ...                     # Additional run outputs
├── notebooks/
│   └── EDA_Notebook.ipynb          # Exploratory Data Analysis
└── README.md
```

## Setup and Installation

### Prerequisites

- Python 3.12+
- Node.js 18+ and npm
- Git

### 1. Clone the Repository

```bash
git clone <repository-url>
cd fyp-nhanes-t2d
```

### 2. Create Virtual Environment and Install Dependencies

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## Running the Project

### Training the ML Pipeline

```bash
# Train all four models with class-weight balancing (recommended)
python main.py --balancing_mode class_weight

# Train with SMOTE
python main.py --balancing_mode smote

# Train with random undersampling
python main.py --balancing_mode undersample

# Use cached hyperparameters (skips 50-trial Optuna search)
python main.py --balancing_mode class_weight --use_cached_params
```

Results are saved to `reports/run_YYYY-MM-DD_HH-MM-SS_<mode>/`.

### Starting the Web Application

Open two terminal windows:

**Terminal 1: Backend**
```bash
python -m uvicorn api.main:app --reload
```
The API starts at http://localhost:8000.

**Important: Automatic Run Selection**
At startup, the backend scans the `reports/` directory, sorts all `run_YYYY-MM-DD_HH-MM-SS_*` folders in reverse chronological order, and loads model artefacts from the most recent run. This means the last pipeline execution determines which models, metrics, SHAP outputs, and fairness reports are served to the frontend. To switch which run is active, either re-run the pipeline or rename/remove newer run directories.

**Terminal 2: Frontend**
```bash
cd frontend
npm run dev
```
The frontend starts at http://localhost:5173.

### Running Tests

```bash
# Run all 31 tests
pytest tests/ -v

# Run pipeline tests only
pytest tests/test_pipeline.py -v

# Run API tests only
pytest tests/test_api.py -v
```

## Web Application

The application provides two modes accessible via a toggle in the top navigation:

**Model Comparison Mode**: Displays evaluation metrics (AUC, F1, precision, recall, accuracy) for all four classifiers as interactive cards. Each card expands to show two tabs: Evaluation Metrics and Global SHAP (beeswarm plot), with an interpretation info button providing a plain-language summary of each model's behaviour.

**Exploratory Mode**: Provides three predefined risk profiles and a custom prediction form.

- **Healthy**: Young adult (age 28), normal BMI (22.8), no risk factors, active lifestyle
- **Elevated Risk**: Middle-aged (age 45), overweight BMI (27.8), family diabetes history, sedentary
- **High Risk**: Older adult (age 62), obese BMI (36.3), hypertension, multiple concurrent risk factors

Each preset displays per-model prediction probabilities with a toggle for SHAP feature explanation. The Custom Prediction Form accepts 16 health inputs grouped into Demographics, Body Measurements, Vitals, and Lifestyle/History. BMI and waist-to-height ratio are computed server-side from height, weight, and waist circumference. All inputs are processed transiently with no data stored or logged.

**API Endpoints**:
| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check, reports loaded models |
| `/api/models/metrics` | GET | Returns evaluation metrics for all models |
| `/api/exploratory/presets` | GET | Returns three risk profile presets |
| `/api/exploratory/predict/custom` | POST | Computes predictions for custom input |
| `/api/exploratory/predict/preset/{name}` | POST | Computes predictions for a preset |
| `/api/models/{name}/interpretation` | GET | Returns model interpretation text |
| `/api/models/{name}/shap/global` | GET | Returns global SHAP beeswarm PNG |

## Key Results

| Model | Balancing | ROC-AUC | F1 | Sensitivity |
|---|---|---|---|---|
| XGBoost | class_weight | 0.847 | 0.564 | 0.676 |
| LightGBM | class_weight | 0.845 | 0.560 | 0.667 |
| Random Forest | class_weight | 0.840 | 0.555 | 0.674 |
| Logistic Regression | class_weight | 0.835 | 0.537 | 0.715 |

## Dataset

NHANES (National Health and Nutrition Examination Survey) cycles 2013-2014, 2015-2016, and 2017-2018. The pipeline automatically downloads the required .xpt files from the CDC servers on first run.

- Records: 15,757
- Features: 16 non-invasive (8 numerical, 6 nominal, 2 ordinal)
- Target: Composite label (HbA1c >= 6.5% OR insulin use OR diabetes medication)
- Class distribution: 82.4% non-diabetic, 17.6% diabetic

## Configuration

All feature definitions, NHANES variable mappings, and file paths are centralised in `src/config.py`. To modify the feature set, update the `NUMERICAL_VARS`, `NOMINAL_VARS`, and `ORDINAL_VARS` lists and re-run the pipeline.

The three balancing strategies are controlled via the `--balancing_mode` flag:
- `class_weight`: Adjusts class weights inversely proportional to class frequency (recommended)
- `smote`: Synthetic Minority Over-sampling on the training fold
- `undersample`: Random undersampling of the majority class on the training fold

## Disclaimer

This is an educational tool developed as a BSc Computer Science final year project. It does not replace clinical testing, professional medical diagnosis, or healthcare consultation. Always consult a qualified healthcare provider for medical advice.

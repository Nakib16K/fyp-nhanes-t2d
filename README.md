# Predicting Diabetes using Anthropometric, Lifestyle and Demographic Data

BSc Computer Science final year project, Brunel University London. Author: Abdullah Al Nakib.

## Overview

The project compares logistic regression, random forest, XGBoost and LightGBM using NHANES 2013–2018. A React dashboard shows evaluation results, model scores and SHAP explanations through a FastAPI backend.

The models estimate a diabetes-status label assembled from HbA1c and medication responses at the time of the survey. The app uses non-invasive inputs. Use synthetic examples in the educational demo. See the [research and privacy limits](docs/PRIVACY_AND_LIMITATIONS.md).

## What changed after submission

The April submission ran the dashboard and API locally. The November update selects thresholds on validation data, handles response codes by NHANES variable and loads the model files and results from the same run. It also adds logistic regression explanations. The AWS demo hosts the React dashboard and FastAPI backend. See the [architecture comparison](docs/HOSTING_ARCHITECTURE.md) and [development history](docs/POST_SUBMISSION_DEVELOPMENT.md).

## Project structure

| Directory | Contents |
|---|---|
| `frontend/` | React dashboard and frontend tests |
| `api/` | FastAPI routes and model loading |
| `src/` | Data preparation, training and evaluation |
| `deploy/` | Lambda adapter, viewer access template and container dependency inputs |
| `tests/` | Python regression tests |
| `notebooks/` | Original exploratory analysis code and figures |
| `docs/` | Research notes, setup details and hosting records |

## Run locally

Use Python 3.12. The frontend was tested on Windows with Node 24.22.2 and npm 11.19.1. Run these commands from `frontend/`.

```powershell
npm ci --ignore-scripts
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

The dashboard connects to `http://localhost:8000` by default. Set `VITE_API_URL` to another API address at build time. This setting is visible in the browser.

For predictions, set up a Python virtual environment and add the [model files and explanation reference](docs/REPRODUCIBILITY.md#model-files-for-the-api). Run these commands from the repository root.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 1
```

The repository excludes trained models, respondent data and credentials. API startup requires the complete run. For research training, use `main.py` with the settings in that file. It downloads data and writes a separate experiment.

## Run tests

From the repository root:

```powershell
python -m pip install -r requirements-test.txt
python -m pytest tests/ -q
```

From `frontend/` after installing dependencies:

```powershell
npm test
npm run typecheck
npm run lint
npm run build
```

The tests use synthetic fixtures and mock model loading. The frontend suite checks request handling, state and rendered text. The project records browser and cloud checks separately. See [test setup and reproducibility](docs/REPRODUCIBILITY.md#local-tests).

## Further reading

- [Dissertation notes](docs/DISSERTATION_NOTES.md) and [reference corrections](docs/REFERENCE_CORRECTIONS.md) explain how the April results relate to the later work.
- [Local explanations](docs/LOCAL_EXPLANATIONS.md) explains what SHAP shows and how the logistic regression reference is prepared.
- [Hosting operations](docs/HOSTING_OPERATIONS.md) records the dated AWS acceptance, startup delay, access controls and shutdown procedure.
- [Dependencies and licensing](docs/DEPENDENCIES.md) explains the scope of the [ISC licence](LICENSE) and links to third-party notices.

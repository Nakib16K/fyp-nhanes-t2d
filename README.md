# Predicting Diabetes using Anthropometric, Lifestyle and Demographic Data

BSc Computer Science project, Brunel University London. Author: Abdullah Al Nakib.

This project compares Logistic Regression, Random Forest, XGBoost and LightGBM using NHANES 2013–2018 data. A React dashboard displays model estimates, evaluation metrics and SHAP explanations through a FastAPI backend.

The current application uses 15 non-invasive predictors to estimate a cross-sectional diabetes-status label derived from survey medication responses and HbA1c. It is an educational research demo, not a diagnosis or a forecast of future Type 2 diabetes. The April dissertation and later November updates are documented separately in the [methodology notes](docs/DISSERTATION_NOTES.md).

## Tech stack

| Component | Tools |
|---|---|
| Research and API | Python, pandas, scikit-learn, XGBoost, LightGBM, FastAPI |
| Interface | React, TypeScript, Vite, Tailwind CSS |
| Explanations | SHAP for an uncalibrated base estimator |
| Hosted demo | CloudFront, private S3, Lambda container and private ECR |
| Tests | pytest and Node's test runner |

## Project structure

```text
api/          FastAPI routes and model loading
src/          Data preparation, training, evaluation and artifact checks
frontend/     React dashboard and browser-client tests
deploy/       Lambda adapter, dependency inputs and viewer template
tests/        Python regression tests
docs/         Methodology, runtime, dependency and development notes
notebooks/    Original EDA code with saved outputs removed
```

Models, respondent data, credentials and generated builds are excluded. API startup requires the trusted private run described in [reproducibility](docs/REPRODUCIBILITY.md).

## Frontend setup

The checked Windows toolchain uses Node 24.22.2 and npm 11.19.1. From `frontend`:

```powershell
npm ci --ignore-scripts
npm run typecheck
npm run lint
npm test
npm run build
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

The API defaults to `http://localhost:8000`. Set `VITE_API_URL` when building for another backend; it is public configuration and must contain no secret. The root package provides frontend setup/build/check wrappers as well.

## Local backend

With a compatible Python environment and the complete verified model run available:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Startup stops if models, thresholds and reports cannot be verified together. Each model uses its validation-selected threshold at full precision. The local CORS defaults allow the frontend on port 5173.

`main.py` runs the research pipeline and can download data, train models and create a new experiment. Its balancing/cache options are source settings, not command-line flags. It is separate from starting the API.

## Testing

With the research/test dependencies installed:

```powershell
python -m pytest tests/ -q
```

Python tests use synthetic data and mocked model loading. Frontend tests cover request hashing, prediction state and viewer access. Later container and cloud checks are recorded separately in the [development notes](docs/POST_SUBMISSION_DEVELOPMENT.md).

## Hosted demo

A protected AWS preview passed 28 HTTPS reference cases and 11 browser application requests on 14 November 2026. Its first cold request took about 91 seconds. It is scheduled to stop on 20 November 2026 at 18:37 UTC or earlier; it is not a permanent public service. See [hosting notes](docs/HOSTED_DEMO.md) for architecture, expiry and the distinction between deployed and later source changes.

## Research notes and licence

- [Methodology and later corrections](docs/DISSERTATION_NOTES.md) explain the survey label, retained test-set limitations and separate April/November experiments.
- [Reference corrections](docs/REFERENCE_CORRECTIONS.md) accompany the submitted dissertation. The PDF is not included or changed here.
- [Privacy](docs/PRIVACY_AND_LIMITATIONS.md), [dependencies](docs/DEPENDENCIES.md) and [runtime provenance](docs/HOSTED_RELEASE_PROVENANCE.json) describe the application and deployment boundaries.
- Author-owned code and documentation use [ISC](LICENSE). Third-party notices and the dissertation have separate terms; see [licensing scope](docs/LICENSING_STATUS.md).

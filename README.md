# Predicting Diabetes using Anthropometric, Lifestyle and Demographic Data

BSc Computer Science project, Brunel University London. Author: Abdullah Al Nakib.

This project compares machine learning models using NHANES 2013-2018 anthropometric, lifestyle and demographic data. The current educational application estimates a cross-sectional, survey-defined diabetes-status proxy. It is not a diagnosis, a clinically validated risk score or a prediction of future Type 2 diabetes incidence.

The April dissertation and the later corrected experiment are separate historical records. The current predictor contract has 15 predictors; model-specific decision thresholds come from validation data. SHAP explains an uncalibrated base estimator, rather than decomposing the final calibrated percentage. See the [methodology notes](docs/DISSERTATION_NOTES.md), [reference corrections](docs/REFERENCE_CORRECTIONS.md) and [post-submission development record](docs/POST_SUBMISSION_DEVELOPMENT.md).

## What this source contains

- React/TypeScript frontend and FastAPI backend.
- Research pipeline, preprocessing and evaluation code.
- Run-bound artifact verification, decision-threshold and application controls.
- Local tests, reference container recipes and documented runtime provenance.
- The original EDA notebook code, with saved outputs/execution metadata removed and a historical-scope notice. It has not been rerun against a new dataset.

Private models, raw/processed respondent data, prediction vectors, credentials and raw cloud evidence are not distributed here. Inference requires a separately supplied trusted, complete verified run. The source tree by itself does not include a running backend or trained model files.

## Frontend checks and local preview

The reviewed clean Windows installation used Node **24.22.2** and npm **11.19.1**. Verify `node --version` and `npm --version` in the shell used for the commands; no global npm upgrade was performed. Run these commands from `frontend`:

```powershell
npm ci --ignore-scripts
npm run typecheck
npm run lint
npm run build
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

The fresh install/type/lint/build checks passed, and the generated files matched the earlier tested build byte for byte. The point-in-time npm audit returned no known findings. Lifecycle scripts were disabled during installation; the existing build works with that setting on the tested platform. Other operating systems need their own verification.

The frontend uses `http://localhost:8000` by default. `VITE_API_URL` can select an explicitly configured backend; it is public build configuration, so it must contain no secret. Prediction features require the separate backend and trusted artifacts described below. Use synthetic examples for development.

The root package also provides explicit `setup:frontend`, `typecheck`, `lint`, `build`, `dev` and `preview` wrappers. Its automatic install lifecycle was removed, so installing the root wrapper does not silently install frontend dependencies. Use the explicit setup command when intended. The historical root ISC metadata is retained; see the licensing note below.

## Local backend prerequisites

Read [reproducibility and trusted inputs](docs/REPRODUCIBILITY.md) before starting the API. After a compatible Python environment and the verified private run have been prepared, the local entry point is:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Startup aborts if no complete, consistent run is available. The default local CORS configuration supports the frontend on port 5173. This command is local inference startup; it does not train models or create cloud resources. Installation of the backend environment and a future container rebuild have separate prerequisites and limits in the reproducibility note.

`main.py` is the research pipeline entry point. It can download data, tune, fit, calibrate and write a new experimental run. Its balancing/cache settings are source constants, not command-line flags. Research execution is a distinct workflow and is not part of the frontend/API setup above. The current frozen experiment is retained.

## Evidence and limitations

The reviewed offline source suite passed 189 tests, with one Windows symlink-permission skip. A supplementary Linux check exercised that artifact-symlink rejection boundary successfully. Tests used synthetic preprocessing data and explicit in-process API/model mocks; no frozen model was loaded, no research fit was run and external downloads were blocked. Two dependency deprecation warnings are retained. These checks improve implementation coverage without establishing clinical validity.

A bounded private Lambda trial passed 28 reviewed synthetic cases with the exact recorded patched image, saved diagnostics and verified cleanup of its owned resources. The cold first request took about 86 seconds. This is technical parity evidence, not clinical validation, comprehensive security assurance, p95/p99 performance or acceptance of public/persistent hosting.

[Runtime provenance](docs/RUNTIME_PROVENANCE.json) records exact artifact/environment identities. [Reproducibility](docs/REPRODUCIBILITY.md) distinguishes the accepted image, current research metadata and proposed future-build inputs. The Docker recipes retain unresolved base/OS locking requirements; they are not claimed to reproduce the accepted patched image.

## Privacy, dependencies and licensing

- [Privacy and limitations](docs/PRIVACY_AND_LIMITATIONS.md) describes application handling and its boundaries.
- [Dependency review](docs/DEPENDENCIES.md), [metadata index](docs/DEPENDENCY_LICENSES.json) and [frontend notices](docs/THIRD_PARTY_NOTICES.md) retain upstream terms and point-in-time check scope.
- Author-owned source and original accompanying repository documentation use the [ISC licence](LICENSE), preserving the original root package declaration. [Licensing scope](docs/LICENSING_STATUS.md) distinguishes the dissertation, third-party code/notices, datasets/models and branding, which retain their separate rights and terms.

The public dissertation copy remains deferred. The submitted PDF is preserved privately, and no derivative or publication is included here. The companion notes record known corrections without rewriting the submitted results or presenting later work as original coursework.

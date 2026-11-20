# Reproducibility

| Goal | Inputs |
|---|---|
| Run the dashboard | The frontend lock file, a compatible Node/npm environment and an API for predictions |
| Run the Python tests | `requirements-test.txt` and the synthetic fixtures in the repository |
| Run the API | A compatible Python environment and one complete trusted model run with its explanation reference |
| Build a new backend image | Reference Dockerfiles, pinned base and system packages, and fresh scan and output checks |
| Rerun the research | Verified NHANES inputs, codebooks, splits and the research environment |

Use the setup commands in the [README](../README.md).

## Local tests

[requirements-test.txt](../requirements-test.txt) adds Starlette 1.10.0 and HTTPX 0.28.1 for the Python TestClient checks. Starlette reports a deprecation warning with this combination. These dependencies are for the tests.

Run `python -m pytest tests/ -q` from the repository root and `npm test` from `frontend/`. The tests use synthetic inputs and mock model loading. The frontend suite includes controlled event handlers, hooks and server-rendered output. See the [development history](POST_SUBMISSION_DEVELOPMENT.md#validation-by-release) for separately recorded browser checks.

## Model files for the API

Place one verified run under `reports/results/`. Lambda additionally pins the run name and manifest hash. The accepted layout is:

```text
reports/results/run_f1f2_2026-11-09_16-22-47_574130/
  f1c_manifest.json
  summary_metrics.csv
  algorithmic_fairness_report.csv
  models/{lr,rf,lgbm,xgb}_pipeline.pkl
  {lr,rf,lgbm,xgb}_report.csv
  {lr,rf,lgbm,xgb}_interpretation.txt
  {lr,rf,lgbm,xgb}_shap_summary.png
  local_explanations/manifest.json
  local_explanations/lr_background.json
```

The run contains 19 frozen research files plus the two explanation reference files. Its research manifest SHA-256 is `f5bb0b3cbcec5266b2894e52cfce0b7b2434e3dee687e6d730e6301a28b56475`.

Use only artifacts you trust and keep the files together. Checksums establish whether the files match the expected record. They do not make untrusted pickles safe to load. See [local model explanations](LOCAL_EXPLANATIONS.md) for the reference files.

## Research environment

`requirements.txt` lists the direct dependencies from the November Windows environment. The [research snapshot](RESEARCH_ENVIRONMENT_SNAPSHOT.json) records Python 3.12.0 and 60 installed packages. Recreating the April run would also require its environment, data and split.

To run a new experiment, set balancing and caching in `main.py`. It writes a new run. Completed downloads move into place after the download finishes. For a controlled rerun, verify the raw files against their expected hashes separately. The [notebook](../notebooks/EDA_Notebook.ipynb) contains the original exploratory code and historical plots.

## Image records and rebuilds

The [private trial inventory](RUNTIME_PROVENANCE.json) describes the 12 November Lambda image. The [hosted release record](HOSTED_RELEASE_PROVENANCE.json) identifies the later image and asset hashes and lists subsequent text-only source changes.

The [Linux lock file](../deploy/requirements-runtime-linux.lock) lists 48 wheels checked for a future build. The deployed image came from the updates in the release record. Rebuilding that image from the reference Dockerfiles would also require pinned base, system package and installer inputs. Test compatibility, scan the image and compare its outputs before deploying a rebuild. See [dependencies and licensing](DEPENDENCIES.md).

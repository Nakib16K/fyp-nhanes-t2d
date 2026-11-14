# Reproducibility and trusted inputs

Updated 14 November 2026.

## Reproduction workflows

| Workflow | Recorded evidence | Required inputs or remaining work |
|---|---|---|
| Run the frontend | Clean Windows install/type/lint/build; reviewed package lock. | A compatible Node/npm environment and a configured API for prediction features. |
| Run inference | A manifest-bound 19-file model run, retained image identities and sampled local/cloud parity. | The private trusted artifacts are not in this repository. |
| Rebuild the backend | A checked 48-wheel Linux input set and recorded native-image lineage. | Immutable base/OS/installer inputs and a new build with scan/parity acceptance. |
| Rerun research | Source protocols, current environment metadata and the frozen run identity. | Verified raw data/codebooks/splits and a separately controlled new run. |

## Frontend

`frontend/package-lock.json` is the dependency lock. The checked Windows toolchain uses Node 24.22.2 and npm 11.19.1. A clean installation with lifecycle scripts disabled passed type/lint/build; the npm audit returned no known findings at that checkpoint. These results do not establish reproducibility across every platform or future toolchain.

Use the commands in the [README](../README.md). Root scripts wrap the frontend setup/check/build commands; they do not install frontend dependencies automatically. Author-owned source uses the [ISC licence](../LICENSE).

## Research

`requirements.txt` contains 17 direct versions read from the current Windows research environment. [RESEARCH_ENVIRONMENT_SNAPSHOT.json](RESEARCH_ENVIRONMENT_SNAPSHOT.json) records 60 observed distributions and Python 3.12.0 configuration. This is a current metadata snapshot, not proof of the environment used for the earlier fit or a complete transitive/hash lock.

The downloader stops on unavailable or empty required files and publishes completed downloads atomically. It does not cryptographically verify a historical raw-data snapshot. A separate research rerun needs trusted raw data, codebooks, splits and environment inputs, and must write a new run without replacing the frozen experiment.

The [EDA notebook](../notebooks/EDA_Notebook.ipynb) keeps its original seven code-cell sources, with saved outputs/execution metadata removed. No notebook cell was rerun during source preparation. `main.py` selects balancing/cache behaviour through source settings; it does not implement the older README's command-line flags.

## Runtime images and future builds

[RUNTIME_PROVENANCE.json](RUNTIME_PROVENANCE.json) preserves the 12 November private image record:49 Python distribution versions, Python binary hashes and 90 RPM versions. [HOSTED_RELEASE_PROVENANCE.json](HOSTED_RELEASE_PROVENANCE.json) records the later hosted image and its parent lineage.

The historical private image received ten vendor OS-package updates using release 2023.12.20261109. A later integration image overlaid the reviewed source, removed obsolete helper files and uninstalled pip from the effective runtime while preserving 48 other Python versions. A separate repair selected release 2023.12.20261112 for rpm, rpm-libs and sqlite-libs. Earlier images and the scientific artifacts were preserved. Inherited layers still contain historical installer bytes.

The [48-wheel Linux lock](../deploy/requirements-runtime-linux.lock) is a checked future-build input set; the downloaded wheels were not installed to produce that image. The reference Docker recipes still contain floating base/native inputs and do not recreate the accepted patched image. Any future candidate needs reviewed immutable inputs, native compatibility, a fresh scan and parity checks.

## Private run required for inference

The API loads one complete run from `reports/results`. The Lambda adapter additionally pins its run name and manifest hash:

```text
reports/results/run_f1f2_2026-11-09_16-22-47_574130/
  f1c_manifest.json
  summary_metrics.csv
  algorithmic_fairness_report.csv
  models/{lr, rf, lgbm, xgb}_pipeline.pkl
  {lr, rf, lgbm, xgb}_report.csv
  {lr, rf, lgbm, xgb}_interpretation.txt
  {lr, rf, lgbm, xgb}_shap_summary.png
```

These patterns describe 19 files. The manifest SHA-256 is `f5bb0b3cbcec5266b2894e52cfce0b7b2434e3dee687e6d730e6301a28b56475`. Do not mix files from different runs or load untrusted pickle files; matching a local manifest does not make arbitrary deserialization safe.

Without these private inputs, startup aborts. With a compatible environment and trusted artifacts, use the local Uvicorn command in the README. That command performs inference startup, not training or cloud provisioning.

## Deployed and later source versions

The 14 November cloud acceptance applies to its recorded image, frontend and viewer inputs. Later source cleanup changes comments/docstrings, formatting, test helpers and some frontend explanatory text. The deployed image and frontend were not rebuilt or updated for that cleanup. Hosted provenance records the source-hash differences and checks that inference logic is unchanged; it does not claim the cleaned source is byte-identical to deployment.

See [hosting notes](HOSTED_DEMO.md), [methodology](DISSERTATION_NOTES.md) and [development history](POST_SUBMISSION_DEVELOPMENT.md) for the test scope, cold-start limitation and separate April/November records.

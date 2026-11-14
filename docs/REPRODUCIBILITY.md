# Reproducibility and trusted inputs

Research/private-runtime checkpoint: 13 November 2026. Hosted-release reconciliation: 14 November 2026.

## Three different claims

| Workflow | Established evidence | Remaining boundary |
|---|---|---|
| Use the accepted private artifact | Exact Linux/amd64 image/config identities, verified frozen run, local parity and 28 actual private Lambda cases with cleanup. | Image/model files are not distributed in this source tree. Sampled results do not establish clinical or public hosting readiness. |
| Use the later hosted artifact | The recorded successor image, 18 matching runtime source inputs, preserved 19-file frozen run and 28 HTTPS plus 11 browser application requests accepted on 14 November. | Hosted availability is bounded; the first cold request took about 91 seconds. Public source excludes the image, private artifacts and deployment credentials. |
| Rebuild software | Fresh Windows frontend install/build passes. Forty-eight backend wheels were downloaded, checked against registry SHA-256/size, inspected for metadata/ZIP integrity and checked for dependency compatibility at the recorded versions. | The backend wheel set is a future-build input candidate. Immutable base/native OS/installer inputs, a new build and runtime/parity acceptance remain separate. |
| Rerun research | Current research-environment metadata and direct versions were recovered; source protocols and the frozen run are identified. | A current snapshot is not proof of the historical training environment. Raw-data acquisition hashes/codebooks, full research wheel locks and a new controlled research run are not completed by these notes. |

## Frontend

`frontend/package-lock.json` is the reviewed lock. A separate clean directory installed it with npm lifecycle scripts disabled, then passed type/lint/build. Its three production files matched the previously tested build byte for byte on Windows, Node 24.22.2 and npm 11.19.1. This does not establish cross-platform or every-future-toolchain byte reproducibility. Keep the lock unchanged unless an intentional dependency change receives its own checks.

The local commands are in the [README](../README.md). `npm audit` returned no known findings at the recorded checkpoint; this is a point-in-time registry result, not complete vulnerability assurance.

The root package is a private wrapper with explicit setup/build/check scripts, rather than an automatic install lifecycle. Its root lock has no third-party dependency entries; the actual frontend resolution remains in `frontend/package-lock.json`. The historical ISC metadata is preserved separately from any final project-wide licensing decision.

## Research environment

`requirements.txt` pins the 17 direct requirements to versions read from the current Windows research environment. [RESEARCH_ENVIRONMENT_SNAPSHOT.json](RESEARCH_ENVIRONMENT_SNAPSHOT.json) records all 60 observed distribution metadata entries and the Python 3.12.0 environment configuration. Inspection did not execute that environment's interpreter, import its pipeline, load models or train anything.

These are observations made on 13 November, not a backdated freeze or proof that every package had the same version during the earlier fit. The direct list is not a complete transitive/hash lock or validated Linux research installation. Caching hyperparameters does not guarantee exact reproducibility. `main.py` selects balancing/cache behaviour through source constants; the current entry point does not implement a balancing command-line option.

The downloader now raises on unavailable/empty required files and publishes downloads atomically; ingestion stops when a required cycle/component cannot load. Presence and non-empty content are not cryptographic verification of a complete historical raw-data snapshot. Recover and verify trusted data/codebook/split inputs before a separate research rerun. Keep new outputs under a new run identity and preserve the existing frozen experiment.

The original [EDA notebook code](../notebooks/EDA_Notebook.ipynb) is retained with its seven code-cell sources unchanged, saved outputs/execution metadata removed and a prominent historical notice. No notebook cell was executed during this review. It needs separately verified input data; rerunning against later data is not reproduction of the original April figures.

## Backend runtime and proposed wheel inputs

[RUNTIME_PROVENANCE.json](RUNTIME_PROVENANCE.json) preserves the historical private image's 49 distribution versions, Python binary hashes and 90 RPM versions. The later hosted image is recorded separately in [HOSTED_RELEASE_PROVENANCE.json](HOSTED_RELEASE_PROVENANCE.json): the same 48 non-pip distributions remain, the pip installer is absent from the effective runtime, and the later native repair changes only three RPM versions. Installed distribution/RPM licence metadata was inspected in the existing image using a non-root, read-only, no-network container without importing the API or loading models. The image was not rebuilt or changed.

[requirements-runtime-linux.lock](../deploy/requirements-runtime-linux.lock) contains 48 exact version/hash pins for a proposed CPython 3.12 Linux/x86_64 runtime. Corresponding compatible manylinux/universal wheels were actually downloaded and verified, and the active dependency constraints close at those versions. No wheel was installed. The downloaded archives remain in a private local audit cache; they are not part of this source tree.

The proposed wheel set excludes the historical private image's `pip==25.0.1` build tool. Its earlier advisories were assessed only for the finite private no-install trial; they are not fixed in that historical image or waived for future builds. The hosted successor actually removed pip from its effective runtime during a separate local integration build. Inherited layers still contain historical installer bytes; this is not proof of their removal from every layer. A future installer/build stage needs its own reviewed version, and unnecessary installation tooling should be omitted from the final runtime. Excluding pip from a proposed input list is not evidence that it has been removed from an image.

The lock is not wired into a promoted image. The reference Docker recipes still require an approved immutable base/native OS input set and explicit integration of the verified wheel inputs. Their older floating tags and direct pins do not reproduce the separate OS-patched accepted artifact. The historical private OS patch used vendor release selection 2023.12.20261109 for ten packages. A later integration image overlaid the reviewed runtime source, removed obsolete helper files and the effective pip installer, then a separate native repair selected release 2023.12.20261112 for rpm, rpm-libs and sqlite-libs. The exact lineage is recorded in the hosted provenance; do not silently drop these repairs or substitute an unverified base. Native compatibility, fresh scan and parity must be evaluated for any future rebuilt candidate. Those observed builds and cloud checks predate this documentation reconciliation; no build, upload or cloud provisioning was performed to prepare these source/documentation changes.

## Required private run for inference

The API loads one complete manifest-bound run from `reports/results`. The Lambda adapter additionally binds the recorded run identity and manifest SHA:

```text
reports/results/run_f1f2_2026-11-09_16-22-47_574130/
  f1c_manifest.json
  summary_metrics.csv
  algorithmic_fairness_report.csv
  models/
    lr_pipeline.pkl
    rf_pipeline.pkl
    lgbm_pipeline.pkl
    xgb_pipeline.pkl
  lr_report.csv, rf_report.csv, lgbm_report.csv, xgb_report.csv
  lr_interpretation.txt, rf_interpretation.txt, lgbm_interpretation.txt, xgb_interpretation.txt
  lr_shap_summary.png, rf_shap_summary.png, lgbm_shap_summary.png, xgb_shap_summary.png
```

The verified manifest SHA-256 is `f5bb0b3cbcec5266b2894e52cfce0b7b2434e3dee687e6d730e6301a28b56475`; the complete private set has 19 files. These established identifiers are retained as contracts. Do not fabricate missing files or substitute shared loose model files from another run. Run-bound hashes establish consistency with the trusted set; they do not authenticate arbitrary downloaded pickles or make untrusted deserialisation safe.

The public source intentionally excludes this private run. API startup aborts without complete verified inputs. With a compatible separately prepared environment and trusted artifacts, use the local Uvicorn command in the README; it listens on loopback with one worker. Local frontend port 5173 is covered by default CORS. No automatic training or cloud-provisioning step is part of this setup. [Hosted demo notes](HOSTED_DEMO.md) describe the observed protected deployment and its boundaries; the private orchestration and access credentials are not distributed here.

## What the source snapshot does not certify

The reconciled source preserves the accepted hosted release's application/viewer/test content and adds documentation. Two frontend files restore the original public LF line endings; their focused production-build comparison is recorded with the reconciliation. The rebuilt JavaScript and CSS match the accepted deployed bytes exactly; generated HTML differs only in line endings and an empty line left by script removal. All 18 recorded inference-runtime source hashes match the retained hosted image. It is not claimed to match the older private image source byte for byte or to rebuild the hosted image from the reference recipes. Model artifacts, scientific logic and earlier accepted images were preserved. See the [methodology](DISSERTATION_NOTES.md), [development record](POST_SUBMISSION_DEVELOPMENT.md), [dependency review](DEPENDENCIES.md) and [licensing status](LICENSING_STATUS.md) for distinct dates, evidence and limits.

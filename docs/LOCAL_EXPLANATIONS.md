# Local model explanations

The custom form returns predictions from all four models. Its model selector chooses the local explanation. Logistic Regression uses `LinearExplainer`; Random Forest, LightGBM and XGBoost use `TreeExplainer`.

Local explanations describe the first uncalibrated estimator in the cross-validation calibration ensemble. They do not decompose the final calibrated probability or its threshold decision. LR contributions are log-odds for the positive survey label. Tree outputs retain their model-specific scale; bar magnitudes should not be compared across different model families as probability changes.

## LR reference

LR uses independent-feature SHAP with the mean transformed inputs from its first calibration fold's training records. The accepted frozen run has 9,075 such records and 25 encoded features. For this linear formulation the mean is sufficient; the runtime reference contains no respondent rows. Independent masking does not model feature correlations or establish causality.

The preparation script verifies the raw-file manifest, corrected cohort, recorded splits and frozen model before creating the reference. The training fold's numerical fit matrix and order must match the saved preprocessor; categorical imputation statistics and category sets must match as well. The older processed dataset with no ethnicity-code-7 values is not substituted for the corrected cohort. No model or imputer is refitted.

Two new sidecar files bind the reference to the run, LR model, feature order and checksum. They do not alter `f1c_manifest.json` or any frozen scientific artifact. By default the API reads `local_explanations/manifest.json` and `local_explanations/lr_background.json` within its verified run. `FYP_LOCAL_EXPLANATIONS_DIR` can select a separately prepared trusted directory for local validation. Startup stops if the required reference is missing or inconsistent.

With the trusted model run and matching local provenance inputs available:

```text
python scripts/build_lr_shap_background.py
  --run-dir <trusted-run>
  --raw-dir <verified-raw-files>
  --raw-manifest <raw-file-inventory.json>
  --reference-report <corrected-cohort-and-splits.json>
  --output-dir <new-reference-directory>
  --expected-run-manifest-sha256 <frozen-manifest-hash>
  --expected-raw-manifest-sha256 <raw-inventory-hash>
  --expected-reference-report-sha256 <reference-report-hash>
```

Join the argument lines for the shell in use. The script currently validates the accepted class-weight run's recorded split protocol. Other research balancing modes remain in the training entrypoint; a different run needs its own validated reference preparation before serving LR explanations. Use only trusted, locally generated pickle artifacts. Checksums bind files together and do not make arbitrary pickles safe.

The reference inputs are private runtime prerequisites, not included model/data downloads. Prepare the sidecar outside the frozen directory, then include it in a separately validated runtime copy. The global summary plot may describe the separately fitted full-training estimator, so its background and values need not match a local calibration-fold explanation.

## Missing education and failures

The form's Refused and Don't know choices both send `education_level: null`. The field remains required; numeric attainment levels are 1–5. Raw 7/9 codes are not passed to the estimator as education levels. Prediction and explanation share the same missing-value normalization, and each existing fitted pipeline supplies its own training-derived imputation. The interface identifies imputed education.

A failed explanation leaves the current successful predictions visible and shows a separate error. Starting another request clears stale explanation state. A preset's Run Again action clears that profile's previous result; a failed retry cannot silently present the old prediction as fresh. Other profiles retain their results, and late responses from superseded requests are ignored.

## Validation scope

The historical cloud suite expected LR local SHAP to return 400; that remains a record of the earlier contract. The corrected release passed hosted acceptance on 18 November 2026: 11 browser requests and 23 HTTPS reference cases, including actual LR explanations and both education nonresponse choices. Earlier local checks cover LR additivity, reference integrity and controlled error/retry states. See [hosted provenance](HOSTED_RELEASE_PROVENANCE.json) for the exact image and separate local/cloud results.

The checked-in EDA notebook retains its original seven code cells and four embedded historical plots. Two local-path strings in saved console output are redacted. No cell was rerun; April figures remain historical and should be read with the separately dated methodology notes.

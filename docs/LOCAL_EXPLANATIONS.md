# Local model explanations

The custom form asks for predictions from all four models and an explanation from the selected model. Logistic regression uses SHAP's `LinearExplainer`. The three tree models use `TreeExplainer`.

The explanation describes the first uncalibrated estimator in the calibration ensemble. For logistic regression, contributions are changes in the estimator's log-odds relative to its reference. The final calibrated percentage and the threshold decision are separate outputs. Tree models can use different scales, so the bar lengths across models are not directly comparable.

## Logistic regression reference

The reference is the mean of the transformed inputs from the first calibration fold's training data. The accepted run uses 9,075 records and 25 encoded features. It stores only the feature order and mean, with no individual records. The explainer treats features independently when hiding them. This does not establish causal effects.

`scripts/build_lr_shap_background.py` checks the raw data inventory, cohort, splits and fitted model before calculating the reference. It checks the transformed training inputs and the categorical imputation statistics and categories against the original preprocessor. The preparation uses the class-weight run and does not refit the model.

Run `python scripts/build_lr_shap_background.py --help` for the arguments. Use the trusted run, its matching raw data and split records, and the expected hashes for those inputs. Write to a new reference directory, then add `manifest.json` and `lr_background.json` under `local_explanations/` in a verified runtime copy. For local validation, `FYP_LOCAL_EXPLANATIONS_DIR` selects an alternate trusted reference directory. Startup requires the reference to match the run and model.

## Missing education and errors

Refused and Don't know both send `education_level: null`. Valid attainment codes are 1–5. Prediction and explanation share the same missing-value handling and use the training-time imputer. The interface indicates when education was missing.

If an explanation fails, the current prediction stays visible and the interface shows a separate error. A new request clears old results for that profile and ignores responses from superseded requests. The [deployment history](POST_SUBMISSION_DEVELOPMENT.md#validation-by-release) records when the completed behaviour was checked.

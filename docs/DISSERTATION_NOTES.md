# Dissertation notes and later corrections

The April dissertation describes the submitted experiment and local application. This note records what the later review found in the April source and what changed in November. The original tables and screenshots describe the April work. See the [architecture comparison](HOSTING_ARCHITECTURE.md#april-submission) for the relationship between the submitted design and the later hosted demo.

## Scope of the project

The project compares four model families using NHANES 2013–2018 data. It estimates a diabetes-status label assembled from HbA1c and medication responses at the time of the survey. The app uses non-invasive predictors, while the research label includes a laboratory measurement. This design cannot measure future incidence or independently distinguish diabetes types.

The evaluation did not use NHANES survey weights, strata or clusters. Its sample proportions and subgroup estimates cannot establish national prevalence or clinical performance. The dashboard is an educational tool.

## Methodological corrections

Page references below identify PDF pages in the 86-page submitted document.

| Topic | Historical finding | Later treatment and interpretation |
|---|---|---|
| Threshold selection, pp31–32 and 54 | The report describes selection using training data. The original source optimised F1 using final test labels, including during fairness reporting. | Later code selects each operating threshold using validation data before applying the fixed rule to the test partition. Historical threshold-dependent F1, sensitivity, specificity and subgroup error rates require the test-selection qualification. Threshold selection alone does not alter ranking-based ROC-AUC. |
| Inference decisions, p53 | The report describes model-specific thresholds, while the original API displayed classes using 0.5. | Later inference requires the threshold belonging to each verified model/run and compares the unrounded score. The displayed flag is an exploratory model decision, not a medical cutoff. |
| Ethnicity handling, pp30,45 and83 | Generic categorical cleaning treated code 7 as nonresponse, although the appendix correctly lists it as a valid ethnicity category. | Cleaning now follows variable-specific codebooks. Saved reconciliation evidence records 604 valid ethnicity values restored, while retaining the 15,757-row labelled cohort. These were affected feature values, not 604 removed participant rows. [CDC codebook](https://wwwn.cdc.gov/nchs/data/nhanes/public/2017/datafiles/DEMO_J.htm) |
| Predictor count and alcohol input, pp2,28–29 and85 | Sixteen predictors were configured, while the missingness gate excluded the alcohol variable in the fitted preprocessors examined during subsequent audits. ALQ120Q was also presented as an annual frequency without resolving its questionnaire/unit differences. | The corrected configuration explicitly has 15 predictors; the unused alcohol input was retired from the application. Raw form fields, derived features and encoded model columns are separate contracts. Retirement of an already-excluded fitted predictor is not evidence of a performance improvement. |
| SHAP interpretation, pp33–34,49–50 and57 | The implementation extracts an uncalibrated base estimator while the interface displays calibrated model scores. | Later wording identifies the base-estimator output being explained. SHAP contributions do not decompose the final calibrated percentage, establish causality or define clinical protective effects. |
| Run consistency, pp50 and54 | Models and the latest metrics/SHAP directory could be chosen from different locations. | Later loading binds models, thresholds, metrics and explanatory artifacts to one verified run and aborts startup when a complete consistent run cannot be loaded. A file hash establishes integrity against the chosen record, not the safety of arbitrary pickle files. |
| Fairness, pp58–59 | The original table reports an ethnicity FNR spread of approximately 19.6 percentage points under its coding and threshold procedure. | Preserve that value as historical. Later subgroup analysis includes denominators and uncertainty, including the restored category. Corrected coding does not establish equitable clinical outcomes or isolate the cause of a subgroup difference. |
| Data handling, pp34,43 and50–51 | Immediate discard, zero residual trace and model-registry clearing are described broadly. | State the application-side contract precisely: prediction inputs are not intentionally written to application storage or payload logs. Garbage collection does not certify erasure from every browser, process, operating-system or infrastructure layer. |
| Reproducibility, pp48 and64 | Cached parameters are presented as ensuring reproducibility. | Reproduction also depends on data/splits, source, artifacts, runtime versions and build inputs. Later manifests and inventories improve traceability; future-build reproducibility remains a separate acceptance task. |

Page 29 checks for perfect correlation, which cannot establish whether the evaluation used information from the test data. Pages 2 and 62 report similar AUC values across the tested balancing methods. That comparison only addresses those methods and that evaluation. The studies compared on page 56 used different experiments, so the reported scores alone cannot rank the approaches.

On page 56, the class-weight scores are 0.847 for XGBoost and 0.840 for random forest. The difference is 0.007, or 0.7 percentage points. The text says about three points.

## Distinguishing the experiments

| Record | XGBoost ROC-AUC | Interpretation |
|---|---:|---|
| April dissertation, class-weight experiment | 0.847 as reported | Historical result; retain the original protocol and operating-point qualifications. |
| November engineering baseline | 0.8451917840 | Separate subsequent run with validation-derived thresholds, before the later data-contract correction. |
| November corrected run | 0.8460996229 | Separate frozen run with corrected ethnicity handling and an explicit 15-predictor contract. Its threshold is 0.2852226079, selected on validation data. |

The paired comparison evaluates the two November runs on the same reconstructed test set of 3,152 respondents, including 555 with a positive label. It resamples respondents 1,200 times to estimate intervals for the corrected run minus the November baseline.

| Model | ROC-AUC difference | Saved 95% percentile interval |
|---|---:|---|
| Logistic Regression | +0.00133418 | [-0.00003230, +0.00273085] |
| Random Forest | -0.00023832 | [-0.00167005, +0.00129082] |
| LightGBM | -0.00029591 | [-0.00188910, +0.00126110] |
| XGBoost | +0.00090784 | [-0.00065550, +0.00238951] |

All four ROC-AUC intervals include zero, so this comparison gives no clear direction for the change in ROC-AUC. Sensitivity and specificity can still move in different directions when the decision threshold changes. The comparison uses a test set examined earlier. Its membership was reconstructed from row order and the recorded random seeds. The intervals omit the NHANES survey design, and the two runs differ in more than a single code change.

## Tests and later engineering

The dissertation reports 31 tests for the original system. Later tests cover the revised application and container. The private Lambda trial and the browser demo have their own dated results in the [development history](POST_SUBMISSION_DEVELOPMENT.md#validation-by-release). These are checks of the implementation using synthetic examples.

## Reference corrections and document provenance

The [reference corrections](REFERENCE_CORRECTIONS.md) identify mismatched authors, titles and identifiers. A later public copy should label any cover changes and redactions and point readers to these companion notes. Keep the submitted copy as the record of what was assessed in April.

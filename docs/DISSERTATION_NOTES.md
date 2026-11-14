# Dissertation methodology and later corrections

Dated note: 12 November 2026.

This note accompanies *Predicting Diabetes using Anthropometric, Lifestyle and Demographic Data*, the undergraduate dissertation dated 9 April 2026. It documents findings from subsequent source and evidence review and identifies later corrections. The submitted dissertation remains the historical academic record. Its tables and screenshots describe the original implementation and experiments; later results belong to separately identified runs.

## Scope of the project

The project compares four model families using NHANES 2013–2018 data and presents model outputs through an educational React/FastAPI application. The response variable is a cross-sectional, survey-defined diabetes-status proxy derived from HbA1c and diabetes-medication responses. It does not independently distinguish all diabetes types or establish future Type 2 diabetes incidence. The predictors supplied to inference are non-invasive; a laboratory measurement contributes to the historical target definition.

The work has no established clinical diagnostic or treatment role. Survey weights, strata and clusters were not incorporated into the reported model evaluation. The sample proportions and subgroup estimates therefore must not be described as survey-weighted national prevalence or nationally representative clinical performance.

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

The absence of a perfectly correlated predictor does not rule out data leakage (p29). Similar AUC across the evaluated balancing variants does not establish an absolute feature-set performance ceiling (pp2 and62). Comparisons with another study's reported results are contextual comparisons, not a controlled superiority experiment (p56).

The statement on p56 that Random Forest trails by about three AUC points also needs correction: the displayed class-weight results, 0.847 versus 0.840, differ by 0.007, approximately 0.7 percentage points. The actual table is retained.

## Distinguishing the experiments

| Record | XGBoost ROC-AUC | Interpretation |
|---|---:|---|
| April dissertation, class-weight experiment | 0.847 as reported | Historical result; retain the original protocol and operating-point qualifications. |
| November engineering baseline | 0.8451917840 | Separate subsequent run with validation-derived thresholds, before the later data-contract correction. |
| November corrected run | 0.8460996229 | Separate frozen run with corrected ethnicity handling and an explicit 15-predictor contract. Its threshold is 0.2852226079, selected on validation data. |

The saved paired comparison uses the two November runs on the same reconstructed 3,152-respondent test partition, including 555 positive proxy labels. It does not provide a paired April-versus-November comparison. Its 1,200 iid respondent-bootstrap resamples produced the following corrected-minus-baseline ROC-AUC intervals:

| Model | ROC-AUC difference | Saved 95% percentile interval |
|---|---:|---|
| Logistic Regression | +0.00133418 | [-0.00003230, +0.00273085] |
| Random Forest | -0.00023832 | [-0.00167005, +0.00129082] |
| LightGBM | -0.00029591 | [-0.00188910, +0.00126110] |
| XGBoost | +0.00090784 | [-0.00065550, +0.00238951] |

All four intervals include zero. They do not establish a directional ROC-AUC improvement under that method. Other metric differences are not uniformly zero-crossing; operating-point changes include sensitivity/specificity trade-offs. The test partition had already been examined, its membership was reconstructed from verified row order and source seeds, and the intervals do not account for NHANES survey design. This is descriptive comparison, not fresh external validation, equivalence testing or a causal estimate of a single code change.

## Tests and later engineering

The dissertation's 31-test report describes its original suite and environment. Later application regression, local container checks and real Lambda invocations are separately dated evidence. Mock endpoint tests, synthetic parity checks and actual cloud calls establish different properties. None substitutes for clinical validation or independent assessment of model generalisation.

Subsequent work introduced stricter input/threshold/run contracts, application security and privacy safeguards, CPU-only packaging, read-only/non-root runtime support and a bounded private AWS trial. These changes occurred after submission. The final private trial passed all 28 reviewed synthetic cases and completed resource cleanup; its first request took approximately 86 seconds, leaving a material cold-start limitation for any later interactive hosting decision. See [Post-submission development](POST_SUBMISSION_DEVELOPMENT.md).

## Reference corrections and document provenance

The retrospective reference check found author, identifier and publication-target errors. Exact corrections and qualifications are recorded in [Reference corrections](REFERENCE_CORRECTIONS.md). Bibliographic identity checking does not establish that every sentence of the original literature review follows from its cited source. Claims copied into later documentation must be supported at the appropriate scope.

Any public dissertation copy should identify its redactions, cover changes and companion notes while preserving the privately held original. It must not imply that later corrections were present in the assessed submission. This note records technical and methodological findings; it does not determine the university's assessment outcome or confer clinical approval.

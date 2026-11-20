# Dissertation notes and later development

The April dissertation records the submitted experiment and local application, including the four-model comparison, SHAP analyses and two dashboard modes. Its tables and screenshots describe that work. This note explains how to read the April results and what changed in the separate November work. See the [architecture comparison](HOSTING_ARCHITECTURE.md#april-submission) for the relationship between the submitted design and the hosted demo.

Page references in these notes use the PDF page positions of the 86-page April 2026 submission. Section, table and figure numbers identify the same material within that edition.

## Scope of the project

The project compares four model families using NHANES 2013–2018 data. It estimates a diabetes-status label assembled from HbA1c and medication responses at the time of the survey. The app uses non-invasive predictors, while the research label includes a laboratory measurement. This design cannot measure future incidence or independently distinguish diabetes types.

The evaluation did not use NHANES survey weights, strata or clusters. Its sample proportions and subgroup estimates cannot establish national prevalence or clinical performance. The dashboard is an educational tool.

## Limitations carried forward

The dissertation's conclusion and future work (§7.2–7.3, PDF pp65–66) identify limits that still apply.

- **External and temporal validation.** The April and November experiments use the same NHANES 2013–2018 survey cycles. Performance in an independent dataset, a later survey cycle or a clinical setting remains unknown.
- **Missed cases.** The April dissertation reported 67.6% sensitivity at its selected operating point. November uses validation-derived thresholds. Missed positive labels and the sensitivity/specificity trade-off still depend on the operating point. The dashboard uses the saved thresholds, and an adjustable threshold remains future work.
- **Subgroup differences.** The dissertation reported disparities as part of its fairness audit. Later analysis uses the corrected category coding, counts and uncertainty to give more context. Fairness-aware training and mitigation remain future work.
- **Label scope.** The current task is a binary comparison against the survey-derived label. A separate prediabetes category remains future work.

The usability review (§6.6, PDF p62) also identified a gap in error recovery. The form has field-level checks, and prediction and explanation failures appear separately. API validation failures still lack field-specific feedback in the dashboard.

## April methods and November follow-up

| Topic | April experiment or application | November treatment and interpretation |
|---|---|---|
| Threshold selection, pp31–32 and 54 | The dissertation describes selection using training data. The April implementation selected the F1 operating point using test labels, including for the fairness audit. Read the reported F1, sensitivity, specificity and subgroup error rates in that context. | November selects each operating threshold on validation data and applies the fixed rule to the test partition. ROC-AUC is based on score ranking and does not depend on the selected threshold. |
| Inference decisions, p53 | The dissertation describes model-specific thresholds. The April dashboard API used 0.5 for its displayed decisions. | November inference uses the threshold from the verified model run and compares the unrounded score. The displayed flag represents the model's exploratory decision. |
| Ethnicity handling, pp30,45 and83 | Generic categorical cleaning treated code 7 as nonresponse, although the appendix correctly lists it as a valid ethnicity category. | Cleaning now follows variable-specific codebooks. Saved reconciliation evidence records 604 valid ethnicity values restored, while retaining the 15,757-row labelled cohort. These were affected feature values, not 604 removed participant rows. [CDC codebook](https://wwwn.cdc.gov/nchs/data/nhanes/public/2017/datafiles/DEMO_J.htm) |
| Predictor count and alcohol input, pp2,28–29 and85 | Sixteen predictors were configured, while the missingness gate excluded the alcohol variable in the fitted preprocessors examined during subsequent audits. ALQ120Q was also presented as an annual frequency without resolving its questionnaire/unit differences. | The corrected configuration explicitly has 15 predictors; the unused alcohol input was retired from the application. Raw form fields, derived features and encoded model columns are separate contracts. Retirement of an already-excluded fitted predictor is not evidence of a performance improvement. |
| SHAP interpretation, pp33–34,49–50 and57 | The implementation extracts an uncalibrated base estimator while the interface displays calibrated model scores. | Later wording identifies the base-estimator output being explained. SHAP contributions do not decompose the final calibrated percentage, establish causality or define clinical protective effects. |
| Run consistency, pp50 and54 | Models and the latest metrics/SHAP directory could be chosen from different locations. | Later loading binds models, thresholds, metrics and explanatory artifacts to one verified run and aborts startup when a complete consistent run cannot be loaded. A file hash establishes integrity against the chosen record, not the safety of arbitrary pickle files. |
| Fairness, pp58–59 | The April table reports an ethnicity false-negative rate spread of about 19.6 percentage points under its coding and threshold procedure. | The later audit includes counts and uncertainty, including for the restored category. The audit describes the observed subgroup results. It does not establish the cause of a difference or equitable clinical outcomes. |
| Data handling, pp34,43 and50–51 | The dissertation describes transient input handling in the local application. | The API is designed to avoid writing prediction inputs to application storage or payload logs. Browser, process and infrastructure handling can still differ. |
| Reproducibility, pp48 and64 | The April workflow reused cached tuning parameters. | Reproducing a run also depends on the data, split, source, artifacts, runtime versions and build inputs. Later manifests and inventories make these inputs easier to trace. |

Page 29 checks for perfect correlation, which cannot establish whether the evaluation used information from the test data. Pages 2 and 62 report similar AUC values across the tested balancing methods. That comparison only addresses those methods and that evaluation. The studies compared on page 56 used different experiments, so the reported scores alone cannot rank the approaches.

The April class-weight results in Table 6.1 (PDF p54) give 0.847 for XGBoost and 0.840 for random forest. The difference calculated from those values is 0.007, or 0.7 percentage points.

## Distinguishing the experiments

| Record | XGBoost ROC-AUC | Interpretation |
|---|---:|---|
| April dissertation, class-weight experiment | 0.847 as reported | April result under the submitted experiment's protocol. |
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

The [reference corrections](REFERENCE_CORRECTIONS.md) identify mismatched authors, titles and identifiers. The submitted dissertation is the record of the April assessment. A public reference copy can retain its page positions and identify cover changes and redactions. A revised edition can use its own date and page references.

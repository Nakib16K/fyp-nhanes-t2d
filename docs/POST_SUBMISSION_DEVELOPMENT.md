# Post-submission development

Updated 14 November 2026. The original main commit is `aa77d31d105ee394ed5bed551edd732977db788c`, dated 8 April 2026; the dissertation is dated 9 April. The changes below were made later and do not rewrite the submitted academic record.

## Methodology and application

Later work moved threshold selection from test labels to a separate validation partition, used each model's selected threshold for inference, preserved valid ethnicity code 7 and made the 15-predictor input set explicit. Models, thresholds, metrics and explanations now load from one verified run. Startup stops when that run is missing or inconsistent.

SHAP wording identifies the uncalibrated base estimator being explained. Displayed model percentages and validation cutoffs are not clinical diagnoses. The separate November comparison retains its test-reuse and survey-design limitations; it does not establish an AUC improvement. [Methodology notes](DISSERTATION_NOTES.md) give the detailed corrections and separate experiment results.

New form submissions clear old predictions before requesting another result. Failed predictions therefore cannot leave a previous input's estimate visible. Required data downloads stop ingestion on errors/empty files and are published atomically once complete. Privacy wording describes API transmission and browser-held state without promising complete erasure.

## Runtime problems and fixes

| Problem | Fix and result |
|---|---|
| Read-only/non-root startup needed directories normally created at import. | Created required directories during the image build and checked startup/parity. Original artifacts and fallback images were retained. |
| ECR rejected the repository policy even though generic IAM validation had no findings. | Corrected the service-specific attachment form; later upload/scanning succeeded. The initial generic error did not isolate a particular member. |
| Registry login failed while command output was suppressed. | Isolated temporary credentials, kept redacted diagnostics and removed credentials after use. Later authentication/uploads passed; the exact first failure cause remains unknown. |
| A CLI sign-in expired overnight. | Refreshed the existing temporary sign-in. No persistent access key or Docker restart was required. |
| The first uploaded image had 16 package/CVE scan entries covering 8 CVEs. | A separate ten-package vendor OS patch retained application/artifact hashes and Python versions. Local parity and a subsequent exact-image scan passed. |
| The first Lambda request timed out at its 30-second function allowance. | Set separate function/client time budgets, used 120 seconds for the function and disabled automatic invocation retries. The same patched image then passed 28 private Lambda cases. Its first request still took about 86 seconds. |
| Failed-request logs were removed before export. | Saved returned tails and bounded CloudWatch logs before deletion. The successful private trial retained 89 events and verified removal of all four owned resource types. |
| A later hosted-image scan reported 11 package/CVE entries covering 9 CVEs. | Updated only rpm, rpm-libs and sqlite-libs to the recorded vendor fixes. The repaired image retained 37 task files, 19 frozen files and 48 Python distributions; 28 local handler cases passed. The 14 November exact-image scan had no findings. |
| The edge viewer returned 503 instead of a credential challenge; the result reader also used the wrong response envelope. | Corrected envelope handling. An isolated probe found the recorded ISO expiry string parsed non-finite; numeric epoch expiry passed 10 live diagnostic checks. The temporary function and the failed hosted attempt's 15 owned entries were removed/absence-verified. |
| Categorical captions and wrapped titles shifted SHAP rows/panels. | Reserved matching row/title space and checked labels, values and bars at wide/narrow widths, including the hosted browser. Scientific values/order were unchanged. |

The particular date-string failure does not establish that every date parser feature is unsupported. Scan findings are point-in-time OS results, not exhaustive security clearance. Earlier unsuccessful attempts remain separate from the later successful checks.

## Hosted acceptance — 14 November 2026

The repaired image passed a fresh scan before inference. Protected-origin/viewer checks, periodic guard delivery and a scheduled API concurrency 1-to-0 rehearsal passed before activation; the operational cutoff was restored.

All 28 synthetic reference cases passed through authenticated CloudFront HTTPS, followed by 11 browser application requests. Those 39 controlled attempts checked metrics, interpretation, global SHAP, presets and predictions/local explanations with concurrency 1 and no operator/client retry. Offline fixture tests and the earlier private Lambda trial are separate evidence.

The first cold HTTPS health request returned HTTP 200 after about 91 seconds. Provider logs retain an initial initialization timeout before successful handling of that same request. Joblib serial fallback and a LightGBM TreeExplainer warning also remain. Cold-start latency is unresolved; these checks do not establish p95/p99 or clinical performance.

The preview is scheduled to stop on 20 November 2026 at 18:37 UTC or earlier. Final deletion/absence verification remains pending while it runs. [Hosting notes](HOSTED_DEMO.md) and [provenance](HOSTED_RELEASE_PROVENANCE.json) identify the controls, image and validation scope.

## Source cleanup and reproducibility

The 14 November cleanup passed 201 Python tests with one Windows symlink skip, plus 30 frontend tests, type checking, lint and build. A local browser replay checked the revised SHAP wording and alignment. Source tests use actual loader methods with synthetic boundaries, mocked models and explicit startup fixtures. Later source cleanup removes private staging-folder fallbacks and missing-source skips from required integration checks. New middleware/tests follow the original code's spacing, and comments describe implementation reasons directly.

The frontend's request hashing preserves the exact UTF-8 body and caller headers. API CORS permits its signing-payload header while retaining the origin allowlist. Unused starter metadata links and local-port-only error copy were removed. Later SHAP grammar/explanation cleanup is present in source but has not been deployed to the accepted preview.

Dependency locks, notices and provenance retain their own dates. A current environment snapshot is not a historical training freeze. Reference Docker recipes still need immutable base/native inputs and new-image validation. The original EDA code is preserved with saved outputs removed; neither the notebook nor research experiment was rerun for source cleanup.

The 19 scientific artifacts and previous images remain unchanged. The dissertation PDF, data, models, credentials and raw cloud evidence are excluded from the source release. [Reproducibility](REPRODUCIBILITY.md), [licensing](LICENSING_STATUS.md) and [reference corrections](REFERENCE_CORRECTIONS.md) provide the remaining details.

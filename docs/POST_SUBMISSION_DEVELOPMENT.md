# Post-submission development and validation

Checkpoint: 13 November 2026.

The original code checkpoint is commit `aa77d31d105ee394ed5bed551edd732977db788c`, dated 8 April 2026, and the dissertation is dated 9 April 2026. Later changes are recorded under their subsequent development dates. The original source history and dissertation results are preserved. This record describes the work after that academic baseline.

## Methodology and application contracts

Subsequent review identified a mismatch between the reported threshold-selection procedure and the source, an inference rule using 0.5 instead of each model's selected threshold, generic cleaning of a valid ethnicity code, and an unused/unharmonised alcohol input. Later work corrected those contracts, retained separate experimental outputs and added run-bound artifact verification. The interface now distinguishes educational model thresholds and base-estimator SHAP from clinical diagnoses and calibrated probability explanations.

The corrected scientific run remains frozen. It uses validation-selected thresholds and an explicit 15-predictor contract. The paired comparison of two November runs does not establish ROC-AUC superiority and retains reused-holdout, label and survey-design limitations. [Dissertation methodology note](DISSERTATION_NOTES.md) records the distinctions and reference corrections.

## Reliability and deployment work

| Observed problem | Correction and evidence | Remaining qualification |
|---|---|---|
| Model startup could continue without a complete verified run. | Changed startup to abort, clear partial registry state and propagate the failure. Updated the corresponding lifespan tests and isolated route-test fixtures. | Source selection must retain the corrected API and its matching tests together. |
| CPU/runtime packaging was larger and read-only startup required directories normally created at import. | Used a separate CPU-only dependency candidate and created required runtime directories during the image build. Local parity and read-only/non-root checks were recorded. | Preserve the original fallback and scientific artifacts; build reproducibility is separate from running an existing image. |
| ECR rejected a repository policy despite generic IAM validation returning no findings. | Corrected the service-specific attachment form while retaining the reviewed principal, actions and function restrictions. Subsequent checked execution reached upload and scanning. | The original rejection did not isolate its precise offending member. Generic policy validation is not service admission. |
| Registry login failed while useful command output was suppressed. | Repaired temporary credential isolation, preserved the running Docker endpoint, retained redacted diagnostics and removed temporary credentials after use. Actual authentication and subsequent uploads passed. | An isolation flaw was established; the exact cause of the first suppressed login failure remains unknown. |
| A browser-based CLI sign-in expired between sessions. | Refreshed the existing temporary sign-in and verified identity during subsequent execution. | This was separate from the earlier day's registry error; it did not require persistent access keys or engine restart. |
| The first uploaded image returned 16 OS scan entries covering eight CVEs. | Built a separate OS-only candidate updating ten system packages to vendor-fixed releases. Packaged application/artifact hashes and Python runtime/distribution versions stayed unchanged; local parity passed. A later exact-digest scan reported no findings. | Point-in-time BASIC OS scanning is not a complete vulnerability assessment. Package-manager advisories were reviewed separately for the restricted trial; release dependency review remains necessary. |
| A final local report assumed an image-metadata field that was absent. | Recovered the config digest from the actual descriptor and corroborating metadata/logs; retained the reporting interruption. | The successful build and checks were not relabelled as a new repeated experiment. |
| The first real Lambda request returned a client timeout. Retained metrics showed one function error at its 30-second allowance. | Separated function and client budgets, used a 120-second function allowance for a diagnostic run, retained first-health gating and disabled automatic Invoke retries. The same patched image passed all 28 actual Lambda cases. | Exact failing work in the earlier request is unknown because its logs were lost. The successful run still took about 86 seconds for its cold first request. |
| Cleanup initially removed the log group before failure evidence was exported. | Saved returned tails before response validation and captured bounded owned-session logs before deletion. The successful trial retained 89 CloudWatch events and verified removal of all four owned resource types. | Log export was bounded; it is not a guarantee of every delayed provider event. |

These entries distinguish observed failures, inferred causes and verified corrections. Earlier scientific/application checks include retained local test records; the latest private trial was monitored through completion. Simulated workflow checks establish particular error/ownership/cleanup behaviour, rather than actual service startup or permissions by themselves.

## Measured private-trial result

- The exact patched image passed a fresh OS scan with no reported findings before inference.
- All 28 reviewed synthetic Lambda cases passed, with no automatic client Invoke retries.
- Returned invocation evidence and 89 CloudWatch events were saved before cleanup.
- All four trial-owned resources were removed and verified absent at the end of the run.
- First-request client wall time was approximately 86.0 seconds; the final warm health request reported 2.58 ms of function duration.
- Peak reported memory was 1,205 MB of the configured 2,048 MB.

The first request recorded an initial Init timeout followed by successful initialisation during invocation. Its reported 74.9-second duration includes startup work and is not a warm health-handler benchmark. A joblib serial-mode fallback warning was retained; sampled outputs matched, without a speculative warning-related code change.

This is a small synthetic technical validation. It does not establish p95/p99 latency, clinical accuracy, generalisation, fairness, complete security or a good public cold-start experience. The earlier failed invocation remains part of the history. No persistent/public service was left running by this trial.

## Interface presentation

The release candidate displays categorical SHAP indicator status on a separate line below its feature label. Contribution values align with the top of the label, and preset cards stack below desktop width to keep the explanations readable. A subsequent visual review identified unequal row heights because categorical captions and wrapped descriptions occupied additional space. Preset rows now reserve matching space so labels, values, bars and descriptions line up across the cards; custom-form spacing is preserved. The revised browser check verifies all five visible row positions, extending the earlier label-only alignment check. Feature names, numeric labels, contribution order and values are preserved. Local browser checks at five viewport widths replayed saved synthetic trial responses, including custom-form explanations for XGB, RF and LGBM. These presentation checks are separate from live model inference or another cloud trial.

Training-source comments now describe the reused test partition as retained rather than untouched. This is a wording correction; executable training logic and frozen model artifacts are unchanged. The source-contract check references this descriptive development record in place of the private working changelog, while retaining its existing deployment checks.

## Reproducibility and source preparation

A fresh isolated frontend installation with lifecycle scripts disabled passed type/lint/build and reproduced the earlier production-file bytes on the tested Windows/Node/npm environment. The registry audit returned no known findings at that checkpoint. Missing dependency licence metadata was resolved from available exact-version records, and the frontend notices are preserved separately.

Current research-environment metadata supplied the 17 direct dependency pins and a 60-distribution snapshot. These are current observations, not a backdated training freeze. The existing runtime's 49 distribution versions and 90 RPM records were matched during a read-only/no-network licence inspection. A proposed 48-wheel Linux runtime input set was downloaded and hash/metadata/dependency checked without installation; it excludes the old pip build tool but does not change that tool inside the accepted image. No models were loaded or trained and no image was rebuilt.

The README now separates frontend checks, prerequisite-bound local inference and research execution. Ignore rules exclude private artifacts/credentials/caches, with a final reviewed file allowlist still required. Runtime/research provenance, privacy scope and dependency/licensing notes distinguish observed evidence from unresolved future-build inputs. Stale recipe/adapter comments were updated without changing executable application behaviour.

Final source review retained and clarified the original root wrapper and its ISC metadata, removing automatic install behaviour in favour of explicit frontend commands. The original EDA code was preserved with saved outputs and execution metadata removed, rather than silently dropping the notebook. Legacy loader tests were changed to call the actual implementation instead of copied label/cleaning logic, with exact missingness boundaries and field-specific code regressions. A full-precision decision test now seeds its explicit mock registry before entering the fail-fast application lifespan. These are test/setup/public-source corrections; the scientific implementation and frozen artifacts remain unchanged.

The first complete offline suite exposed another stale fixture that expected post-startup offline behaviour without supplying mocks before the startup gate. Explicit pre-startup mock seeding preserved that test's purpose and the production fail-closed contract. The corrected suite passed 199 tests with one Windows symlink skip; a separate Linux artifact-symlink check passed. No real model deserialisation or external HTTP connection occurred, and dependency deprecation warnings were retained. Root install/check/build wrappers passed offline, with frontend production bytes still matching the earlier verified build.

## Final source-review corrections

A new custom submission clears the previous result before requesting predictions, so a failed request cannot leave a different input's estimate displayed. A focused synthetic handler regression covers the success-then-failure path. The visible privacy notice now describes API transmission and browser-held state without promising immediate erasure.

Metric help and future report templates refer to survey-proxy labels and describe F1 without clinical error-cost claims. Historical report displays include that context; the frozen report files and models remain unchanged. Input-schema/preset comments describe validation bounds and illustrative examples without claiming clinical validity.

Research acquisition now raises if required downloads fail or are empty, publishes completed files atomically and stops when a required cycle/component cannot load. Synthetic tests cover these error paths and a complete merge. This does not hash-certify historical raw inputs or rerun the experiment. Existing main-file line endings are retained to reduce diff noise.

Merging this development line requires the intended cloud deployment to be running and checked against the release, followed by a separate merge decision. The recorded private trial ended with cleanup and does not establish a current hosted service.

## Release work still required

Future backend rebuilds still need immutable base/native OS/installer inputs and actual new-image acceptance; the research snapshot is not a full historical transitive/hash lock. Final local source/diff/privacy review is complete within the selected-file scope, and the prepared source uses ISC for author-owned code/documentation while preserving upstream terms. This does not certify all repository history or project-specific ownership restrictions; external publication remains a separate decision. Public dissertation creation is explicitly deferred; its plan is separate from source preparation. Public-facing names describe behaviour and follow the original code style. Frozen artifact identifiers remain where they are established contracts; a wholesale rename is not a cosmetic change.

Private models, raw or respondent-level data, prediction vectors, credentials, local provenance paths and unredacted AWS evidence are excluded from public material by default. Research reproduction and deployment instructions should explain required private inputs without silently distributing them or triggering training/cloud provisioning. The reviewed source remains separate from any later decision to publish or host it.

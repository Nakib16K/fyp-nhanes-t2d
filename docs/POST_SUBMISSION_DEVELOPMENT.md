# Post-submission development

This record follows the April final submission on [main](https://github.com/Nakib16K/fyp-nhanes-t2d/tree/aa77d31d105ee394ed5bed551edd732977db788c). The source commit is dated 8 April 2026 and the dissertation is dated 9 April. The later results are described by date and run in the [dissertation notes](DISSERTATION_NOTES.md).

## Research and application changes

- Thresholds now come from validation data and are held fixed during test evaluation. The API uses the individual model's threshold and loads models, metrics and reports from the same verified run.
- Cleaning now uses the response codes for each NHANES variable. It keeps valid ethnicity code 7. The application dropped the alcohol input because the examined fitted preprocessors had already excluded it.
- April's form offered logistic regression in its explanation menu, but the endpoint rejected that option. The completed implementation checks a training reference tied to the verified model and explains the first uncalibrated estimator. Refused and Don't know for education now reach the fitted preprocessing pipeline as missing values. See [local explanations](LOCAL_EXPLANATIONS.md).
- A new request clears the previous result. Explanation failures have their own message and older responses cannot overwrite the latest preset request. The display labels the source and scale of the explanation and aligns feature rows across preset cards.
- Required downloads stop the research run on errors or empty files. Successful downloads move into place only after they are complete. The notebook retains its seven code cells and four original plots, with two local paths removed from saved console output.

## Packaging and deployment problems

| What happened | What changed |
|---|---|
| The container needed directories that the code normally created at startup. | Create those directories during the build so the non-root, read-only runtime can start. |
| ECR rejected the repository policy after generic IAM validation reported no findings. | Correct the policy for ECR. Later attachment and upload succeeded. The first error did not identify the failing field. |
| Docker registry login failed with its output suppressed. | Use isolated temporary credentials and retain redacted diagnostics. Later login and upload succeeded. The first failure's cause remains unknown. |
| A temporary AWS sign-in expired. | Refresh the existing sign-in. |
| The first uploaded image had 16 findings across eight CVEs. | Patch ten OS packages while keeping the application, Python versions and model files. Local parity and the later scan of that exact image passed. |
| The 30-second Lambda trial stopped on the first request. | Give Lambda 120 seconds, allow the client to wait for the result and preserve logs before deleting resources. The successful private trial passed 28 cases and verified removal of all four trial resources. Its first health request took about 86 seconds. |
| A later image scan reported 11 findings across nine CVEs. | Update rpm, rpm-libs and sqlite-libs. The repaired image kept 37 packaged files, 19 frozen research files and 48 Python distributions. It passed 28 local handler cases and the 14 November exact-image scan returned zero findings. |
| The CloudFront viewer returned 503 instead of a credential challenge. The result reader also expected the wrong response format. | Fix the result reader. The edge runtime could not turn the recorded expiry string into a number, so the viewer now uses an epoch timestamp. Ten hosted diagnostic cases passed. The temporary diagnostic function and the failed hosted attempt's 15 tracked resources were removed and checked for absence. |
| An AWS CLI wrapper sent generic JSON arguments to commands that required their own options. | Pass those options directly and check registry login before cloud changes. The stopped attempt rolled back before application tests. |
| An access check assumed that an unsigned Lambda URL should return 401. | Record the expected outcome for each origin and save responses before checking them. The Lambda URL correctly returned 403. The stopped attempt rolled back with zero application requests. The next session reused the uploaded image and passed. |

## Validation by release

| Date and scope | Result |
|---|---|
| 12 November private Lambda trial | 28 synthetic cases passed. The runner saved 89 log events and verified cleanup. |
| 14 November protected browser demo | 28 HTTPS reference cases and 11 browser requests passed. This release's test expected the local logistic regression endpoint to reject the request. First health took about 91 seconds. |
| 18 November corrected browser demo | 11 browser requests and 23 HTTPS cases passed, including logistic regression explanations and both education nonresponse choices. The release reused the same-image scan and six earlier viewer tests after checking their inputs. |
| 18 November local source maintenance, rechecked 20 November | 263 Python tests passed with one Windows symlink skip. 53 frontend tests, type checking, lint and build passed. |

The 18 November deployment changed the image, the frontend assets and the saved expiry and shutdown settings within the existing protected architecture. The old 20 November cutoff became historical after the new watchdog schedule and application checks passed. See [hosting operations](HOSTING_OPERATIONS.md) for the later cutoff and measured startup delay.

The earlier 48 local API and 48 native adapter cases exercised the same frozen model run. The maintained source adds test coverage for threshold ties, request size limits, production configuration and the interface's disclosures. Local, container and hosted results cover different parts of the system. The November model run was kept through the deployment and explanation work.

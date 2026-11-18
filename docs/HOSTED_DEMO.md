# Hosted educational demo

The corrected protected AWS demo passed acceptance on **18 November 2026**. It includes LR local explanations, education nonresponse handling and separate prediction/explanation error states. The latest scheduled stop is **8 May 2027 at 00:00 UK time (7 May at 23:00 UTC)**, with earlier financial and safety stops. This is a dated deployment record, not permanent hosting.

## Architecture

CloudFront serves React assets from private S3 and forwards API requests to an AWS_IAM Lambda Function URL. Origin access controls sign requests to both origins. The Lambda container runs FastAPI through Mangum; its image is stored in private ECR.

A viewer-request function checks a private credential hash and numeric expiry before page, asset and API access. It denies invalid or expired configuration and removes viewer authorization before forwarding. The browser supplies a SHA-256 hash of the exact UTF-8 POST/PUT body; it never holds AWS signing credentials or automatically retries a failed prediction. Page and API share one HTTPS domain.

The published viewer template contains no credentials. Account-specific policies, orchestration, model artifacts and rendered access configuration are excluded. The demo uses authenticated internet access. Use synthetic examples.

## Recorded checks

The 18 November acceptance passed 11 browser application requests and 23 HTTPS reference cases: 34 requests in total, with no operator retry or prewarming. Browser checks displayed LR local explanations, both education nonresponse choices, model metrics, interpretation text, global SHAP and synthetic presets. The reference cases checked the corrected responses against frozen local expectations.

Before the update, the exact image's completed ECR BASIC scan had zero findings. That scan and six unchanged actual viewer runtime tests from the earlier attempt were reused after image, code and configuration checks; they were not rerun or counted as new tests. Missing or wrong viewer credentials returned 401, and unsigned direct Lambda/S3 requests returned 403. The published viewer then passed valid-page and wrong-credential checks.

A new scheduled watchdog delivery reported eligible Free Plan status under the extended lease. Guard configuration, the unchanged periodic schedule and both final-stop schedules were read back before extending the API-off timer last. Final resource deletion remains pending while the demo runs.

The earlier 14 November release separately passed 28 HTTPS cases and 11 browser requests. Its matrix expected LR local SHAP rejection. That historical result does not describe the corrected LR endpoint.

## Startup and limits

The first corrected-image health request returned 200 after **103.502 seconds**; the dashboard was ready after 104.213 seconds. A later health request took 117.369 milliseconds. The same log stream records an initial ten-second initialization timeout, followed by successful handling. The timing is consistent with Lambda retrying initialization within the invocation allowance; individual import/model stages in AWS were not profiled. The interface shows a connecting state while it waits.

Cold-start delay remains unresolved. The older 91-second first hosted request and separate 7.23-second sample describe the previous image. These individual observations are not a latency distribution or evidence of an improvement. See [AWS's runtime lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html) for initialization behaviour.

Small synthetic checks establish sampled technical behaviour, not clinical validity, a comprehensive security audit or a performance guarantee. Scan findings are point-in-time OS results. Earlier joblib serial fallback and LightGBM TreeExplainer warnings remain recorded.

## Operation and shutdown

The API reserves concurrency 1, 2048 MiB memory and a 120-second timeout. The five-minute watchdog requires an eligible ACTIVE Free Plan and a USD20 credit reserve, and stops earlier for unavailable financial state, ineligibility, the expiry margin or an owner/safety stop. Separate scheduled guard/API-stop actions and viewer expiry use the final cutoff above. There is no Paid upgrade, automatic renewal, paid prewarming or provisioned concurrency.

The 18 November approved extension superseded the old 20 November operational stop only after application and control acceptance. The original creation time and ownership record were preserved under a separate bound lease. Eligible credits may be consumed; the owner-cash limit is USD0. Budget alerts and reserve checks are not hard lifetime spending caps or a cost forecast.

Access denial, concurrency 0 and distribution disablement are distinct from resource deletion. Final cleanup must verify owned-resource absence and then remove the unused retained guard role. Scheduler delivery and CloudFront propagation prevent an exact-second deletion guarantee.

## Source version

[Hosted provenance](HOSTED_RELEASE_PROVENANCE.json) records the current image and dated history. The application, frontend and tests in this source release match the accepted 106-file source snapshot. Documentation was updated after acceptance to record the results and new stop. Those documentation edits do not require an application rebuild. Frozen scientific artifacts remain unchanged; models, data, credentials and raw cloud evidence are excluded.

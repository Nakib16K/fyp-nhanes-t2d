# Hosted educational demo

The protected AWS preview passed its recorded acceptance on 14 November 2026. Its scheduled stop is **20 November 2026 at 18:37 UTC**, or earlier for an eligibility/credit trigger. This is a dated deployment record, not a promise of permanent availability.

## Architecture

CloudFront serves React assets from private S3 and forwards API requests to an AWS_IAM Lambda Function URL. Origin access controls sign requests to both origins. The Lambda container runs FastAPI through Mangum; its image is stored in private ECR.

A viewer-request function checks a private credential hash and numeric expiry before page, asset and API access. It denies invalid/expired configuration and removes viewer authorization before forwarding. The browser supplies a SHA-256 hash of the exact UTF-8 POST/PUT body; it never holds AWS signing credentials or automatically retries a failed prediction. Page and API share one HTTPS domain.

The viewer template is published without credentials. Account-specific policies, orchestration, model artifacts and rendered access configuration are not distributed in this source tree. Access is authenticated over the internet, rather than VPC-private networking. Use synthetic examples.

## Recorded checks

- The exact image completed an ECR BASIC scan with no findings before inference. This is a point-in-time OS scan.
- Missing/wrong viewer credentials and unsigned direct S3/Lambda requests were denied.
- Periodic guard delivery and a scheduled API concurrency 1-to-0 rehearsal passed before activation; the cutoff was then restored.
- All 28 authenticated HTTPS reference cases and 11 browser application requests passed. Browser checks covered metrics, interpretation, global/local SHAP, three presets and responsive alignment.

The first cold health request returned HTTP 200 after about 91 seconds. Logs retain an initial provider initialization timeout, followed by successful handling of that request; no operator/client retry was sent. Joblib serial fallback and a LightGBM TreeExplainer output warning remain. These small synthetic checks are functional validation, not clinical validation, a comprehensive security audit or percentile-latency measurements.

## Operation and shutdown

The API reserves concurrency 1, 2048 MiB memory and a 120-second timeout. A periodic guard checks eligible free-plan status, credit reserve and the lease. Separate scheduled guard/API-stop actions target 20 November at 18:37 UTC. Viewer expiry provides another access cutoff. The original maximum is 20 November at 19:07:33 UTC and has not been extended.

The demo is limited to eligible free-plan credits and no Paid upgrade. Test/request counters and budget alerts are not hard lifetime spending caps. Actual credit consumption was not measured.

Access denial, API concurrency 0 and distribution disablement are distinct from resource deletion. Cleanup must retain diagnostics, remove owned resources and verify absence, including the intentionally retained guard IAM role. That final deletion remains pending while the bounded preview runs. Scheduler delivery and CloudFront propagation prevent an exact-second deletion guarantee.

## Source version

[Hosted provenance](HOSTED_RELEASE_PROVENANCE.json) identifies the tested image and source. The cleaned public source contains later comment/format/test-helper and frontend wording changes. The existing demo still runs the accepted earlier version; these cosmetic corrections have not been deployed. Inference logic and scientific artifacts remain unchanged. The deployed release and later source changes have separate version records.

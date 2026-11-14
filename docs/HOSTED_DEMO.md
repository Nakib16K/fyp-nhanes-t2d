# Protected hosted educational demo

Acceptance date: 14 November 2026. Scheduled operational stop: **20 November 2026 at 18:37 UTC**, or earlier for an eligibility/credit stop condition. The original maximum remains 19:07:33 UTC that day. This is a dated deployment record; a later reader must not infer that the preview is still available.

## Deployment and access

React assets are stored in private S3 and served through CloudFront. A viewer-request function checks a privately rendered credential hash and numeric UTC expiry before every page, asset and API path. It denies unrendered, malformed or expired configuration and removes viewer authorization before forwarding an allowed request. Access credentials and the rendered function are not published.

The FastAPI/Mangum container runs in Lambda behind an AWS_IAM Function URL. CloudFront origin access controls sign requests to the protected origins. The browser hashes the exact UTF-8 JSON POST/PUT body and sends `x-amz-content-sha256`; it has no AWS credentials and does not automatically retry a failed prediction. The hosted page and API use the same HTTPS domain. Local development retains the explicit loopback API default and CORS allowlist.

This is authenticated internet access, not VPC-private networking. No custom domain, provisioned concurrency, warmer or clinical service is claimed. Use synthetic examples. A source checkout does not supply the private model run, image, accounts, passwords, account-bound policies or deployment/cleanup orchestration.

## Actual acceptance

- The exact recorded repaired image completed a fresh ECR BASIC scan with zero findings before inference. This is point-in-time OS scanning, not exhaustive security clearance.
- Ten live viewer/direct-origin probes passed: missing/wrong viewer credentials denied; unsigned direct Lambda URL and S3 access denied. Runtime viewer checks also passed.
- An actual scheduled Lambda concurrency 1-to-0 rehearsal passed while the distribution was disabled, then its operational cutoff was restored. Nonmanual periodic guard delivery was observed before activation.
- All 28 synthetic reference cases passed through authenticated CloudFront HTTPS, followed by 11 browser application requests. The 39 controlled application attempts had concurrency 1 and no operator/client retry.
- Browser checks covered authentication, metrics, interpretation, global SHAP, three presets with predictions/local explanations and aligned SHAP headings/first labels/bars at wide and1100px widths. Live fault injection was not part of this acceptance; unavailable-API presentation has separate offline fixture evidence.

The first unprewarmed health request returned 200 after 91,018.681ms. Provider logs record an initial 10,000.12ms init-phase timeout, followed by 79,929.14ms handling for the same HTTP request. Cold starts can therefore keep a viewer waiting around90 seconds and remain a limitation. Joblib serial-mode fallback and LightGBM TreeExplainer output-shape warnings are retained. This small synthetic check does not establish p95/p99, clinical validity, future availability or comprehensive security/reliability.

## Bounded operation and cleanup

The recorded configuration reserves API concurrency 1 and uses a 120-second function allowance. A periodic guard checks eligible free-plan status/credit reserve and the lease; separate scheduled guard/API-stop actions target18:37UTC on20November. Viewer expiry provides another access cutoff. Acceptance was time/attempt bounded; that test counter is not a global lifetime traffic limit or hard spending cap.

Only eligible free-plan credits are permitted, with USD0 owner cash and no Paid upgrade. Actual credit consumption/invoice amount was not measured. These are project operating boundaries, not a guarantee that alerts or individual request counters enforce an exact spend ceiling.

Stopping access, setting API concurrency 0 and disabling the distribution are distinct from deleting resources. Scheduler timing and distribution propagation do not guarantee exact-second final deletion. Logs must be retained and owned resources removed/absence-verified; the owner-side finalizer also removes the intentionally retained guard IAM role. Final absence proof is pending while this preview is intentionally running. There is no automatic lease renewal.

## Source and runtime relationship

[HOSTED_RELEASE_PROVENANCE.json](HOSTED_RELEASE_PROVENANCE.json) records the exact image/config, parent lineage, runtime-source hashes and acceptance counts. Application, viewer and test content from the accepted 96-file selection is preserved. Two frontend files restore the original public LF line endings only; a focused production-build comparison checks this formatting correction. The rebuilt JavaScript and CSS match the accepted deployed bytes exactly; generated HTML differs only in line endings and an empty line left by script removal. This public reconciliation updates five existing documentation files and adds these demo notes plus hosted provenance; the original acceptance manifest remains a separate historical identity. All 18 inference-runtime source inputs match the retained image. The historical private image/provenance remain separate and unchanged.

The public viewer file is an unrendered fail-closed template. Public source excludes trained artifacts, raw respondent data, image layers, credentials, generated frontend files and account-specific raw receipts. Reference Docker recipes still need complete immutable inputs and new-image checks; they are not claimed to recreate the accepted patched image. The dissertation and academic/scientific limitations retain their separate recorded scope.

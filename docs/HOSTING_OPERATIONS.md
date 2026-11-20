# Hosting operations

The protected demo is for synthetic examples. The repository contains the application, Lambda adapter, viewer template and reference build inputs. Access credentials, AWS deployment controllers and the trusted model files are held privately. See [architecture](HOSTING_ARCHITECTURE.md) for the request and shutdown paths.

## Recorded release

On 18 November 2026, the corrected release passed 11 authenticated browser requests and 23 HTTPS reference cases. The checks covered local logistic regression explanations, both education nonresponse choices, model metrics, global SHAP and presets. The release reused a completed scan of the exact image and six earlier viewer tests after checking that the relevant inputs matched. It also checked access denials and a new scheduled watchdog event. [Release provenance](HOSTED_RELEASE_PROVENANCE.json) records the image, source and assets.

The first health request after the update took 103.502 seconds, and the dashboard was ready after 104.213 seconds. A later health request took 117 milliseconds. A separate same-day check returned all four models in 17.273 seconds. Logs showed an initial ten-second AWS initialization timeout before the first request succeeded. The samples show variable first-use delay, and the slow stages have yet to be measured individually. [AWS Lambda lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)

## Hosting limits

The 18 November configuration set the latest shutdown to **8 May 2027 at 00:00 UK time (7 May at 23:00 UTC)**. The watchdog checks every five minutes for an active AWS Free Plan, more than USD20 in eligible credits and at least 24 hours until plan expiry. Missing financial data, falling below those limits, an owner stop or another safety trigger can close the demo earlier. The Free Plan and eligible credits are the basis for USD0 owner cash. Paid upgrades and automatic renewals are outside the approved scope. [AWS Free Plan terms](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)

## Check an active release

Confirm the expected account, region, image and frontend asset identities. Check that the API is active, concurrency is one, the URL requires AWS IAM, and CloudFront has deployed the expected viewer and origin configuration.

Verify recent watchdog output for the expected lease identifier and expiry. A healthy event includes `FREE_PLAN_CHECK_PASSED` and `hosting_active: true`. Investigate absent or failed checks. Confirm that the viewer expiry, watchdog settings and both scheduled stops agree. Save the diagnostics needed for a review before logs expire.

## Update or restore the demo

1. Record the source, image digest and frontend assets. Check the existing controls and identify the currently accepted release to restore if this update fails.
2. Confirm Free Plan eligibility. Keep an earlier API stop armed during setup. Check the completed scan for the exact image and confirm that the viewer and unsigned direct origins deny access as expected.
3. Temporarily set API concurrency to zero and let active requests finish. Update the code and assets only if the Lambda revision and S3 object versions still match the recorded baseline.
4. Run the agreed browser and reference checks once. Record each request and any uncertain outcome. Stop inference if a required check fails. Automatic retries and prewarming are outside the acceptance procedure.
5. Check the published viewer and a fresh scheduled watchdog event. Update the independent API stop last, after the other checks pass.

On failure, save diagnostics and leave the API closed. Check the resource identities and restore the previous application, access and shutdown settings before reopening. An incomplete restore or unexpected resource state requires investigation.

## Shut down and verify cleanup

The watchdog sets API concurrency to zero, removes the Function URL and disables CloudFront before deleting resources. It may report `WAITING_FOR_DISABLED_DISTRIBUTION` while the CloudFront change is deploying. Cleanup continues after disablement reaches the deployed state.

Check resource identities and ownership before deletion. Remove the demo distribution, origin controls, viewer function, Lambda resources, ECR images and repository, S3 files and bucket, logs and schedules. Stop if ownership or the inventory differs from the recorded release.

The watchdog can report `APP_CLEANUP_ACKNOWLEDGED_GUARD_ROLE_REMAINS` after removing its function and logs. The owner checks the rest of the inventory for absence, verifies that the remaining role is unused and removes it. Sign off only after checking the full inventory again. Loss of access can precede removal of storage and other resources.

## Source review and merge

Review the proposed source against April `main`. Verify the commit, GitHub diff, test evidence, documentation links and exclusions for private files. PRs to `main` require resolved conversations and apply to administrators. Force pushes and deletion are blocked.

When the owner decides to merge, recheck the exact PR head and base and confirm that the accepted cloud release is running with the expected access, financial and shutdown controls. Refresh a stale health check with one authenticated request. Hold for investigation if it fails or returns an uncertain result. Reuse applicable prior tests for documentation and formatting changes.

Prefer a squash merge so the later changes read as one follow-up to the April submission. Verify the resulting `main` and the PR state afterwards. Source merge and an AWS release have separate approvals. The recorded financial and shutdown limits continue after merge.

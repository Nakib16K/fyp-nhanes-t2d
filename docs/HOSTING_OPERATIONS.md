# Hosting operations

Use synthetic examples in the protected demo. The repository contains the application, Lambda adapter, viewer template and reference build files. Credentials, deployment scripts and trained models are kept separately. See the [architecture guide](HOSTING_ARCHITECTURE.md) for how requests reach the API and how the demo shuts down.

## Recorded release

On 18 November 2026, the release passed 11 authenticated browser requests and 23 HTTPS reference cases. The checks covered local logistic regression explanations, both education nonresponse choices, model metrics, global SHAP and presets. The same image had already passed a scan, and the viewer still matched the inputs from six earlier tests. The release also tested denied requests and confirmed that the scheduled watchdog ran. The [release record](HOSTED_RELEASE_PROVENANCE.json) lists the image, source and assets.

## Startup and capacity

The first health request after the 18 November update took 103.5 seconds, and the dashboard was ready after 104.2 seconds. A later health request took 117 milliseconds. Separate health checks returned all four models in 17.3 seconds on 18 November and 25.2 seconds on 20 November. These are individual observations.

For the 103.5-second request, Lambda logged a ten-second initialization timeout before the invocation succeeded. AWS retries on-demand initialization within the function timeout. This release verifies the run and loads the four models before reporting healthy. The cloud logs do not isolate the time spent on each import or model load. [AWS Lambda lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)

On 20 November 2026, three pairs of direct Lambda requests compared the deployed image with a version that loads SHAP when an explanation is requested. The median first request fell from 16.8 to 10.6 seconds, and all 18 synthetic requests passed. The slowest first request on the candidate took 64.3 seconds, including a retry after Lambda hit its initialization timeout. The demo kept the deployed image because the candidate still had a slow start. The comparison measured Lambda directly. The browser timings above include CloudFront.

The demo uses on-demand capacity with one concurrent API request and shows a connecting message while the backend starts. Occasional use can require a fresh start and overlapping requests can be throttled. These trade-offs suit a small, access-controlled demo with a fixed hosting window. See the [hosting architecture](HOSTING_ARCHITECTURE.md#from-local-use-to-the-hosted-demo).

## Hosting limits

The 18 November configuration set the latest shutdown to **8 May 2027 at 00:00 UK time (7 May at 23:00 UTC)**. The watchdog checks every five minutes for an active AWS Free Plan, more than USD20 in eligible credits and at least 24 hours until plan expiry. Missing financial data, falling below those limits, an owner stop or another safety trigger can close the demo earlier. The Free Plan and eligible credits are the basis for USD0 owner cash. Paid upgrades and automatic renewals are outside the approved scope. [AWS Free Plan terms](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)

## Check an active release

Confirm the expected account, region, image and frontend asset identities. Check that the API is active, concurrency is one, the URL requires AWS IAM, and CloudFront has deployed the expected viewer and origin configuration.

Check that the watchdog has logged a recent result for the current demo expiry. A healthy event includes `FREE_PLAN_CHECK_PASSED` and `hosting_active: true`. Investigate missing or failed checks. Confirm that the viewer expiry, watchdog settings and both scheduled stops agree. Save the relevant logs before they expire.

## Update or restore the demo

1. Record the source, image digest and frontend assets. Check the existing controls and identify the currently accepted release to restore if this update fails.
2. Confirm Free Plan eligibility. Keep an earlier API stop armed during setup. Check the completed scan for the exact image and confirm that the viewer and unsigned direct origins deny access as expected.
3. Temporarily set API concurrency to zero and let active requests finish. Read the current Lambda revision ID and pass it with the code update. Use the saved S3 ETag when replacing the dashboard HTML. Write the new JavaScript asset only if its key is unused. If it already exists, check its ownership and hash before reusing it.
4. Run the agreed browser and reference checks once. Record each request and any uncertain outcome. Stop inference if a required check fails. Automatic retries and prewarming are outside the acceptance procedure.
5. Check the published viewer and a fresh scheduled watchdog event. Update the independent API stop last, after the other checks pass.

On failure, save diagnostics and leave the API closed. Check the resource identities and restore the previous application, access and shutdown settings before reopening. An incomplete restore or unexpected resource state requires investigation.

## Shut down and verify cleanup

The watchdog sets API concurrency to zero, removes the Function URL and disables CloudFront before deleting resources. It may report `WAITING_FOR_DISABLED_DISTRIBUTION` while the CloudFront change is deploying. Cleanup continues after disablement reaches the deployed state.

Check resource identities and ownership before deletion. Remove the demo distribution, origin controls, viewer function, Lambda resources, ECR images and repository, S3 files and bucket, logs and schedules. Stop if ownership or the inventory differs from the recorded release.

The watchdog can report `APP_CLEANUP_ACKNOWLEDGED_GUARD_ROLE_REMAINS` after removing its function and logs. The owner checks the rest of the inventory for absence, verifies that the remaining role is unused and removes it. Sign off only after checking the full inventory again. Loss of access can precede removal of storage and other resources.

## Source review and merge

Review the proposed source against April `main`. Verify the commit, GitHub diff, test evidence, documentation links and exclusions for private files. PRs to `main` require resolved conversations and apply to administrators. Force pushes and deletion are blocked.

Before merging, check the exact commits in the PR and on `main`. Check that the hosted release is running with the expected access, spending and shutdown controls. If the last health result is stale, send one authenticated health request. Investigate a failed or uncertain result before merging. Existing test results can cover documentation edits and formatting that leaves the code's behaviour intact.

Prefer a squash merge so the later changes read as one follow-up to the April submission. Verify the resulting `main` and the PR state afterwards. Source merge and an AWS release have separate approvals. The recorded financial and shutdown limits continue after merge.

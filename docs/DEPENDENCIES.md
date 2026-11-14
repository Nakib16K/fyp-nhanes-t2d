# Dependency and notice review

Dependency/notice review checkpoint: 13 November 2026. Hosted-runtime delta documented on 14 November 2026. See [DEPENDENCY_LICENSES.json](DEPENDENCY_LICENSES.json) for exact metadata and existing notice-file hashes.

## Frontend

The reviewed lock has 300 package entries, each with a recorded source/integrity value. A fresh isolated installation with lifecycle scripts disabled passed type/lint/build and produced the same production bytes as the earlier checked frontend. The actual check used Node 24.22.2 and npm 11.19.1 on Windows. No package version, package-lock or application logic was changed to obtain that result.

The point-in-time registry audit returned zero known findings across the full lock. This is not a guarantee against all vulnerabilities. Ninety-one lock records omitted a licence field; fresh/local metadata plus official exact-version registry records supplied the missing expressions, including 25 optional platform packages. A missing metadata field was not treated as proof of an incompatible licence.

[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) preserves the actual React, React DOM, Scheduler and Lucide licence texts from the fresh installation for the corresponding frontend code. Other dependencies retain their own terms; development dependencies and optional platform tools are not all automatically part of the browser bundle. The metadata index does not replace assessment of a changed bundle or distribution.

## Python/native runtime

All 49 installed Python distribution versions and 90 RPM names/versions matched the saved historical private-image inventory during read-only inspection. Installed licence/notice-file metadata was collected without executing application code or loading models. Official PyPI metadata was also inspected; LightGBM's installed metadata and [versioned upstream licence](https://github.com/lightgbm-org/LightGBM/blob/v4.7.0/LICENSE) resolve the registry-field omission.

The runtime includes multiple upstream terms and native/vendored components. Python/native binaries and container images are not distributed in this source candidate. Redistributing such artifacts needs a separate complete licence/NOTICE/source-obligation review; the metadata table is not blanket legal clearance. The source author's licence cannot relicense dependencies.

Forty-eight compatible backend wheels were downloaded and hash/metadata checked for proposed future-build inputs, with no active dependency-constraint errors. They were not installed. The set excludes the historical private runtime's older pip tool, whose restricted-trial advisory review is not a general build/public-hosting waiver. The later hosted integration image actually removed pip from its effective runtime while retaining all 48 other distribution versions; its inherited layers still contain historical installer bytes. A subsequent native repair updated only rpm, rpm-libs and sqlite-libs, retaining 90 RPM names. The exact hosted image passed a fresh ECR BASIC scan with no findings on 14 November; this remains a point-in-time OS check. The original private image is preserved. See [hosted provenance](HOSTED_RELEASE_PROVENANCE.json) for the lineage and remaining future-build requirements.

## Research requirements

The 17 direct requirements now use versions read from the current Windows research environment, with all 60 observed distributions recorded separately. This is a current metadata snapshot, not a certified historical training freeze, clean installation, transitive research hash lock or new fit. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

The npm check semantics are documented by [npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/) and [npm audit](https://docs.npmjs.com/cli/v11/commands/npm-audit/). Those commands and registry results answer package-installation/advisory questions; they do not validate medical/scientific claims or automatically approve publication.

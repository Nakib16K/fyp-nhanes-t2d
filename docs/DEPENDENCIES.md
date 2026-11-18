# Dependencies and notices

Dependency review:13 November 2026. Hosted image follow-up:14 November 2026.

## Frontend

The reviewed lock contains 300 package entries with source/integrity metadata. A clean Windows installation using Node 24.22.2 and npm 11.19.1, with lifecycle scripts disabled, passed type checking, lint and build. The npm audit reported no known findings at that checkpoint.

[DEPENDENCY_LICENSES.json](DEPENDENCY_LICENSES.json) records the licence metadata, including missing fields resolved from exact-version records. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) retains React, React DOM, Scheduler and Lucide notices. Dependencies keep their upstream terms; development and optional platform packages are not all part of the browser bundle.

## Python and native runtime

The historical private image contained 49 Python distributions and 90 RPM packages. Its installed metadata and licence files were inspected read-only, without importing the API or loading models. [RUNTIME_PROVENANCE.json](RUNTIME_PROVENANCE.json) preserves that inventory.

The later hosted image retains 48 non-pip distributions. Pip was removed from the effective runtime, although inherited layers still contain historical installer bytes. A separate vendor repair updated only rpm, rpm-libs and sqlite-libs while retaining 90 RPM names. The exact image completed a fresh ECR BASIC scan with no findings on 14 November. This point-in-time OS scan is not an exhaustive vulnerability assessment. See [hosted provenance](HOSTED_RELEASE_PROVENANCE.json) for the image lineage.

The 48-wheel Linux lock was downloaded and checked for archive/hash/metadata and dependency compatibility. It remains a proposed future-build input set; it has not been promoted through the reference Docker recipes. Future builds need reviewed immutable base, OS and installer inputs, then scan and parity checks. Image/binary redistribution also needs the relevant upstream notices and obligations.

## Research environment

The 17 direct research pins and 60-distribution snapshot describe the Windows environment observed on 13 November. They are not a historical training freeze or a complete transitive research lock. [Reproducibility](REPRODUCIBILITY.md) separates the research, private-runtime and hosted records.

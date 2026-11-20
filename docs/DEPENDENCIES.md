# Dependencies and licensing

The [ISC licence](../LICENSE) covers the author's source and original repository documentation, following the declaration in the April package metadata. The dissertation, university branding, model artifacts and datasets fall outside that licence. Upstream components keep their own terms. See the [frontend notices](THIRD_PARTY_NOTICES.md) and [reviewed dependency metadata](DEPENDENCY_LICENSES.json).

The frontend uses the versions listed in `frontend/package-lock.json`. A Windows setup with Node 24.22.2 and npm 11.19.1 passed type checking, lint and build after installation with lifecycle scripts disabled. The November audit describes the versions checked at that time.

Python has separate inputs for research, tests and deployment. The [research snapshot](RESEARCH_ENVIRONMENT_SNAPSHOT.json) records the observed Windows environment. The [private trial inventory](RUNTIME_PROVENANCE.json) records the earlier Lambda packages and native libraries. The [hosted provenance](HOSTED_RELEASE_PROVENANCE.json) records the later image and its validation. These snapshots describe different environments.

The repository contains source and build files. Before distributing a container or binary, check the upstream licence and source requirements. See [setup and rebuild limits](REPRODUCIBILITY.md).

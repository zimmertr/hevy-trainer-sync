# 0029. The repo carries CONTRIBUTING, NOTICES and a Makefile whose targets mirror CI, each in Docker

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ ("Create PR for adding contribuging, notes, makefiles, security, etc."), closing this repo's gaps against zimmertr/ai-config's `initialize-project` standards
- Issues and PRs: this PR, zimmertr/ai-config#1
- Cited in code as: none
- Guide: [`docs/DEVELOPMENT.md`](../DEVELOPMENT.md), Running the checks in Docker

## Context

`initialize-project` lists the files every repo carries and asks for every CI check to be a `make` target in Docker. Against that list, this repo had `LICENSE`, `.gitignore`, `README.md`, `SECURITY.md`, the issue templates and `CLAUDE.md`, but no `CONTRIBUTING.md`, `NOTICES.md` or Makefile.

## Decision

- `CONTRIBUTING.md`: how to send a change: the `make` targets, tests at 100%, the PR title, the owning docs page and a record, and no personal data.
- `NOTICES.md`: the services this talks to (Hevy, Garmin Connect, hevy2garmin) and the software bundled in the image, with each license, pointing to the release's SBOM attestation for the full list.
- `Makefile`: `test`, `test-one`, `build` and `scan`, each in Docker, each running what CI runs. Later CI checks add their own target.

## Evidence

- 2026-11-05: the licenses in `NOTICES.md` were read from the installed packages' metadata in `zimmertr/hevy-trainer-sync:0.1.4`: pip 26.2.2 (MIT), psycopg and psycopg-binary 3.2.9 (LGPL v3), tzdata 2025.2 (Apache 2.0), on Python 3.13. hevy2garmin's license (MIT) is from its repository.
- 2026-11-05: `make test` passed in Docker at 100%, and `make scan` built the image and found no fixable Critical or High.

## Alternatives rejected

- A `docker-compose.yml`: `initialize-project` asks for one to run a project with its backing services, but this tool's are hevy2garmin and its Postgres in the cluster, and a local run against the real account is discouraged (0006). Compose would have nothing to bring up.
- A `.claude/settings.json` setting `"attribution": false` for the repo: TJ's global settings already set it, and TJ chose to rely on them (2026-11-05: "We can assume my settings.json will follow me around for now."). It would only have reached cloud sessions and other contributors.

## Consequences

A new CI check isn't finished until it has a `make` target too. `NOTICES.md` names versions, so a dependency bump that changes a license needs the table updated; the SBOM attestation stays the complete list.

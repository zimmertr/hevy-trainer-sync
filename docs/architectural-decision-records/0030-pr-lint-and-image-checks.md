# 0030. Every PR is linted, and builds, scans and smoke-tests the image it would ship

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ ("Set up image build/scan on PRs, hadolint/linter in a new PR."), closing this repo's gaps against zimmertr/ai-config's `initialize-project` standards
- Issues and PRs: this PR, zimmertr/ai-config#1
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo; [`docs/CICD.md`](../CICD.md), Flow

## Context

A PR ran only `test` and `PR Title`. The image was first built, and first scanned, by the release after the merge, so a Dockerfile that didn't build or an image with a fixable High failed on main, where the fix is another release. Nothing linted the code.

## Decision

`pr.yml` adds two required checks, cut from Bluebird's `pr.yml`:

- `Lint`: ruff 0.16.0 under `ruff.toml`, which is Bluebird's rule set (`E`, `F`, `I`, `B`, `UP`, `BLE`, 120 columns) without its FastAPI import ban.
- `Docker Build`, in order:
  1. hadolint on the `Dockerfile`.
  2. A `linux/amd64` build, loaded on the runner and never pushed.
  3. Trivy under `trivy.yaml`, fixable only, posted as one sticky comment (skipped on Dependabot's PRs, whose token is read-only).
  4. A smoke test of the image: `--help` answers, psycopg loads, the zoneinfo data is there, and it runs as UID 1000.
  5. A failure on any fixable Critical or High, the rule the release enforces.

The code was brought under the linter in the same PR: 20 automatic fixes (`datetime.UTC`, import order) and 30 lines wrapped to 120 columns, with no change in behaviour. The Makefile gains `lint` and `lint-docker`.

## Evidence

- 2026-11-05, in Docker: hadolint 2.12.0 passed the `Dockerfile` unchanged. Ruff with this rule set found 48 issues, all `E501`, `UP017`, `I001` or `E401`. After the fixes `ruff check .` passes and `make test` still covers 100% of lines and branches.
- 2026-11-05: each smoke check printed its expected value against a local build: `usage: hevy-trainer-sync`, `True`, `America/Los_Angeles`, `1000`.

## Alternatives rejected

- `ruff format` over the whole codebase: it rewraps every file and buries the change. Only the statements over 120 columns were formatted.
- Ruff's own defaults: they leave out import sorting, bugbear and pyupgrade, and Bluebird runs the larger set.

## Consequences

A PR that breaks the image build, fails hadolint or ruff, or ships a fixable Critical or High can't merge. Each PR takes the image build's minute or two. The ruff version is pinned in `pr.yml` and the `Makefile`, where Dependabot doesn't look, so it moves by hand.

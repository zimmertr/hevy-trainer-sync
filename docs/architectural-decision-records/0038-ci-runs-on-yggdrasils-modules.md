# 0038. CI runs on yggdrasil's shared modules, pinned to a release commit

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ, in zimmertr/yggdrasil#5
- Issues and PRs: zimmertr/yggdrasil#5
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), "Working in this repo"

## Context

This repo's workflows were the source most of zimmertr/yggdrasil's modules were extracted from (zimmertr/yggdrasil#4). Keeping a copy here meant every fix landed twice, and the copies had already drifted from Bluebird's.

## Decision

- The PR title check, the PR image check, the Dependabot auto-merge, the weekly image scan and the release call yggdrasil's modules (`pr-title`, `docker-build`, `auto-merge`, `image-scan`, `release`), each pinned to a yggdrasil release's commit SHA with the version in a comment.
- What is this repo's own stays here: `test`, `Lint`, the smoke test (three commands in `pr.yml`), and the inputs and secrets each module takes.
- No `GitVersion.yml` or `trivy.yaml` here: the modules read yggdrasil's defaults, so a change to them reaches this repo with the next pin bump. `make scan` passes the default's one skip rule as a flag (TJ, 2026-11-06).
- Dependabot checks the pinned actions daily, and proposes a release only once it is three days old, as yggdrasil's record 0023 asks of every consumer.
- The switch is three PRs: PR checks, then auto-merge and the weekly scan, then the release.

## Evidence

- 2026-11-06: this repo's `GitVersion.yml` and `trivy.yaml` hold the same rules as yggdrasil's `defaults/`, so the modules judge titles and images as this repo did.

## Alternatives rejected

- Keeping this repo's own copies: every fix lands twice, and the copies drift.
- Keeping `trivy.yaml` for `make scan`: the CI gate would then read this repo's copy and miss a change to the default. A drifted flag in the Makefile misleads only a local scan.
- One PR for the whole switch: a failure would be hard to pin down, and so would the rollback.

## Consequences

- A module change reaches this repo only as a Dependabot PR that moves the pin, three days after its release.
- Two required checks are renamed, because a called workflow's check is named `<this job> / <module job>`: `PR Title / PR Title` and `Docker Build / Docker Build`.
- The PR title check no longer names the bump on the PR or warns on a major. It checks the type only.

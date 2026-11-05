# 0023. Every action is pinned to a commit, and the image carries an SBOM and provenance

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ (chose "Actions pinned to SHAs" and "SBOM + provenance" from Bluebird's release hardening)
- Issues and PRs: #32
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

The workflow named actions by moving major tags (`actions/checkout@v5`), so a tag moved upstream changed what ran with `DOCKERHUB_TOKEN` and `GH_PAT`. Bluebird pins every action to a commit (its decision 0100) and attaches build attestations to its images.

## Decision

Every `uses:` names a full commit SHA with its version in a comment, the same commits Bluebird runs. `.github/dependabot.yml` watches the `github-actions` ecosystem weekly and proposes each move as a `build(deps):` PR, which releases a patch. The GitVersion engine is pinned to `6.8.2` in `versionSpec`, which Dependabot does not see. Build & Push publishes the image with `provenance: mode=max` and `sbom: true`, for `linux/amd64` only.

## Evidence

No dated measurement.

## Alternatives rejected

- Bluebird's arm64 build: the cluster is amd64, and nothing here pulls the image on a Mac.
- Pinning the base image to a digest as well: not chosen this time. The `apt-get upgrade` layer of 0022 covers the security side.

## Consequences

Action updates arrive as PRs that need TJ's approval; there is no Dependabot auto-merge here. The pushed tag names an index holding the image and its attestations, which Docker Hub lists as an extra "unknown/unknown" platform.

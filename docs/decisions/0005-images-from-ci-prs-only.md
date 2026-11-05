# 0005. Images are built only by CI, and main changes only through PRs

- Status: Accepted. Its tag convention is superseded by 0021
- Date: 2026-11-04
- Decider: TJ
- Issues and PRs: #1
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

The repo was created by an agent through the GitHub API. TJ set the terms before the first line of code.

## Decision

Every change reaches main through a pull request that TJ approves. The image is built and pushed by `.github/workflows/image.yml` on a push to main, tagged with the commit, never by hand.

## Evidence

No dated measurement.

## Alternatives rejected

- Building and pushing the image from a workstation, as the hevy2garmin dashboard image still is (see the Kubernetes-Manifests README): no record of what went into it.

## Consequences

The workflow needs `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` as repository secrets, which TJ set on 2026-11-04.

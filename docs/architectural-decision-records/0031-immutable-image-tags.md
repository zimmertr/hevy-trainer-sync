# 0031. Image tags on Docker Hub are immutable

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ ("Turn on immutability."), set in Docker Hub's settings on 2026-11-05
- Issues and PRs: this PR
- Cited in code as: none
- Guide: [`docs/CICD.md`](../CICD.md), Systems

## Context

The GitHub releases were already immutable (0021), but anyone with push rights to `zimmertr/hevy-trainer-sync` could overwrite a version tag, so the image the manifests pin could change under them without a new release.

## Decision

Docker Hub's immutable tags are on for the repository, with the rule `.*`: every tag, once pushed, can't be overwritten or deleted. The setting lives in Docker Hub, not in this repo.

## Evidence

- 2026-11-05: the release pushes one tag, the version, and only when the image for it is missing (`release.yml`'s Determine Version), so no run ever pushes a tag twice. The PR build is loaded on the runner and never pushed.
- 2026-11-05: the token in the maintainer's secrets was refused by Docker Hub's API (401 on login), so TJ turned it on.

## Alternatives rejected

- A narrower rule, such as `^[0-9]+\.[0-9]+\.[0-9]+$`: it would leave the pre-0.1.0 SHA tags mutable, and no tag here should ever move.

## Consequences

A release can never be fixed by re-pushing its version; it is fixed forward with a new one, which the pipeline already required. A bad tag stays on Docker Hub for good. The setting isn't in git, so a new registry repository needs it set again by hand.

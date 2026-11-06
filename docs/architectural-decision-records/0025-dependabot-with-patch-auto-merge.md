# 0025. Dependabot watches pip, Docker and Actions, and patch updates merge themselves

- Status: Accepted. Narrows the approval rule of 0005; minor updates were added to the self-merge by [0037](0037-minor-updates-merge-themselves.md)
- Date: 2026-11-05
- Decider: TJ ("dependabot scanning for the repo ... Just like Bluebird", then "Yes, like Bluebird" to auto-merging patch updates, and to using the PAT in `secrets.json` as `AUTO_MERGE_PAT`)
- Issues and PRs: #35
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

Dependabot watched only the pinned actions (0023). Nothing proposed updates to `requirements.txt` or the base image, and GitHub's Dependabot alerts and security updates were off.

## Decision

- **Alerts and security updates** are on for the repo.
- **Version updates**, weekly, for pip (both requirements files, with a seven-day cooldown), GitHub Actions and Docker. Every title is `build(deps):` or `build(deps-dev):`, which releases a patch.
- **The base image is pinned as tag@digest**, so an upstream rebuild of `python:3.13-slim` arrives as a PR.
- **Patch-level version updates merge themselves.** `dependabot-auto-merge.yml` arms squash auto-merge when Dependabot's metadata says `version-update:semver-patch`, and comments on the PR to say so. GitHub merges once `test` and `PR Title` pass and every conversation is resolved, and the merge releases and deploys. Minor, major and digest-only updates wait for TJ.
- The merge uses the `AUTO_MERGE_PAT` Dependabot secret, because a merge made with `GITHUB_TOKEN` does not start `release.yml`. It holds TJ's personal fine-grained PAT, which has admin on this repo.

## Evidence

No dated measurement. The workflow is Bluebird's, which has run since 2026-07-24 (when its `AUTO_MERGE_PAT` was set).

## Alternatives rejected

- Every Dependabot PR waits for TJ, as 0005 had it: TJ chose Bluebird's behaviour.
- A PAT scoped to this repo alone: recommended, and declined in favour of the existing token. A leak of the secret exposes whatever that token reaches.

## Consequences

A patch release of a dependency can reach the cluster that drives TJ's Hevy and Garmin accounts without anyone reading it. The seven-day pip cooldown and the release scan (0022) are the guards. Rotating TJ's PAT means setting `AUTO_MERGE_PAT` again, or auto-merge stops (the PRs then wait, nothing breaks). Copilot comments must be resolved before a self-merge can complete (0024).

# 0024. Main is protected the way Bluebird's is, and Copilot reviews every PR

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ ("Set up branch protection, dependabot scanning for the repo, and github security scanning. Just like Bluebird."), and, the same day, the Copilot review ruleset
- Issues and PRs: #35
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

Main had no protection. The rule that every change goes through a PR (0005) was kept by habit, and the `PR Title` check from 0021 could fail without stopping a merge.

## Decision

Classic branch protection on `main`, with Bluebird's settings:

- A pull request is required, with 0 approving reviews. Stale reviews are dismissed on a new push.
- `test` and `PR Title` must pass. The branch need not be up to date (`strict: false`).
- Every conversation must be resolved before merging.
- No force-push and no deletion.
- Admins are held to all of it.

A ruleset, "Copilot review for default branch", asks Copilot to review every PR, drafts included, and also blocks deleting or force-pushing main.

## Evidence

Bluebird's settings, read through the API on 2026-11-05: the same values as above, with its own nine CI jobs as the required checks, and ruleset 19701460 with the same three rules.

## Alternatives rejected

- Requiring one approval: TJ is the only reviewer, and Dependabot's patch updates merge themselves (0025). Bluebird requires none either.
- `strict: true`: every merge would force the next open PR to update and rerun before merging, for no gain on a repo this size.

## Consequences

Nobody can push to main, TJ included; the release workflow only pushes tags, which this does not cover. A Copilot comment blocks the merge until it is resolved, which also holds up a self-merging Dependabot PR. Renaming the `test` job or the `PR Title` job means updating the required checks in the same change.

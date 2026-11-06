# 0024. Main is protected the way Bluebird's is, with Bluebird's Copilot review ruleset

- Status: Accepted; its Copilot review ruleset is removed by [0033](0033-no-copilot-review-ruleset.md)
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

- Bluebird's settings, read through the API on 2026-11-05: the same values as above, with its own nine CI jobs as the required checks, and ruleset 19701460 with the same three rules.
- 2026-11-05: the ruleset requested no Copilot review on #35, a draft, in the first ten minutes. On Bluebird, none of the six latest non-Dependabot PRs (#841 to #851) has a Copilot review either; the only review among them is `github-advanced-security[bot]` on #845. The rule is in force but has produced no reviews on either repo, likely because Copilot code review is not available on the account. Not confirmed.

## Alternatives rejected

- Requiring one approval: TJ is the only reviewer, and Dependabot's patch updates merge themselves (0025). Bluebird requires none either.
- `strict: true`: every merge would force the next open PR to update and rerun before merging, for no gain on a repo this size.

## Consequences

Nobody can push to main, TJ included; the release workflow only pushes tags, which this does not cover. If Copilot does start reviewing, its comments block the merge until resolved, self-merging Dependabot PRs included. Renaming the `test` job or the `PR Title` job means updating the required checks in the same change.

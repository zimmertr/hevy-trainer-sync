# 0037. Dependabot's minor updates merge themselves too

- Status: Accepted. Amends [0025](0025-dependabot-with-patch-auto-merge.md)
- Date: 2026-11-05
- Decider: TJ, 2026-11-05: "I thought we were setting a standard to auto merge patch and minor updates?", asked about #36 and #37 waiting
- Issues and PRs: this PR, #36, #37
- Cited in code as: decision record 0037, in `dependabot-auto-merge.yml` and `.github/dependabot.yml`
- Guide: [`docs/CICD.md`](../CICD.md), Dependabot

## Context

0025 copied Bluebird's auto-merge when it armed only patch updates. Bluebird then widened it to minor updates (its record 0273), and zimmertr/ai-config's `initialize-project` standard sets patch and minor as the baseline. This repo kept the patch-only rule, so #37 (psycopg 3.2.9 to 3.3.6) waited for TJ when the standard says it should not.

## Decision

`dependabot-auto-merge.yml` arms squash auto-merge when Dependabot's metadata says `version-update:semver-patch` or `version-update:semver-minor`, with the same condition Bluebird uses. Major and digest-only updates still wait for TJ. Everything else in 0025 stands: the `AUTO_MERGE_PAT` merge, the seven-day pip cooldown, and the checks a merge waits for.

## Evidence

- 2026-11-05: #37's `Auto-merge patch updates` job passed without arming auto-merge, because its update type was `version-update:semver-minor`.
- 2026-11-05: Bluebird's `dependabot-auto-merge.yml` arms both types, with the condition copied here.

## Alternatives rejected

- Keeping patch only: TJ's standard is patch and minor.
- Adding majors: a major can break the API this code calls, and the tests mock the network, so CI would not catch it.

## Consequences

A minor release of a dependency can now reach the cluster without anyone reading it. The guards are the same as for patches: the pip cooldown, the tests and the release scan (0022). Dependabot reads a calendar-versioned package's year change as a major, so tzdata 2025.2 to 2026.6 (#36) still waits for TJ.

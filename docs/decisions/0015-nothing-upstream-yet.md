# 0015. Nothing goes upstream to hevy2garmin until this tool has been polished and tested

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ ("No issue or PR for now. We need to develop and polish this first. And also test it")
- Issues and PRs: #13
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Rules, the upstream bullet

## Context

Send to Device and an in-place workout update would help every hevy2garmin user, and upstreaming them would remove this job's reads of hevy2garmin's database. hevy2garmin is MIT-licensed TypeScript, merges outside PRs within a day (upstream #774 and #751 in the week before), and is run by most of its users as a fork.

## Decision

No issue, PR or fork on drkostas/hevy2garmin for now, and no rebuild of hevy2garmin from scratch. The features stay here until they have run through real sessions.

## Evidence

No dated measurement. The tool had its first end-to-end run on 2026-11-05.

## Alternatives rejected

- Upstream now: the features had not been through one real workout.
- A diverging fork: every upstream fix would have to be merged by hand.
- A rebuild: would mean owning Garmin login, activity matching and FIT merging, which upstream fixes weekly (for example upstream #748 and #774).

## Consequences

The coupling in #13 stays until this is revisited. Posting anything on hevy2garmin needs TJ's go-ahead, since it is public.

# 0014. The mirrored routines stay in Hevy after they reach Garmin

- Status: Accepted
- Date: 2026-11-05
- Decider: none needed: forced by hevy2garmin's design and Hevy's API. TJ asked whether they could go and accepted the answer.
- Issues and PRs: #11
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), How it fits together

## Context

TJ noticed the `Upper W8` and `Lower W8` routines in Hevy and asked whether they could be removed once copied to Garmin.

## Decision

They stay. hevy2garmin keys each Garmin workout on the Hevy routine's id (`synced_routines.hevy_routine_id`) and re-reads the routine on every sync to detect changes.

## Evidence

- 2026-11-05: read in hevy2garmin's `web/lib/garmin-routine-sync.ts`. Hevy's public API has no routine delete.

## Alternatives rejected

- Delete after sync: the next run would create a routine with a new id, hevy2garmin would treat it as a new workout, and the old Garmin workout would be left behind. Deleting would also need the private API.

## Consequences

The folder `Hevy Trainer` holds one routine per template. Training still starts from Trainer on the phone. Retired templates leave routines behind (#11).

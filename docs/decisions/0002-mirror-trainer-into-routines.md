# 0002. Trainer's program is mirrored into Hevy routines that hevy2garmin carries to the watch

- Status: Accepted
- Date: 2026-11-04
- Decider: TJ ("Yes, build C")
- Issues and PRs: #1, KM#1818
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), How it fits together

## Context

The watch only names exercises when it runs a planned workout. hevy2garmin turns Hevy routines into Garmin planned workouts, but Hevy Trainer never creates routines, and the Trainer screens have no "save as routine" option (checked on 2026-11-04 from TJ's screenshots).

## Decision

This tool reads the Trainer program from Hevy's private API and writes one routine per template into the folder `Hevy Trainer` through the public API. hevy2garmin then syncs those routines to Garmin like any other.

## Evidence

- 2026-11-04: the private endpoint `GET /hevy_trainer/v3/program` returned two templates (`upper_2x_a`, `lower_2x_a`) with exercises, set counts, warm-up counts, rep ranges and rest, and no weights.
- 2026-11-05: `Upper W8` and `Lower W8` synced to Garmin and reached the watch.

## Alternatives rejected

- Keep the phone's Bluetooth off until hevy2garmin has merged, so Garmin forwards only the merged activity. TJ: possible, but not seamless or automatic.
- Delete and re-upload on Strava after the merge. Strava has no delete API.
- Copy routines from the last logged session with the public API only. Needs no private API, but the routine is a session behind Trainer's plan.

## Consequences

The tool depends on an undocumented endpoint and a pasted login (#9). The routines are a copy for the watch, so edits made to them in Hevy are overwritten on the next run.

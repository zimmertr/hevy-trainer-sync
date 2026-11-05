# 0016. Garmin's own Strava connection stays on

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ ("No, not yet")
- Issues and PRs: #26
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), How it fits together, the Strava bullet

## Context

TJ wants a session on Strava complete the moment it is posted. Garmin forwards the watch's activity to Strava within seconds of the phone sync, and hevy2garmin can only merge into that activity after it exists in Garmin. So the first Strava post is always the watch's version, and the merged sets land on it later.

## Decision

Garmin keeps forwarding activities to Strava. This tool does not upload to Strava. The gap is narrowed instead by merging sooner after the workout.

## Evidence

- 2026-11-05: Strava activities from October show Hevy's weights that were merged weeks after posting, so merged sets do reach an existing Strava activity.

## Alternatives rejected

- Turn off Garmin's Strava link and upload the merged file from this tool, rejected for now: the only way to make the first post complete, but every other activity (runs included) would then need forwarding too, and it needs a Strava API app with write access.

## Consequences

For the first minutes after a session, Strava shows the watch's sets. With a planned workout those carry the planned exercises, reps and weights. #26 holds the decision open until a few sessions show how far off the first post is.

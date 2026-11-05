# 0001. hevy2garmin merges Hevy's sets into the watch's own activity

- Status: Accepted
- Date: 2026-11-04
- Decider: TJ, in the hevy2garmin dashboard's Settings
- Issues and PRs: #25 (the Unknown names); KM#1809 deployed the dashboard
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), How it fits together, the merge bullet

## Context

The watch records heart rate, calories and time but guesses the exercises. Hevy records the exercises, sets and weights but has no heart rate. One accurate activity on Strava needs both halves in one place. hevy2garmin had been deployed with merging off and a sync window that started on the day it was installed, so none of the past workouts had merged.

## Decision

hevy2garmin's watch strategy is `merge` (Enhance on in Settings) and its sync window starts in September 2026. hevy2garmin pushes Hevy's sets into the Garmin activity the watch recorded and keeps that activity, so the watch's own metrics survive.

## Evidence

- 2026-11-04: with the start date moved to September and Enhance on, hevy2garmin merged the 13 Hevy workouts into Garmin Connect.
- 2026-11-05: three Strava activities from 23 Oct, 27 Oct and 3 Nov carry Hevy's weights (for example 45.1 lb, which is Hevy's 20.4 kg), so the merged sets reached Strava. Most exercise names read "Unknown". hevy2garmin documents that Garmin will not show exercise names written into a device-recorded activity (upstream #325).

## Alternatives rejected

- `replace`: uploads a named activity and deletes the watch's. Real exercise names, but the watch-only metrics are lost.
- `describe`: writes a description and no sets.
- Deleting the Strava activity and uploading a corrected one: Strava's API has had no delete endpoint since 17 Jan 2017.

## Consequences

Exercise names on Strava stay "Unknown" for merged sets unless the watch recorded them from a planned workout, which is unverified (#25). That gap is why [0002](0002-mirror-trainer-into-routines.md) exists. The setting lives in hevy2garmin's database, not in any manifest, so nothing in git holds it.

# 0019. A poller inside the cluster checks Hevy every 60 seconds and starts hevy2garmin's merge at once

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ ("I would consider a cloudflare tunnel, but would prefer not to expose anything and just poll every 60s")
- Issues and PRs: #23, #24 (the late-sync duplicate), KM#1839
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), How it fits together, the poller bullet

## Context

TJ posts to Strava straight after a session. hevy2garmin's scheduled sync holds every workout for two hours after it ends, so the watch's activity can reach Garmin first, and only then merges. For those two hours Strava shows the watch's version of the sets ([0016](0016-garmin-keeps-posting-to-strava.md)). A 60-second cron alone would not help, because the two-hour hold is the bottleneck, not the 15-minute schedule.

hevy2garmin already has a faster path: its Hevy webhook route, `POST /api/cron/webhook`. On a self-hosted server it answers at once, then tries a merge-only sync every few minutes and uploads a fresh activity only on its last attempt. Hevy calls that route from the internet, which would mean exposing the dashboard.

## Decision

`python -m hevy_trainer_sync poll` runs as Deployment `hevy-trainer-poll`. Every `POLL_SECONDS` (60) it reads the public API's `GET /v1/workouts/events?since=`. For each workout saved or edited since the last mark, it calls `POST http://hevy2garmin/api/cron/webhook` from inside the cluster with `CRON_SECRET`. It needs no Hevy session and no volume.

hevy2garmin's staged sync is tuned in its Deployment: first attempt after 60 seconds (`WEBHOOK_DELAY_SECONDS`), then every 180 (`WEBHOOK_RETRY_INTERVAL_SECONDS`), 10 attempts (`WEBHOOK_MAX_ATTEMPTS`, the most it allows). The fresh-upload fallback therefore comes about 28 minutes after the save, against 25 with upstream's defaults.

## Evidence

- 2026-11-05: `GET /v1/workouts/events` returned TJ's 3 Nov Lower session as an `updated` event carrying the whole workout and its `updated_at`.
- 2026-11-05: the hevy2garmin commit deployed (`f0f6755`) has the staged merge-only webhook path (`web/lib/webhook-retry.ts`) and reads the three `WEBHOOK_*` variables.
- The merge skips the two-hour hold on merge-only attempts (`respectGrace && !mergeOnly` in `typescript/src/sync/sync-one.ts`).

## Alternatives rejected

- Hevy's webhook through a Cloudflare Tunnel: TJ would consider it, but prefers to expose nothing.
- A 60-second cron calling `/api/cron/sync`: still waits out the two-hour hold.
- Polling inside the hourly mirror: the mirror owns the RWO session volume and runs for seconds an hour. A long-running loop holding that volume would block the CronJob.
- Polling Garmin every minute for the watch's activity: Garmin rate-limits accounts, and hevy2garmin's staged attempts already do that check a few times per workout.

## Consequences

- Garmin Connect shows the merged sets a few minutes after the watch syncs, instead of two hours later.
- Corrected 2026-11-05: this record first said Strava would show the merged sets too. It does not; Strava keeps the watch's first post ([0020](0020-the-watch-recording-is-what-strava-keeps.md)). The poller still keeps Garmin Connect current.
- If the watch syncs more than about 28 minutes after the workout is saved in Hevy, the last attempt uploads a fresh activity and the watch's own copy arrives later as a second one. That is upstream's trade-off with a slightly longer window, and the scheduled sync had the same failure at two hours. #24 tracks widening it.
- Hevy sees 1,440 small event reads a day. A restart loses at most the poll in flight; the poller starts one interval back, and hevy2garmin's scheduled sync still catches anything missed after two hours.
- The routine for the next session still waits for the hourly mirror ([0007](0007-hourly-cronjob.md)).
- `test_poll.py` covers the event filter, the high-water mark and the retry-on-failure behaviour.

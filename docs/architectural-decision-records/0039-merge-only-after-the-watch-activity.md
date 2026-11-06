# 0039. The poller asks hevy2garmin to merge only once the watch's activity is on Garmin, and nothing is ever uploaded

- Status: Accepted. Supersedes 0019's call on every save and its webhook timings
- Date: 2026-11-06
- Decider: TJ ("Just make it so this is seamless and easy to use and \"just works\" without dumb manual steps", and on a session the watch never recorded: "Never upload". "Only garmin will ever upload to Strava. Not Hevy.")
- Issues and PRs: #24, #51, KM PR to follow
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), How it fits together, the poller bullet

## Context

Under [0019](0019-poll-hevy-every-minute.md) the poller called hevy2garmin's webhook route as soon as a workout was saved. The route tries a merge-only sync every three minutes, and its tenth and last attempt, about 28 minutes after the save, uploads a fresh activity when no watch recording has turned up. Garmin posts that upload to Strava. When the watch synced late, its own activity then arrived as a second one, so Strava showed the session twice. The scheduled `hevy2garmin-sync` CronJob did the same two hours after the workout ended. The Friday checklist asked TJ to open Garmin Connect within five minutes of finishing to beat that deadline. TJ rejected any step like that.

## Decision

- hevy2garmin is never asked to sync a workout whose watch activity Garmin does not have yet. The poller holds each saved workout, and every poll it looks on Garmin for that workout's watch recording. It reads the activity list with hevy2garmin's token, borrowed read-only as in [0009](0009-send-to-device-from-here.md). It matches with a port of hevy2garmin's own matcher (`match.py`, from `findMergeMatch`) and the merge settings the dashboard saved. Only then does it call the webhook route, and the route's first attempt merges.
- The route takes no workout id and syncs the newest workout hevy2garmin has not finished. So the poller only ever asks about the newest workout still waiting. An older one waits until the newer one is merged or given up.
- The poller stops waiting on a workout once `synced_workouts` has it. A workout the watch never recorded is given up after 48 hours and stays in Hevy only. Nothing from Hevy alone ever reaches Garmin or Strava.
- If the dashboard's merge is off, or its watch strategy is anything but `merge`, the poller logs an error and asks nothing, because hevy2garmin would then upload.
- `hevy2garmin-sync` is suspended. `WEBHOOK_DELAY_SECONDS` drops to 0, since the activity is already there when the route is called.

## Evidence

- 2026-11-06, hevy2garmin source as deployed: `runStagedSync` (`web/lib/webhook-retry.ts`) passes `mergeOnly: false` on its last attempt, and no setting turns that off. The scheduled route calls `syncOneWorkout` with `respectGrace: true` and the grace period is a constant, 120 minutes (`typescript/src/sync/grace.ts`).
- Same source: with merge on, an attempt that finds the watch activity merges into it whether or not it is merge-only. `mergeOnly` changes only what happens when no activity is found (`typescript/src/sync/types.ts`, the `mergeOnly` comment).
- Same source: the webhook route reads nothing from the request (`web/app/api/cron/webhook/route.ts`) and the engine takes the first unsynced workout of Hevy's list (`syncOneWorkout`, `candidates[0]`). On 2026-11-06 Hevy's `GET /v1/workouts` listed TJ's workouts newest first.

## Alternatives rejected

- Opening Garmin Connect within five minutes of a session: a manual step, which TJ rejected.
- Stretching the webhook's retry window: every window ends in an upload, so it only makes a duplicate rarer.
- Uploading a session the watch missed, after six or 24 hours: TJ chose never to upload. Only Garmin posts to Strava.
- Changing hevy2garmin to merge only: that needs a fork or an upstream change, and [0015](0015-nothing-upstream-yet.md) holds both back.
- 0019 rejected polling Garmin every minute because of Garmin's rate limits. The poller now reads Garmin once a minute, but only while a workout is waiting, which is usually a few minutes after each session.

## Consequences

- No manual step after a session. Strava gets the watch's post and nothing else; Garmin Connect shows the merged sets on the first poll after the watch syncs, however late that is.
- The poller now needs `DATABASE_URL` and `H2G_PASSWORD`. A 401 from Garmin is handled the way Send to Device handles it.
- The match rules are copied, not shared. If hevy2garmin changes its matcher, `match.py` has to follow, or a workout ours matches and theirs does not would end in the route's upload about 28 minutes later.
- A workout the watch missed stays unsynced in hevy2garmin. The dashboard's Sync Now would upload it, so it must not be pressed.
- Waiting workouts live in the pod's memory. A restart reads 48 hours of Hevy events again, and the ones hevy2garmin already has drop out on the first poll.
- `test_match.py` holds the matcher's rules; `test_poll.py` holds the waiting, the newest-first rule, the give-up and the token refresh.

# Traffic: what the job calls, and how often

Nothing calls this tool. [CICD.md](CICD.md) covers how it gets deployed. This page lists every outbound call a run makes, so the load it puts on Hevy, hevy2garmin and Garmin is visible in one place. All of it leaves from the cluster, through TJ's home connection.

## Per run

| # | Call | When | Count |
|---|---|---|---|
| 1 | Hevy private `POST /auth/refresh_token` | When the stored `expires_at` has passed, which is almost every hourly run since the token lasts about 30 minutes, or when step 2 answers 401 | 0 to 2 |
| 2 | Hevy private `GET /hevy_trainer/v3/program` | Every run (again after a refresh) | 1 or 2 |
| 3 | Hevy public `GET /v1/workouts` | Every run, until every exercise has a weight or `WORKOUT_PAGES` runs out | 1 to 4 |
| 4 | Hevy public `GET /v1/routine_folders` | Every run | 1 or more pages |
| 5 | Hevy public `POST /v1/routine_folders` | Only when the folder is missing | 0 or 1 |
| 6 | Hevy public `GET /v1/routines` | Every run | 1 or more pages |
| 7 | Hevy public `POST /v1/routines` or `PUT /v1/routines/{id}` | Per template that changed | 0 to one per template |
| 8 | hevy2garmin `POST /api/login`, `POST /api/routines/sync` | Only when a routine changed, or `--force` | 0 or 2 |
| 9 | Postgres, two `SELECT`s | Only when step 8 ran and `DATABASE_URL` is set | 0 or 2 |
| 10 | Garmin `GET /device-service/deviceservice/mylastused` | Same as 9, unless `GARMIN_DEVICE_ID` is set | 0 or 1 |
| 11 | Garmin `POST /device-service/devicemessage/messages` | Per changed routine | 0 to one per template |
| 12 | hevy2garmin `POST /api/routines/sync` with no ids | Only when Garmin answers 401 at step 10 | 0 or 1 |

A run with nothing to do makes about six Hevy calls and nothing else. hevy2garmin then makes its own Garmin calls for step 8; see its source.

## The poller

| Call | When | Count |
|---|---|---|
| Hevy public `GET /v1/workouts/events?since=` | Every `POLL_SECONDS` | 1 per minute, more pages only when more than ten events arrive at once |
| Postgres, one `SELECT` on `synced_workouts` | Every poll while a workout is waiting | Usually a few minutes after each session |
| Postgres, `SELECT`s on `app_cache` and `platform_credentials` | Every poll while the newest waiting workout has no watch activity yet | Same |
| Garmin `GET /activitylist-service/activities/search/activities` | Same | 1 per minute until the watch syncs, then none |
| hevy2garmin `POST /api/cron/webhook` | Once the watch activity is found | One a session, again after 30 minutes only if the merge never landed |
| hevy2garmin `POST /api/login`, `POST /api/routines/sync` with no ids | Only when Garmin answers 401 | 0 or 2 |

hevy2garmin's first attempt after the webhook call finds the same activity, merges and stops. A workout the watch never recorded costs one Garmin list a minute for 48 hours, then nothing.

## Per day

The poller makes 1,440 event reads a day, plus a Garmin activity list a minute for the few minutes between Finish in Hevy and the watch's sync. The CronJob runs 24 times a day. In a week with two workouts and one Monday rename, Garmin sees roughly six device messages and six last-used lookups from this tool, and hevy2garmin makes its own calls to rebuild those workouts.

## Identity and caching

Every call names this tool in its `User-Agent` (`http.USER_AGENT`), except Garmin's, which carry the Android app's headers. Nothing caches a response: a run makes about six Hevy calls an hour and the poller one a minute, each asking for what changed since the last. Record: [0035](architectural-decision-records/0035-a-polite-client.md).

## Timeouts and retries

HTTP calls time out after 30 seconds (`http.request`), except the dashboard: 300 seconds for a routine sync, which waits on Garmin, and 120 for schedule and unschedule. Postgres connections time out after 10 seconds. A `429` with a `Retry-After` of at most 60 seconds is waited out and retried once (`http.MAX_RETRY_AFTER_S`); a longer wait, a missing header, or a second `429` fails the call. Nothing else is retried except the program call after a Hevy refresh on a 401 and the one Garmin token refresh above. Record: [0035](architectural-decision-records/0035-a-polite-client.md). The poller does not retry within a poll either. A failed Hevy read leaves the mark where it was, and any other failed call leaves the workout waiting, so the next poll asks again. A failed run waits for the next hour; `backoffLimit: 0` keeps Kubernetes from retrying a run that might have half-written routines.

## Inbound

None. Neither pod has a Service or listens on anything. Hevy's webhook would need hevy2garmin reachable from the internet; the poller exists so it does not have to be (records [0019](architectural-decision-records/0019-poll-hevy-every-minute.md), [0039](architectural-decision-records/0039-merge-only-after-the-watch-activity.md)).

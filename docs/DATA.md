# Data sources

What each source can and cannot tell this tool, and every quirk found so far. Each finding carries the date it was observed. When a source surprises you, add the finding here in the same PR as the fix.

| Source | Documented | Auth | Used for |
|---|---|---|---|
| Hevy private API, `api.hevyapp.com` | No | `x-api-key: shelobs_hevy_web` plus a bearer from the hevy.com cookie | The Trainer program, session refresh |
| Hevy public API, `api.hevyapp.com/v1` | [Yes](https://api.hevyapp.com/docs) | `api-key` header (Hevy Pro) | Folders, routines, recent workouts |
| hevy2garmin dashboard | Its source | Session cookie from `POST /api/login` | Turning routines into Garmin workouts |
| hevy2garmin Postgres | Its source | CNPG `uri` | Garmin workout ids and Garmin's token, read-only |
| Garmin Connect, `connectapi.garmin.com` | No | Bearer DI token borrowed from hevy2garmin, Android app headers | Last-used device, Send to Device |

## Terms and limits

What each provider says about how it may be called, read on 2026-11-05.

- **Hevy public API:** no published rate limit. The docs ask that a job updating hourly or daily not send its requests exactly at xx:00 but at a random minute instead, and warn the API may change or be abandoned. The CronJob runs at minute 7. The poller reads the events once a minute, which that request, about hourly and daily jobs, doesn't speak to. Hevy Pro only.
- **Hevy private API:** undocumented, so no published terms or limits. Used for two calls a run, as the web app makes them.
- **Garmin Connect:** undocumented, with no published terms for this API. Called only after a routine changed.
- **hevy2garmin:** TJ's own deployment. Its webhook route throttles past `WEBHOOK_MAX_INFLIGHT` (see below).

## Hevy Trainer program (private)

`GET /hevy_trainer/v3/program?client_program_updated_at=1970-01-01T00:00:00.000Z&client_next_workout_updated_at=1970-01-01T00:00:00.000Z`, as catalogued by [hevy-mcp-unofficial](https://github.com/LovelessCodes/hevy-mcp-unofficial).

- **What it has** (2026-11-04): `id`, `created_at`, `current_week`, `next_workout_index`, `program_variety`, `exercises_rotated_at`, `edits`, and `templates[]`. Each template has a `key` such as `upper_2x_a` and `exercises[]` with `index`, `exercise_template_id` (the public API's template id), `set_count`, `warmup_set_count`, `rep_range {start, end}` and `rest_seconds`.
- **What it lacks**: weights, and any display title. The title comes from the key: the words before the frequency token (`upper_2x_a` is "Upper").
- **`current_week` is not the app's week** (2026-11-04): it read 5 when the app showed cycle 2, week 2 of a 6-week cycle. Calendar weeks since `created_at` gave 8, which matched. Record: [0010](architectural-decision-records/0010-program-week-in-names.md). Issue #14 tracks whether that holds.
- **`exercises_rotated_at`** read Thursday 29 Oct, so rotations do not fall on week boundaries.

## Hevy session (private)

- Tokens come from the hevy.com `auth2.0-token` cookie, a URL-encoded JSON object with `access_token`, `refresh_token` and `expires_at`. The access token lasts about 30 minutes (2026-11-04).
- `POST /auth/refresh_token` with `{"refresh_token": ...}` needs the old access token in `Authorization` as well, even an expired one. Without it Hevy answers 400 (2026-11-04).
- The refresh token rotates on every refresh. Whoever refreshes last holds the only valid copy. Record: [0006](architectural-decision-records/0006-session-on-a-volume.md).
- Nobody knows yet whether refresh tokens have an absolute lifetime (#9).

## Hevy public API

- **Page size** is at most 10 for these endpoints.
- **`POST /v1/routines`** accepts `rep_range: null` on a set. **`PUT /v1/routines/{id}`** rejects it with `Expected object, received null`, once per offending set (2026-11-05, fixed in #19). Sets without a range omit the key.
- **Create and update answers** wrap the routine as `{"routine": [ ... ]}` or `{"routine": { ... }}`; `hevy_public.Client` accepts both.
- **No routine delete.** Retired templates leave routines behind (#11).
- **Weights are stored in kilograms.** A pound value logged in the app comes back as a long float (80 lb is `36.28743275485118`). Garmin Connect shows a merged weight as 80 lbs.
- **`GET /v1/workouts/events?since=`** lists `updated` and `deleted` events with the whole workout, newest first (2026-11-05).

## hevy2garmin

- `POST /api/login {password}` sets the `h2g_session` cookie. The routine routes also accept `Authorization: Bearer <CRON_SECRET>` (2026-11-05, read in its source).
- `POST /api/routines/sync {ids}` answers `{ok, synced, skipped, failed, results[]}`. An empty `ids` list touches Garmin without syncing anything, which refreshes and stores its Garmin token.
- On a content change it deletes the old Garmin workout and creates a new one, so the watch loses it until something sends the new one (`web/lib/garmin-routine-sync.ts`).
- `POST /api/cron/webhook`, with `Authorization: Bearer <CRON_SECRET>`, ignores its body and answers at once with `{ok, mode: "staged", status: "accepted"}` (or `"throttled"` past `WEBHOOK_MAX_INFLIGHT`, 4). It then waits `WEBHOOK_DELAY_SECONDS`, tries a merge-only sync up to `WEBHOOK_MAX_ATTEMPTS - 1` times `WEBHOOK_RETRY_INTERVAL_SECONDS` apart, and lets the last attempt upload a fresh activity. Merge-only attempts skip the two-hour hold. A pod restart drops the staged work, and the scheduled sync picks it up (read in `web/lib/webhook-retry.ts` at `f0f6755`, 2026-11-05).
- `POST /api/routines/{id}/schedule {date}` answers `scheduleId: null` for a single date; the id is in `routine_schedules`.
- Tables read: `synced_routines (hevy_routine_id, garmin_workout_id, title, status, content_hash)`, `routine_schedules (hevy_routine_id, schedule_id, scheduled_date)`, and `platform_credentials` where `platform = 'garmin_tokens'`, whose `credentials -> 'garmin_tokens'` holds `di_token`, `di_client_id` and `di_refresh_token`.
- Exercise mapping is its own table. Hevy's Pullover (Dumbbell) arrives on Garmin as "EZ-Bar Pull-over" (2026-11-04).
- Merged sets keep their exercise names in Garmin Connect. Garmin shows any exercise with stored confidence 0 as "Unknown", and the merge sends `probability: 100` since upstream #325 was fixed; the deployed `f0f6755` has it. Seen correct on the 3 Nov Lower (2026-11-05). Record: [0001](architectural-decision-records/0001-merge-into-the-watch-activity.md).

## Garmin Connect

- `GET /device-service/deviceservice/mylastused` answers with `userDeviceId`, the id the device message wants.
- `POST /device-service/devicemessage/messages` takes a **list** of messages. A bare object gets `500 MismatchedInputException` (2026-11-05, fixed in #20). Each message is `{deviceId, messageUrl: "workout-service/workout/FIT/<id>", messageType: "workouts", groupName: null, messageName, priority: 1, fileType: "FIT", metaDataId: <id>}`. The watch downloads it at its next phone sync.
- connectapi answers differently to a bare bearer, so requests carry the Android app's headers (`garmin.HEADERS`).
- Garmin forwards a new activity to Strava within seconds of the phone sync, and nothing after that. hevy2garmin's merge of the 3 Nov Lower on 4 Nov changed Garmin Connect and left Strava's copy as the watch sent it (2026-11-05). Record: [0020](architectural-decision-records/0020-the-watch-recording-is-what-strava-keeps.md).
- The watch's FIT files store weight in sixteenths of a kilogram, so 25, 45 and 80 lb entered on the watch read 24.9, 45.1 and 80.1 lb on Strava.

## Strava

- Shows exactly what Garmin first forwarded. Its API cannot edit an activity's sets or delete an activity (no delete since 17 Jan 2017).
- Exercise names come from the watch's recording: auto-detected per set without a planned workout, so they can change from set to set within one exercise (3 Nov Lower, 2026-11-05).

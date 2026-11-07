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
- **Hevy private API:** undocumented, so no published terms or limits. Used for five calls a run: the refresh, the program, both preferences and the user's workouts, the last three as the app makes them for Trainer (record 0042).
- **Garmin Connect:** undocumented, with no published terms for this API. Called only after a routine changed.
- **hevy2garmin:** TJ's own deployment. Its webhook route throttles past `WEBHOOK_MAX_INFLIGHT` (see below).

## Hevy Trainer program (private)

`GET /hevy_trainer/v3/program?client_program_updated_at=1970-01-01T00:00:00.000Z&client_next_workout_updated_at=1970-01-01T00:00:00.000Z`, as catalogued by [hevy-mcp-unofficial](https://github.com/LovelessCodes/hevy-mcp-unofficial).

- **What it has** (2026-11-04): `id`, `created_at`, `current_week`, `next_workout_index`, `program_variety`, `exercises_rotated_at`, `edits`, and `templates[]`. Each template has a `key` such as `upper_2x_a` and `exercises[]` with `index`, `exercise_template_id` (the public API's template id), `set_count`, `warmup_set_count`, `rep_range {start, end}` and `rest_seconds`.
- **What it lacks**: weights, and any display title. The title comes from the key: the words before the frequency token (`upper_2x_a` is "Upper").
- **The whole reply** (2026-11-06, logged by `get_program`): `program` and `status`, nothing else. No next workout and no weights anywhere, though the request asks for `client_next_workout_updated_at`. The program also has `schema_version`, `level`, `goal`, `equipments`, `weekly_frequency`, `updated_at`, `workout_duration_minutes`, `rest_timer_length`, `cardio_preference`, `split_type` and `deloads_enabled`; each exercise also has `id` and `kind`; each template has `name` and `edits`.
- **`current_week` is not the app's week** (2026-11-04, again 2026-11-06): it read 5 while the app showed "Cycle 2 (6-Week Program)", week 2/6. Calendar weeks since `created_at` gave 8, which the app shows as cycle 2, week 2. Records: [0010](architectural-decision-records/0010-program-week-in-names.md), [0042](architectural-decision-records/0042-trainer-prescriptions-by-the-apps-rules.md). Issue #14.
- **The app's week and prescribed weights are worked out on the phone** (2026-11-06, read from the Android app 3.2.5). The v3 reply has neither, and hevy.com's Trainer page has no code for either. #12.
  - **Week.** Calendar weeks since the program's `created_at`, each starting on the user's first weekday at local midnight, plus one. Cycle is `floor((week - 1) / n) + 1` and week of cycle is `(week - 1) % n + 1`, where `n` is 6, or 7 with `deloads_enabled`. Week 8 shows as "Cycle 2", week 2/6.
  - **Weight.** From the last time the exercise was logged, its normal sets only: the base is their lowest weight. Fewer sets than the target: no change. Every set at or above the top of the rep range: base times 1.05. Every set below the bottom: base times 0.95. Otherwise no change. A deload week takes 60%. The rep range itself can move up or down a fixed ladder (4-6, 6-8, 8-12, 12-15, 15-20, 20-25, 25-30), which is the green "Reps" arrow in the app, so the program's `rep_range` is only the starting range.
  - **Rounding** goes to a weight the user has: the dumbbells, bars and plates kept in Trainer's preferences, or a machine's increment (up for an increase, down for a decrease, nearest otherwise).
  - **Dumbbells round as a pair.** The app doubles each available dumbbell before rounding, so the logged weight of a dumbbell exercise counts both. TJ logs dumbbell RDLs at 130 lb with a 100 lb heaviest dumbbell.
  - **History.** The previous log is the newest workout from the same Trainer template (`trainer_workout_template_id`) holding the exercise, outside deload weeks. Only exercises of type `weight_reps` or `bodyweight_reps` on a dumbbell, barbell or machine get a weight; `reps_only` ones move their rep range; anything else gets nothing. Types and equipment come from the library the app ships, 451 exercises in 3.2.5 (`library.py`).
  - **New exercises.** With no previous log the app guesses from the best one-rep max of the last 3 or 12 months. This tool doesn't, and keeps the last logged weight.

## Trainer's and the user's preferences (private)

- **`GET /hevy_trainer/user_preferences`** (2026-11-06): `excludedExercisesIds`, `availableWeights` and `availableEquipment` (the same lists: `platesKg`, `platesLbs`, `barsKg`, `barsLbs`, `dumbbellsKg`, `dumbbellsLbs`), `injuries` and `updated_at`. TJ's `dumbbellsLbs` runs 5 to 100 lb, out of order.
- **`GET /v2/user_preferences`** (2026-11-06): `username`, `weight_unit`, `first_weekday` and display settings.

## The user's workouts (private)

- **`GET /user_workouts_paged?username=&limit=&offset=`** answers `{workouts: [...]}`, newest first (2026-11-06, from the app's code). On 2026-11-07 a `limit` of 10 got a 400 with an empty body; the app only asks for 1 or 3, so the run asks for 3. The reply's shape is still unconfirmed live. Each workout carries `trainer_workout_template_id` and `start_time` in Unix seconds, and each set an `indicator` (`normal`, `warmup` and so on), `reps` and `weight_kg`. The public API's workouts say neither which Trainer template they came from nor much else the app's rules read.
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
- `POST /api/cron/webhook`, with `Authorization: Bearer <CRON_SECRET>`, ignores its body and answers at once with `{ok, mode: "staged", status: "accepted"}` (or `"throttled"` past `WEBHOOK_MAX_INFLIGHT`, 4). It then waits `WEBHOOK_DELAY_SECONDS`, tries a merge-only sync up to `WEBHOOK_MAX_ATTEMPTS - 1` times `WEBHOOK_RETRY_INTERVAL_SECONDS` apart, and lets the last attempt upload a fresh activity. Merge-only attempts skip the two-hour hold. A pod restart drops the staged work, and the scheduled sync picks it up (read in `web/lib/webhook-retry.ts` at `f0f6755`, 2026-11-05). No setting turns the last attempt's upload off (2026-11-06).
- The webhook route syncs the newest workout it has not finished, from Hevy's list, newest first. It takes no workout id (`syncOneWorkout`, `candidates[0]`, read 2026-11-06).
- With merge on, any attempt that finds the watch activity merges into it, merge-only or not. Merge-only changes only what happens when no activity is found. The match needs a `strength_training` activity that is saved, covers 70% of the Hevy workout and starts within 20 minutes of it, all settable on the dashboard's Settings page (`typescript/src/merge-match.ts`, read 2026-11-06). `match.py` copies it.
- The scheduled sync's two-hour hold is a constant (`DEFAULT_GRACE_MINUTES`), and after it the workout is uploaded (2026-11-06).
- `POST /api/routines/{id}/schedule {date}` answers `scheduleId: null` for a single date; the id is in `routine_schedules`.
- Tables read: `synced_routines (hevy_routine_id, garmin_workout_id, title, status, content_hash)`, `routine_schedules (hevy_routine_id, schedule_id, scheduled_date)`, `synced_workouts (hevy_id, ...)`, where any row means the workout is done, `app_cache` where `key = 'merge_settings'`, a JSONB object with `merge_mode`, `merge_watch_strategy`, `merge_activity_types`, `merge_overlap_pct` (a percentage) and `merge_max_drift_min`, and `platform_credentials` where `platform = 'garmin_tokens'`, whose `credentials -> 'garmin_tokens'` holds `di_token`, `di_client_id` and `di_refresh_token`.
- Exercise mapping is its own table. Hevy's Pullover (Dumbbell) arrives on Garmin as "EZ-Bar Pull-over" (2026-11-04).
- Merged sets keep their exercise names in Garmin Connect. Garmin shows any exercise with stored confidence 0 as "Unknown", and the merge sends `probability: 100` since upstream #325 was fixed; the deployed `f0f6755` has it. Seen correct on the 3 Nov Lower (2026-11-05). Record: [0001](architectural-decision-records/0001-merge-into-the-watch-activity.md).

## Garmin Connect

- `GET /device-service/deviceservice/mylastused` answers with `userDeviceId`, the id the device message wants.
- `POST /device-service/devicemessage/messages` takes a **list** of messages. A bare object gets `500 MismatchedInputException` (2026-11-05, fixed in #20). Each message is `{deviceId, messageUrl: "workout-service/workout/FIT/<id>", messageType: "workouts", groupName: null, messageName, priority: 1, fileType: "FIT", metaDataId: <id>}`. The watch downloads it at its next phone sync.
- connectapi answers differently to a bare bearer, so requests carry the Android app's headers (`garmin.HEADERS`).
- Garmin forwards a new activity to Strava within seconds of the phone sync, and nothing after that. hevy2garmin's merge of the 3 Nov Lower on 4 Nov changed Garmin Connect and left Strava's copy as the watch sent it (2026-11-05). Record: [0020](architectural-decision-records/0020-the-watch-recording-is-what-strava-keeps.md).
- `GET /activitylist-service/activities/search/activities?startDate=&endDate=&limit=&start=` lists activities by date, as YYYY-MM-DD, with `activityId`, `startTimeGMT` (`YYYY-MM-DD HH:MM:SS`, no zone), `duration` in seconds (0 until saved) and `activityType.typeKey`. The dates are the watch's local dates, so the poller asks for a day either side.
- The watch keeps a workout that Send to Device put on it after hevy2garmin deletes that workout from Garmin Connect. On 2026-11-06 the plain `Upper` and `Lower` from before the week names were still on the watch beside `Upper W8` and `Lower W8`, and gone from Garmin Connect. TJ deleted them on the watch.
- The watch's FIT files store weight in sixteenths of a kilogram, so 25, 45 and 80 lb entered on the watch read 24.9, 45.1 and 80.1 lb on Strava.

## Strava

- Shows exactly what Garmin first forwarded. Its API cannot edit an activity's sets or delete an activity (no delete since 17 Jan 2017).
- Exercise names come from the watch's recording: auto-detected per set without a planned workout, so they can change from set to set within one exercise (3 Nov Lower, 2026-11-05).

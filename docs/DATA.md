# Data sources

What each source can and cannot tell this tool, and every quirk found so far. Each finding carries the date it was observed. When a source surprises you, add the finding here in the same PR as the fix.

| Source | Documented | Auth | Used for |
|---|---|---|---|
| Hevy private API, `api.hevyapp.com` | No | `x-api-key: shelobs_hevy_web` plus a bearer from the hevy.com cookie | The Trainer program, session refresh |
| Hevy public API, `api.hevyapp.com/v1` | [Yes](https://api.hevyapp.com/docs) | `api-key` header (Hevy Pro) | Folders, routines, recent workouts |
| hevy2garmin dashboard | Its source | Session cookie from `POST /api/login` | Turning routines into Garmin workouts |
| hevy2garmin Postgres | Its source | CNPG `uri` | Garmin workout ids and Garmin's token, read-only |
| Garmin Connect, `connectapi.garmin.com` | No | Bearer DI token borrowed from hevy2garmin, Android app headers | Last-used device, Send to Device |

## Hevy Trainer program (private)

`GET /hevy_trainer/v3/program?client_program_updated_at=1970-01-01T00:00:00.000Z&client_next_workout_updated_at=1970-01-01T00:00:00.000Z`, as catalogued by [hevy-mcp-unofficial](https://github.com/LovelessCodes/hevy-mcp-unofficial).

- **What it has** (2026-11-04): `id`, `created_at`, `current_week`, `next_workout_index`, `program_variety`, `exercises_rotated_at`, `edits`, and `templates[]`. Each template has a `key` such as `upper_2x_a` and `exercises[]` with `index`, `exercise_template_id` (the public API's template id), `set_count`, `warmup_set_count`, `rep_range {start, end}` and `rest_seconds`.
- **What it lacks**: weights, and any display title. The title comes from the key: the words before the frequency token (`upper_2x_a` is "Upper").
- **`current_week` is not the app's week** (2026-11-04): it read 5 when the app showed cycle 2, week 2 of a 6-week cycle. Calendar weeks since `created_at` gave 8, which matched. Record: [0010](decisions/0010-program-week-in-names.md). Issue #14 tracks whether that holds.
- **`exercises_rotated_at`** read Thursday 29 Oct, so rotations do not fall on week boundaries.

## Hevy session (private)

- Tokens come from the hevy.com `auth2.0-token` cookie, a URL-encoded JSON object with `access_token`, `refresh_token` and `expires_at`. The access token lasts about 30 minutes (2026-11-04).
- `POST /auth/refresh_token` with `{"refresh_token": ...}` needs the old access token in `Authorization` as well, even an expired one. Without it Hevy answers 400 (2026-11-04).
- The refresh token rotates on every refresh. Whoever refreshes last holds the only valid copy. Record: [0006](decisions/0006-session-on-a-volume.md).
- Nobody knows yet whether refresh tokens have an absolute lifetime (#9).

## Hevy public API

- **Page size** is at most 10 for these endpoints.
- **`POST /v1/routines`** accepts `rep_range: null` on a set. **`PUT /v1/routines/{id}`** rejects it with `Expected object, received null`, once per offending set (2026-11-05, fixed in #19). Sets without a range omit the key.
- **Create and update answers** wrap the routine as `{"routine": [ ... ]}` or `{"routine": { ... }}`; `hevy_public.Client` accepts both.
- **No routine delete.** Retired templates leave routines behind (#11).
- **Weights are stored in kilograms.** A pound value logged in the app comes back as a long float (80 lb is `36.28743275485118`), and Garmin and Strava show it rounded, for example 80.1 lb.
- **`GET /v1/workouts/events?since=`** lists `updated` and `deleted` events with the whole workout, newest first (2026-11-05).

## hevy2garmin

- `POST /api/login {password}` sets the `h2g_session` cookie. The routine routes also accept `Authorization: Bearer <CRON_SECRET>` (2026-11-05, read in its source).
- `POST /api/routines/sync {ids}` answers `{ok, synced, skipped, failed, results[]}`. An empty `ids` list touches Garmin without syncing anything, which refreshes and stores its Garmin token.
- On a content change it deletes the old Garmin workout and creates a new one, so the watch loses it until something sends the new one (`web/lib/garmin-routine-sync.ts`).
- `POST /api/routines/{id}/schedule {date}` answers `scheduleId: null` for a single date; the id is in `routine_schedules`.
- Tables read: `synced_routines (hevy_routine_id, garmin_workout_id, title, status, content_hash)`, `routine_schedules (hevy_routine_id, schedule_id, scheduled_date)`, and `platform_credentials` where `platform = 'garmin_tokens'`, whose `credentials -> 'garmin_tokens'` holds `di_token`, `di_client_id` and `di_refresh_token`.
- Exercise mapping is its own table. Hevy's Pullover (Dumbbell) arrives on Garmin as "EZ-Bar Pull-over" (2026-11-04).
- Merged sets on a device-recorded activity show as "Unknown" exercise names on Garmin and Strava, while reps and weights land (upstream #325; seen on Strava 2026-11-05). Record: [0001](decisions/0001-merge-into-the-watch-activity.md).

## Garmin Connect

- `GET /device-service/deviceservice/mylastused` answers with `userDeviceId`, the id the device message wants.
- `POST /device-service/devicemessage/messages` takes a **list** of messages. A bare object gets `500 MismatchedInputException` (2026-11-05, fixed in #20). Each message is `{deviceId, messageUrl: "workout-service/workout/FIT/<id>", messageType: "workouts", groupName: null, messageName, priority: 1, fileType: "FIT", metaDataId: <id>}`. The watch downloads it at its next phone sync.
- connectapi answers differently to a bare bearer, so requests carry the Android app's headers (`garmin.HEADERS`).
- Garmin forwards a new activity to Strava within seconds of the phone sync. Edits made later, including hevy2garmin's merged sets, reached the existing Strava activity in October's data (2026-11-05).

# Using it

Once it is deployed there is nothing to run. This page is what you see, what you do, and what to do when something looks wrong.

## A normal week

- **In Hevy**, the folder `Hevy Trainer` holds one routine per Trainer template, named for the program week: `Upper W8`, `Lower W8`. Don't edit them; the next run overwrites them. Don't delete them either: hevy2garmin needs them to keep the watch's copy. Record: [0014](decisions/0014-routines-stay-in-hevy.md).
- **On the watch**, the same names appear under Workouts after the phone next syncs. Nothing is on the calendar. Record: [0008](decisions/0008-no-calendar-scheduling.md).
- **To train**, start Trainer's workout in Hevy on the phone, and on the watch start the matching workout from the Workouts list. The watch walks you through the planned exercises and sets. Log the real reps and weights in Hevy as usual.
- **During the session**, what the watch records is what Strava keeps, forever. Follow the planned sets, and if you change a weight or do different reps, enter it on the watch as well as in Hevy. Record: [0020](decisions/0020-the-watch-recording-is-what-strava-keeps.md).
- **After you finish**, the watch's activity reaches Garmin and Strava at its next phone sync. Within a minute of Finish in Hevy, the poller asks hevy2garmin to merge, and Garmin Connect has Hevy's sets a few minutes after the watch has synced. Strava does not change. Let the watch sync within about 25 minutes of finishing; after that hevy2garmin gives up waiting and uploads a second activity. Records: [0001](decisions/0001-merge-into-the-watch-activity.md), [0019](decisions/0019-poll-hevy-every-minute.md).
- **Within the hour**, the routine you just trained is updated with the weights you lifted, and the watch gets the new copy at its next sync.
- **On Monday**, the routines are renamed for the new week, `W9` and so on, and reach the watch the same way. Record: [0010](decisions/0010-program-week-in-names.md).

## Is it working?

The quickest check is the name on the watch. If it still says last week's number on a Monday afternoon, runs are failing. Then:

```sh
kubectl -n hevy2garmin-system get jobs
kubectl -n hevy2garmin-system logs job/<the latest hevy-trainer-sync job>
```

A healthy run with nothing to do ends with `nothing to push to Garmin`. A run that changed something ends with `sent ... to device ...` lines.

If Garmin Connect still shows the watch's sets half an hour after a session, check the poller and hevy2garmin:

```sh
kubectl -n hevy2garmin-system logs deploy/hevy-trainer-poll --since=1h
kubectl -n hevy2garmin-system logs deploy/hevy2garmin --since=1h | grep webhook
```

The poller logs one `workout '...' saved; hevy2garmin accepted` line per workout. hevy2garmin logs `[webhook] attempt N/10` lines, and `no watch activity on Garmin yet` until the watch has synced.

## When something breaks

| Log line | Meaning | Fix |
|---|---|---|
| `HEVY_SESSION is not the auth2.0-token cookie` | The state file is gone and the secret has no usable cookie | Paste a fresh cookie into the secret's `hevy-session` key (README, Requirements) and run a job |
| `HTTP 400 from https://api.hevyapp.com/auth/refresh_token` or `401` after a refresh | The session chain is broken, usually because something else refreshed it | Same as above. Never run a second copy against the cluster's session |
| `X is not set` | A required variable is missing | See [CONFIGURATION.md](CONFIGURATION.md) |
| `HTTP 400 from https://api.hevyapp.com/v1/routines/...` | Hevy rejected a routine payload | File a bug with the log; the payload shape is pinned in `test_build.py` |
| `hevy2garmin: ... failed=N` | hevy2garmin could not build the Garmin workout | Open the dashboard's Routines page for the error |
| `send to device failed for ...` | Garmin refused the device message | The workout is still in Garmin Connect; Send to Device there works by hand. File a bug with the log |
| `reading Hevy workout events failed` (poller) | Hevy's public API is down, the key is wrong, or the cluster could not reach it (`<urlopen error ...>`) | Nothing; the poller retries every minute and catches up |
| `asking hevy2garmin to merge ... failed` (poller) | The dashboard is down, or `CRON_SECRET` does not match | Check the dashboard pod and the secret. hevy2garmin's own schedule still merges after two hours |

## Running it by hand

From the cluster, with the deployed image and the real session:

```sh
kubectl -n hevy2garmin-system create job --from=cronjob/hevy-trainer-sync hevy-trainer-sync-manual-$(date +%H%M)
```

`--force` re-sends every routine to the watch even when nothing changed; [CONFIGURATION.md](CONFIGURATION.md) shows how to pass it. Don't run the tool from a workstation against the same Hevy session: it rotates the refresh token and the cluster's copy stops working.

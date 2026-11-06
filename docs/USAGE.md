# Using it

Once it is deployed there is nothing to run. This page is what you see, what you do, and what to do when something looks wrong.

## A normal week

- **In Hevy**, the folder `Hevy Trainer` holds one routine per Trainer template, named for the program week: `Upper W8`, `Lower W8`. Don't edit them; the next run overwrites them. Don't delete them either: hevy2garmin needs them to keep the watch's copy. Record: [0014](architectural-decision-records/0014-routines-stay-in-hevy.md).
- **On the watch**, Trainer's next workout is on today's date in the training calendar after the phone next syncs, and it's the only one this tool puts there. When the routine changes, the watch gets the new version in its place, not a second copy. Record: [0040](architectural-decision-records/0040-the-calendar-carries-workouts-to-the-watch.md).
- **To train**, start Trainer's workout in Hevy on the phone, and on the watch press the activity button, pick Strength, and say yes when it offers today's workout, the way it does for a Runna run. The watch walks you through the planned exercises and sets. Log the real reps and weights in Hevy as usual.
- **During the session**, what the watch records is what Strava keeps, forever. Follow the planned sets, and if you change a weight or do different reps, enter it on the watch as well as in Hevy. Record: [0020](architectural-decision-records/0020-the-watch-recording-is-what-strava-keeps.md).
- **After you finish**, there is nothing to do. The watch's activity reaches Garmin and Strava at its next phone sync, however late that is. The poller waits for it, then has hevy2garmin merge Hevy's sets into it, so Garmin Connect has them within a minute or two. Strava does not change, and nothing else is ever posted. A session the watch didn't record stays in Hevy only. Don't press Sync Now on the dashboard: it would upload that session, or one the watch hasn't synced yet, as a second activity. Records: [0001](architectural-decision-records/0001-merge-into-the-watch-activity.md), [0039](architectural-decision-records/0039-merge-only-after-the-watch-activity.md).
- **A minute or two after Finish in Hevy**, the poller has the mirror run: the routine you just trained gets the weights you lifted, and the next workout goes on today's date, so the watch has it at its next sync. Record: [0041](architectural-decision-records/0041-run-the-mirror-after-each-save.md).
- **On Monday**, the routines are renamed for the new week, `W9` and so on, and reach the watch the same way. Record: [0010](architectural-decision-records/0010-program-week-in-names.md).

## Is it working?

The quickest check is the name on the watch. If it still says last week's number on a Monday afternoon, runs are failing. Then:

```sh
kubectl -n hevy2garmin-system get jobs
kubectl -n hevy2garmin-system logs job/<the latest hevy-trainer-sync job>
```

A healthy run with nothing to do ends with `nothing to push to Garmin`. A run that changed something ends with `sent ... to device ...` lines.

If Garmin Connect still shows the watch's sets a few minutes after the watch has synced, check the poller and hevy2garmin:

```sh
kubectl -n hevy2garmin-system logs deploy/hevy-trainer-poll --since=1h
kubectl -n hevy2garmin-system logs deploy/hevy2garmin --since=1h | grep webhook
```

For each workout the poller logs `saved; waiting for the watch's activity on Garmin`, then `watch activity N found for ...; hevy2garmin accepted` once the watch has synced, then `is on Garmin; done`. hevy2garmin logs `[webhook] attempt 1/10: synced`.

## When something breaks

| Log line | Meaning | Fix |
|---|---|---|
| `HEVY_SESSION is not the auth2.0-token cookie` | The state file is gone and the secret has no usable cookie | Paste a fresh cookie into the secret's `hevy-session` key (README, Requirements) and run a job |
| `HTTP 400 from https://api.hevyapp.com/auth/refresh_token` or `401` after a refresh | The session chain is broken, usually because something else refreshed it | Same as above. Never run a second copy against the cluster's session |
| `X is not set` | A required variable is missing | See [CONFIGURATION.md](CONFIGURATION.md) |
| `HTTP 400 from https://api.hevyapp.com/v1/routines/...` | Hevy rejected a routine payload | File a bug with the log; the payload shape is pinned in `test_build.py` |
| `hevy2garmin: ... failed=N` | hevy2garmin could not build the Garmin workout | Open the dashboard's Routines page for the error |
| `send to device failed for ...` | Garmin refused the device message. Only with `SEND_TO_DEVICE=1`, which the cluster no longer sets | The workout is still in Garmin Connect; Send to Device there works by hand. File a bug with the log |
| `scheduled ... on ...: <error>` | hevy2garmin could not put the next workout on the calendar | Open the dashboard's Routines page for the error. The next hourly run tries again |
| `reading Hevy workout events failed` (poller) | Hevy's public API is down, the key is wrong, or the cluster could not reach it (`<urlopen error ...>`) | Nothing; the poller retries every minute and catches up |
| `checking the waiting workouts failed` (poller) | The database, Garmin or the dashboard did not answer, or `CRON_SECRET` does not match | Nothing, if it clears; the poller tries again every minute. If it repeats, check the dashboard pod, its database and the secret |
| `no watch activity turned up for ... in 2 days, 0:00:00` (poller) | The watch didn't record the session, or never synced it | Nothing. The session stays in Hevy only |
| `hevy2garmin's merge is off or not set to merge` (poller) | The dashboard's Settings page has merge off, or a watch strategy other than Merge | Turn merge on with the Merge strategy. Until then nothing is merged, so nothing is duplicated |

## Running it by hand

From the cluster, with the deployed image and the real session:

```sh
kubectl -n hevy2garmin-system create job --from=cronjob/hevy-trainer-sync hevy-trainer-sync-manual-$(date +%H%M)
```

`--force` re-sends every routine to the watch even when nothing changed; [CONFIGURATION.md](CONFIGURATION.md) shows how to pass it. Don't run the tool from a workstation against the same Hevy session: it rotates the refresh token and the cluster's copy stops working.

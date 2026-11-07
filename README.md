# hevy-trainer-sync

Puts Hevy Trainer's next workout on a Garmin watch.

Hevy Trainer builds a program and shows you the next session in the app, but it never creates a routine, and routines are the only thing [hevy2garmin](https://github.com/drkostas/hevy2garmin) can turn into a planned workout on the watch. Without a plan the watch guesses each exercise from arm movement, and because Garmin forwards an activity to Strava the moment it is created, Strava keeps those guesses even after hevy2garmin merges the real sets into Garmin Connect.

This job closes the gap. Every run it:

1. Reads the Trainer program from Hevy's private API (the endpoint the app itself uses, catalogued in [hevy-mcp-unofficial](https://github.com/LovelessCodes/hevy-mcp-unofficial)).
2. Writes one Hevy routine per program template into a folder called `Hevy Trainer`, through the public API, named for Trainer's cycle and week the way the app shows them: `Upper C2 W2` is cycle 2, week 2. The name on the watch is the quickest way to see a run didn't land. Sets, rep ranges, warm-ups and rest times come from Trainer, and so do the weights: Hevy's servers don't hand out what Trainer prescribes, the app works it out on the phone, so this follows the app's own rules on your logged sessions to get the same numbers.
3. Tells your hevy2garmin dashboard to push the routines that changed to Garmin.
4. Puts Trainer's next workout on today's date in the Garmin calendar and takes everything else it scheduled off, so there's one planned workout at a time. That's how it gets to the watch: Garmin keeps calendar workouts in step with the watch, so when hevy2garmin rebuilds a workout after a routine changes, the watch gets the new one in place of the old. It used to send each workout with Send to Device instead, which only ever adds, and old copies piled up on the watch. That step is still there behind `SEND_TO_DEVICE`, but I run with it off.

It has a second mode, `poll`, for the other direction. hevy2garmin holds a finished workout for two hours before merging it into Garmin Connect, and if the watch's activity still isn't there, it uploads one of its own, which Garmin then posts to Strava as a duplicate. `poll` reads Hevy's workout events every minute, waits until Garmin has the watch's activity for the workout, and only then calls hevy2garmin's webhook route, the same call Hevy's own webhook would make. hevy2garmin merges into the watch's activity on its first try, so Garmin Connect has the real sets a minute or two after the watch syncs, and nothing but the watch ever reaches Strava. A session the watch didn't record stays in Hevy. Strava never sees the merge, so the plan on the watch is still what makes Strava right. It runs inside the cluster, so nothing has to be reachable from the internet, and it never touches the Hevy session. I suspend hevy2garmin's own scheduled sync, since it's the thing that uploads.

Start the workout from the watch's Training menu and every set is named before Garmin ever forwards it.

Hevy's private API is undocumented and can change without notice. The public API and hevy2garmin are the only things this depends on otherwise.

## Requirements

- Hevy Pro, for the API key at https://hevy.com/settings?developer.
- A hevy2garmin dashboard with Garmin connected, reachable from wherever this runs. For `poll`, its `CRON_SECRET` and its Postgres too.
- The `auth2.0-token` cookie from a logged-in hevy.com tab. Open DevTools, Application, Cookies, and copy the value as it is; URL-encoded is fine. Both tokens in it are needed, because Hevy's refresh endpoint wants the old access token alongside the refresh token. It is only used once: the refresh token rotates on every refresh, so after the first run the state file is the only valid copy.

## Configuration

Everything is environment variables.

| Variable | Default | Purpose |
| --- | --- | --- |
| `HEVY_API_KEY` | | Public API key |
| `HEVY_SESSION` | | The `auth2.0-token` cookie value, read only when the state file is missing |
| `HEVY_STATE_FILE` | `/state/hevy-session.json` | Where the rotating session tokens live. Must persist between runs. |
| `H2G_URL` | `http://hevy2garmin` | hevy2garmin dashboard |
| `H2G_PASSWORD` | | Its login password. `poll` uses it only to have the Garmin session refreshed |
| `FOLDER_TITLE` | `Hevy Trainer` | Routine folder to manage |
| `WORKOUT_PAGES` | `4` | How many pages of ten workouts to scan for last weights |
| `DATABASE_URL` | | hevy2garmin's Postgres, read-only: the Garmin workout ids and session for Send to Device, and calendar entry ids. Unset disables both steps. `poll` needs it for the Garmin session, the merge settings and which workouts are done. |
| `SEND_TO_DEVICE` | `1` | Send each new Garmin workout to the watch. I set `0`; it leaves old copies behind |
| `GARMIN_DEVICE_ID` | last used | Which Garmin device to send to |
| `SCHEDULE_NEXT` | `0` | Put the next workout on today's Garmin calendar, which is how it reaches the watch. I set `1` |
| `TZ` | `UTC` | Which day "today" is for the calendar, and when Trainer's week turns over |
| `CRON_SECRET` | | hevy2garmin's cron secret, for `poll` |
| `POLL_SECONDS` | `60` | How often `poll` checks Hevy |
| `RUN_CRONJOB` | | A CronJob for `poll` to run as soon as a workout is saved, so the next workout is on the calendar right after a session. I set `hevy-trainer-sync` |

Flags: `--dry-run` reads everything and writes nothing to Hevy or hevy2garmin (the session token is still refreshed). `--force` pushes every managed routine to Garmin even if nothing changed.

## Running

I run it as a Kubernetes CronJob next to hevy2garmin; the manifests are in my [kubernetes-manifests](https://github.com/zimmertr/kubernetes-manifests) repo under `misc/hevy2garmin`. CI cuts a release on every merge to main, versioned from the PR title with GitVersion, and bumps the tag there.

CI runs the tests and reports line and branch coverage. Anything local runs in Docker:

```sh
docker run --rm -v "$PWD":/repo -w /repo python:3.13-slim sh -c 'pip install -q -r requirements-dev.txt && PYTHONPATH=src python -m coverage run -m unittest discover -s tests && python -m coverage report'
```

Don't run the tool itself against the session the cluster uses. Every run, `--dry-run` included, rotates the refresh token.

How it all fits together, how to run it by hand, and why it works the way it does are in [docs/](docs/).

## What it does not do

- Delete routines. The public API has no delete, so a template Trainer retires stays in the folder until you remove it.
- Guess weights Trainer hasn't seen. An exercise new to the program gets the last weight you logged for it anywhere, or none, until you've done it once.
- Follow mid-session changes. The watch has whatever the last run wrote; swap an exercise in the app during a workout and hevy2garmin's merge fixes Garmin Connect afterwards, as before.

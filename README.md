# hevy-trainer-sync

Puts Hevy Trainer's next workout on a Garmin watch.

Hevy Trainer builds a program and shows you the next session in the app, but it never creates a routine, and routines are the only thing [hevy2garmin](https://github.com/drkostas/hevy2garmin) can turn into a planned workout on the watch. Without a plan the watch guesses each exercise from arm movement, and because Garmin forwards an activity to Strava the moment it is created, Strava keeps those guesses even after hevy2garmin merges the real sets into Garmin Connect.

This job closes the gap. Every run it:

1. Reads the Trainer program from Hevy's private API (the endpoint the app itself uses, catalogued in [hevy-mcp-unofficial](https://github.com/LovelessCodes/hevy-mcp-unofficial)).
2. Writes one Hevy routine per program template into a folder called `Hevy Trainer`, through the public API, named for the program week: `Upper W8` is the eighth week since the program started, which is what the app's cycle and week multiply out to. The name on the watch is the quickest way to see a run didn't land. Sets, rep ranges, warm-ups and rest times come from Trainer; working weights come from your last logged session of each exercise.
3. Tells your hevy2garmin dashboard to push the routines that changed to Garmin.
4. Sends each new Garmin workout to the watch, the way Garmin Connect's Send to Device button does. hevy2garmin recreates the Garmin workout whenever a routine changes, and the new copy isn't on the watch until something sends it. The watch downloads it at its next phone sync. This uses the Garmin session hevy2garmin holds, read from its Postgres, so Garmin never sees a second login.

Optionally (`SCHEDULE_NEXT=1`) it also puts Trainer's next workout on today's date in the Garmin calendar. Off by default: it means a planned-workout entry on every day until you train.

Start the workout from the watch's Training menu and every set is named before Garmin ever forwards it.

Hevy's private API is undocumented and can change without notice. The public API and hevy2garmin are the only things this depends on otherwise.

## Requirements

- Hevy Pro, for the API key at https://hevy.com/settings?developer.
- A hevy2garmin dashboard with Garmin connected, reachable from wherever this runs.
- The `auth2.0-token` cookie from a logged-in hevy.com tab. Open DevTools, Application, Cookies, and copy the value as it is; URL-encoded is fine. Both tokens in it are needed, because Hevy's refresh endpoint wants the old access token alongside the refresh token. It is only used once: the refresh token rotates on every refresh, so after the first run the state file is the only valid copy.

## Configuration

Everything is environment variables.

| Variable | Default | Purpose |
| --- | --- | --- |
| `HEVY_API_KEY` | | Public API key |
| `HEVY_SESSION` | | The `auth2.0-token` cookie value, read only when the state file is missing |
| `HEVY_STATE_FILE` | `/state/hevy-session.json` | Where the rotating session tokens live. Must persist between runs. |
| `H2G_URL` | `http://hevy2garmin` | hevy2garmin dashboard |
| `H2G_PASSWORD` | | Its login password |
| `FOLDER_TITLE` | `Hevy Trainer` | Routine folder to manage |
| `WORKOUT_PAGES` | `4` | How many pages of ten workouts to scan for last weights |
| `DATABASE_URL` | | hevy2garmin's Postgres, read-only: the Garmin workout ids and session for Send to Device, and calendar entry ids. Unset disables both steps. |
| `SEND_TO_DEVICE` | `1` | Send each new Garmin workout to the watch |
| `GARMIN_DEVICE_ID` | last used | Which Garmin device to send to |
| `SCHEDULE_NEXT` | `0` | Also put the next workout on today's Garmin calendar |
| `TZ` | `UTC` | Which day "today" is for the calendar |

Flags: `--dry-run` reads everything and writes nothing to Hevy or hevy2garmin (the session token is still refreshed). `--force` pushes every managed routine to Garmin even if nothing changed.

## Running

I run it as a Kubernetes CronJob next to hevy2garmin; the manifests are in my [kubernetes-manifests](https://github.com/zimmertr/kubernetes-manifests) repo under `misc/hevy2garmin`. CI builds the image on every merge to main and bumps the tag there.

CI runs the tests, with 100% line and branch coverage required. Anything local runs in Docker:

```sh
docker run --rm -v "$PWD":/repo -w /repo python:3.13-slim sh -c 'pip install -q -r requirements-dev.txt && PYTHONPATH=src python -m coverage run -m unittest discover -s tests && python -m coverage report'
```

Don't run the tool itself against the session the cluster uses. Every run, `--dry-run` included, rotates the refresh token.

How it all fits together, how to run it by hand, and why it works the way it does are in [docs/](docs/).

## What it does not do

- Delete routines. The public API has no delete, so a template Trainer retires stays in the folder until you remove it.
- Guess weights Trainer hasn't seen. An exercise with no logged working set gets no weight on the watch.
- Follow mid-session changes. The watch has whatever the last run wrote; swap an exercise in the app during a workout and hevy2garmin's merge fixes Garmin Connect afterwards, as before.

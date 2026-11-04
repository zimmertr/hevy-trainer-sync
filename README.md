# hevy-trainer-sync

Puts Hevy Trainer's next workout on a Garmin watch.

Hevy Trainer builds a program and shows you the next session in the app, but it never creates a routine, and routines are the only thing [hevy2garmin](https://github.com/drkostas/hevy2garmin) can turn into a planned workout on the watch. Without a plan the watch guesses each exercise from arm movement, and because Garmin forwards an activity to Strava the moment it is created, Strava keeps those guesses even after hevy2garmin merges the real sets into Garmin Connect.

This job closes the gap. Every run it:

1. Reads the Trainer program from Hevy's private API (the endpoint the app itself uses, catalogued in [hevy-mcp-unofficial](https://github.com/LovelessCodes/hevy-mcp-unofficial)).
2. Writes one Hevy routine per program template into a folder called `Hevy Trainer`, through the public API, named for where the program stands: `Upper C2-W2` is cycle 2, week 2. The name on the watch is the quickest way to see a run didn't land. Sets, rep ranges, warm-ups and rest times come from Trainer; working weights come from your last logged session of each exercise.
3. Tells your hevy2garmin dashboard to push the routines that changed to Garmin.
4. Puts Trainer's next workout on today's date in the Garmin calendar. That is what gets it onto the watch: Garmin pushes scheduled workouts to the device by itself, while a workout that only sits in the library needs Send to Device by hand, and hevy2garmin recreates the Garmin workout whenever a routine changes, which drops that. A past entry that was never done is moved to today; one that was done stays, linked to its activity.

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
| `CYCLE_WEEKS` | `3` | Weeks per Trainer cycle, for the `C2-W2` suffix. The API only reports the week number; the app shows it as cycle and week. |
| `DATABASE_URL` | | hevy2garmin's Postgres, read-only, for the calendar entry ids its API doesn't return. Unset disables the calendar step. |
| `TZ` | `UTC` | Which day "today" is for the calendar |

Flags: `--dry-run` reads everything and writes nothing to Hevy or hevy2garmin (the session token is still refreshed). `--force` pushes every managed routine to Garmin even if nothing changed.

## Running

```sh
PYTHONPATH=src python3 -m hevy_trainer_sync --dry-run
```

Tests need nothing but Python 3.11 or newer:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

Build the image:

```sh
docker buildx build --platform linux/amd64 --push -t "zimmertr/hevy-trainer-sync:$(git rev-parse HEAD)" .
```

I run it as a Kubernetes CronJob next to hevy2garmin; the manifests are in my [kubernetes-manifests](https://github.com/zimmertr/kubernetes-manifests) repo under `misc/hevy2garmin`.

## What it does not do

- Delete routines. The public API has no delete, so a template Trainer retires stays in the folder until you remove it.
- Guess weights Trainer hasn't seen. An exercise with no logged working set gets no weight on the watch.
- Follow mid-session changes. The watch has whatever the last run wrote; swap an exercise in the app during a workout and hevy2garmin's merge fixes Garmin Connect afterwards, as before.

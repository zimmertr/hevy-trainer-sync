# hevy-trainer-sync

Puts Hevy Trainer's next workout on a Garmin watch.

Hevy Trainer builds a program and shows you the next session in the app, but it never creates a routine, and routines are the only thing [hevy2garmin](https://github.com/drkostas/hevy2garmin) can turn into a planned workout on the watch. Without a plan the watch guesses each exercise from arm movement, and because Garmin forwards an activity to Strava the moment it is created, Strava keeps those guesses even after hevy2garmin merges the real sets into Garmin Connect.

This job closes the gap. Every run it:

1. Reads the Trainer program from Hevy's private API (the endpoint the app itself uses, catalogued in [hevy-mcp-unofficial](https://github.com/LovelessCodes/hevy-mcp-unofficial)).
2. Writes one Hevy routine per program template (`Upper`, `Lower`, ...) into a folder called `Hevy Trainer`, through the public API. Sets, rep ranges, warm-ups and rest times come from Trainer; working weights come from your last logged session of each exercise.
3. Tells your hevy2garmin dashboard to push the routines that changed to Garmin.

Start the workout from the watch's Training menu and every set is named before Garmin ever forwards it.

Hevy's private API is undocumented and can change without notice. The public API and hevy2garmin are the only things this depends on otherwise.

## Requirements

- Hevy Pro, for the API key at https://hevy.com/settings?developer.
- A hevy2garmin dashboard with Garmin connected, reachable from wherever this runs.
- The `auth2.0-token` cookie from a logged-in hevy.com tab. Open DevTools, Application, Cookies, copy the value, URL-decode it, and take the `refresh_token` field. It is only used once: the token rotates on every refresh, so after the first run the state file is the only valid copy.

## Configuration

Everything is environment variables.

| Variable | Default | Purpose |
| --- | --- | --- |
| `HEVY_API_KEY` | | Public API key |
| `HEVY_REFRESH_TOKEN` | | Bootstrap refresh token, read only when the state file is missing |
| `HEVY_STATE_FILE` | `/state/hevy-session.json` | Where the rotating session tokens live. Must persist between runs. |
| `H2G_URL` | `http://hevy2garmin` | hevy2garmin dashboard |
| `H2G_PASSWORD` | | Its login password |
| `FOLDER_TITLE` | `Hevy Trainer` | Routine folder to manage |
| `WORKOUT_PAGES` | `4` | How many pages of ten workouts to scan for last weights |

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

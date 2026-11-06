# Configuration

Everything is environment variables and two flags. There is no config file. The README carries the same variable table in short; change both together.

## Variables

| Variable | Default | Required | Read by | Purpose |
|---|---|---|---|---|
| `HEVY_API_KEY` | | Yes | `cli.py` | Hevy public API key, from https://hevy.com/settings?developer (Hevy Pro) |
| `HEVY_SESSION` | | First run only | `state.load_or_bootstrap` | The hevy.com `auth2.0-token` cookie, whole, URL-encoded or not. Ignored once the state file exists |
| `HEVY_STATE_FILE` | `/state/hevy-session.json` | | `state` | The rotating session. Must persist between runs, and only one process may use it |
| `H2G_URL` | `http://hevy2garmin` | | `h2g.Dashboard`, `poll.main` | The hevy2garmin dashboard |
| `H2G_PASSWORD` | | Unless `--dry-run`; always for `poll` | `h2g.Dashboard` | The dashboard's login password. The poller logs in only to have Garmin's token refreshed |
| `FOLDER_TITLE` | `Hevy Trainer` | | `cli.py` | The routine folder this tool owns. Routines outside it are never touched |
| `WORKOUT_PAGES` | `4` | | `cli.py` | Pages of ten workouts scanned for last weights |
| `DATABASE_URL` | | For `poll` | `db` | hevy2garmin's Postgres, read-only. Unset turns off Send to Device and the calendar. The poller reads its Garmin token, merge settings and finished workouts |
| `SEND_TO_DEVICE` | `1` | | `cli.py` | `1` sends each new Garmin workout to the watch; anything else skips it |
| `GARMIN_DEVICE_ID` | last-used device | | `cli.send_to_device` | The Garmin device to send to |
| `SCHEDULE_NEXT` | `0` | | `cli.py` | `1` also puts the next workout on today's Garmin calendar. Record: [0008](architectural-decision-records/0008-no-calendar-scheduling.md) |
| `TZ` | `UTC` | | `schedule.today_in` | Which day "today" is for the calendar |
| `CRON_SECRET` | | `poll` only | `poll.main` | hevy2garmin's cron secret, sent as a bearer to its webhook route |
| `POLL_SECONDS` | `60` | | `poll.main` | How often `poll` reads Hevy's workout events |

An empty string counts as unset. A required variable that is missing exits with status 2 and names it.

## Modes and flags

`python -m hevy_trainer_sync` runs the mirror once. `python -m hevy_trainer_sync poll` runs the poller until stopped; it reads only `HEVY_API_KEY`, `H2G_URL`, `H2G_PASSWORD`, `DATABASE_URL`, `CRON_SECRET` and `POLL_SECONDS`, and takes no flags. How long it waits for the watch (48 hours) and how long before it asks hevy2garmin again (30 minutes) are constants in `poll.py`. The mirror's flags:

| Flag | Effect |
|---|---|
| `--dry-run` | Reads everything and writes nothing to Hevy, hevy2garmin or Garmin. The Hevy session is still refreshed and saved, because reading the program needs a valid token |
| `--force` | Sends every managed routine to hevy2garmin and the watch, changed or not |

## In the cluster

Kubernetes-Manifests `misc/hevy2garmin/resources/trainer-sync.yml` sets:

| Variable | Source |
|---|---|
| `HEVY_API_KEY` | Secret `hevy2garmin`, key `hevy-api-key` |
| `HEVY_SESSION` | Secret `hevy2garmin`, key `hevy-session`, optional |
| `H2G_URL` | `http://hevy2garmin` |
| `H2G_PASSWORD` | Secret `hevy2garmin`, key `password` |
| `HEVY_STATE_FILE` | `/state/hevy-session.json` on PVC `hevy-trainer-sync-state` |
| `DATABASE_URL` | Secret `hevy2garmin-database-app`, key `uri` |

Everything else takes its default.

`misc/hevy2garmin/resources/trainer-poll.yml` runs the poller with args `poll` and sets:

| Variable | Source |
|---|---|
| `HEVY_API_KEY` | Secret `hevy2garmin`, key `hevy-api-key` |
| `H2G_URL` | `http://hevy2garmin` |
| `H2G_PASSWORD` | Secret `hevy2garmin`, key `password` |
| `DATABASE_URL` | Secret `hevy2garmin-database-app`, key `uri` |
| `CRON_SECRET` | Secret `hevy2garmin`, key `cron-secret` |

hevy2garmin's own Deployment sets `WEBHOOK_DELAY_SECONDS=0`, `WEBHOOK_RETRY_INTERVAL_SECONDS=180` and `WEBHOOK_MAX_ATTEMPTS=10`. The poller calls the route only once the watch's activity is on Garmin, so the first attempt, at once, merges. The `hevy2garmin-sync` CronJob is suspended. Record: [0039](architectural-decision-records/0039-merge-only-after-the-watch-activity.md).

To run the mirror once with a flag, create a Job from the CronJob and add the argument:

```sh
kubectl -n hevy2garmin-system create job --from=cronjob/hevy-trainer-sync hevy-trainer-sync-force --dry-run=client -o json \
  | python3 -c 'import json,sys; j=json.load(sys.stdin); j["spec"]["template"]["spec"]["containers"][0]["args"]=["--force"]; print(json.dumps(j))' \
  | kubectl -n hevy2garmin-system create -f -
```

## Logs

One line per step at `INFO`, `WARNING` for skipped steps, `ERROR` for failures, all on stdout. There is no log-level setting.

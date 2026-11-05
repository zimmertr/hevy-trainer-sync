# Configuration

Everything is environment variables and two flags. There is no config file. The README carries the same variable table in short; change both together.

## Variables

| Variable | Default | Required | Read by | Purpose |
|---|---|---|---|---|
| `HEVY_API_KEY` | | Yes | `cli.py` | Hevy public API key, from https://hevy.com/settings?developer (Hevy Pro) |
| `HEVY_SESSION` | | First run only | `state.load_or_bootstrap` | The hevy.com `auth2.0-token` cookie, whole, URL-encoded or not. Ignored once the state file exists |
| `HEVY_STATE_FILE` | `/state/hevy-session.json` | | `state` | The rotating session. Must persist between runs, and only one process may use it |
| `H2G_URL` | `http://hevy2garmin` | | `h2g.Dashboard` | The hevy2garmin dashboard |
| `H2G_PASSWORD` | | Unless `--dry-run` | `h2g.Dashboard` | The dashboard's login password |
| `FOLDER_TITLE` | `Hevy Trainer` | | `cli.py` | The routine folder this tool owns. Routines outside it are never touched |
| `WORKOUT_PAGES` | `4` | | `cli.py` | Pages of ten workouts scanned for last weights |
| `DATABASE_URL` | | | `db` | hevy2garmin's Postgres, read-only. Unset turns off Send to Device and the calendar |
| `SEND_TO_DEVICE` | `1` | | `cli.py` | `1` sends each new Garmin workout to the watch; anything else skips it |
| `GARMIN_DEVICE_ID` | last-used device | | `cli.send_to_device` | The Garmin device to send to |
| `SCHEDULE_NEXT` | `0` | | `cli.py` | `1` also puts the next workout on today's Garmin calendar. Record: [0008](decisions/0008-no-calendar-scheduling.md) |
| `TZ` | `UTC` | | `schedule.today_in` | Which day "today" is for the calendar |

An empty string counts as unset. A required variable that is missing exits with status 2 and names it.

## Flags

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

Everything else takes its default. To run once with a flag, create a Job from the CronJob and add the argument:

```sh
kubectl -n hevy2garmin-system create job --from=cronjob/hevy-trainer-sync hevy-trainer-sync-force --dry-run=client -o json \
  | python3 -c 'import json,sys; j=json.load(sys.stdin); j["spec"]["template"]["spec"]["containers"][0]["args"]=["--force"]; print(json.dumps(j))' \
  | kubectl -n hevy2garmin-system create -f -
```

## Logs

One line per step at `INFO`, `WARNING` for skipped steps, `ERROR` for failures, all on stdout. There is no log-level setting.

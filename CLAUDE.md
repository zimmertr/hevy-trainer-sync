# hevy-trainer-sync

Mirrors the Hevy Trainer program into Hevy routines, has hevy2garmin turn them into Garmin workouts, and sends those to the watch. One Python command, run hourly as a Kubernetes CronJob. Start with [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Documentation

Prose lives in `docs/`. A change that makes any of it untrue updates it in the same PR. The README is TJ's: keep it accurate and in his voice, never restructure it, and change its variable table together with `docs/CONFIGURATION.md`. Record: [0017](docs/decisions/0017-docs-and-records.md)

| Doc | Holds |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | The two flows, one run step by step, the modules, the Kubernetes objects |
| [`docs/CICD.md`](docs/CICD.md) | From PR to the running CronJob, with the diagram. Keep it current with every workflow or manifest change |
| [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) | Every variable and flag, and where the cluster sets each one |
| [`docs/USAGE.md`](docs/USAGE.md) | What TJ sees in Hevy, on the watch and on Strava, and what to do when it breaks |
| [`docs/DATA.md`](docs/DATA.md) | What each source returns, and every quirk found, dated |
| [`docs/TRAFFIC.md`](docs/TRAFFIC.md) | Every outbound call per run, timeouts and retries |
| [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) | The CI-first loop, Docker commands, how to write tests |
| [`docs/decisions/`](docs/decisions/README.md) | One record per decision. The README is the index and says how to write one |

Every decision gets a record in the same PR that makes it, and the rule below that states it links to it.

## How it fits together

- hevy2garmin merges Hevy's sets into the watch's own Garmin activity (Enhance on, sync window from September 2026). Record: [0001](docs/decisions/0001-merge-into-the-watch-activity.md)
- This tool reads Trainer's program from Hevy's private API and writes one routine per template into the `Hevy Trainer` folder, which hevy2garmin syncs to Garmin. Record: [0002](docs/decisions/0002-mirror-trainer-into-routines.md)
- It runs hourly as CronJob `hevy-trainer-sync`, one run at a time. Record: [0007](docs/decisions/0007-hourly-cronjob.md)
- The routines stay in Hevy; hevy2garmin is keyed on their ids. Record: [0014](docs/decisions/0014-routines-stay-in-hevy.md)
- Garmin's own Strava connection stays on, so the first Strava post is the watch's version until the merge lands. Record: [0016](docs/decisions/0016-garmin-keeps-posting-to-strava.md)

## Rules

- **The session has one owner.** The Hevy session is bootstrapped once from the whole `auth2.0-token` cookie and then lives only in `HEVY_STATE_FILE` on the PVC. Never refresh it from a second process, and never run the tool locally against the cluster's session. Record: [0006](docs/decisions/0006-session-on-a-volume.md)
- **hevy2garmin owns Garmin.** Never log in to Garmin and never refresh Garmin's token from here. Send to Device borrows hevy2garmin's token read-only from its database; on a 401, ask the dashboard to sync nothing and read the token again. Never write to hevy2garmin's tables. Record: [0009](docs/decisions/0009-send-to-device-from-here.md)
- **No calendar.** The calendar step stays off (`SCHEDULE_NEXT` unset). Record: [0008](docs/decisions/0008-no-calendar-scheduling.md)
- **Names carry the program week**, counted from the program's `created_at`, and existing routines are matched by base title so a rename updates in place. Record: [0010](docs/decisions/0010-program-week-in-names.md)
- **Nothing goes upstream yet.** No issue, PR or fork on drkostas/hevy2garmin until TJ says so; anything posted there is public. Record: [0015](docs/decisions/0015-nothing-upstream-yet.md)
- **Only touch the managed folder.** Routines outside `FOLDER_TITLE` are never read for matching or written.
- **`--dry-run` writes nothing** to Hevy, hevy2garmin or Garmin.

## Tests

Every change ships with tests. Coverage stays at 100% of lines and branches, and CI fails below it. Tests use `unittest` and `unittest.mock`, and never touch the network or a database. Record: [0018](docs/decisions/0018-full-coverage.md)

CI runs the tests. Commit early, push, open a draft PR and read the `test` job. Run anything locally only when CI cannot answer the question, and then in Docker, never on the host. The commands are in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## Issues

File issues with [`.claude/skills/create-issue/SKILL.md`](.claude/skills/create-issue/SKILL.md): the two-sentence summary, the six sections, the hemingway and humanizer passes, one priority, one type, the area labels and the session label. Record: [0013](docs/decisions/0013-bluebird-issue-flow.md)

## Working in this repo

- Work in a fresh clone in the session's scratchpad, never in TJ's checkout. Branch from the latest `origin/main`.
- Everything reaches main through a PR that TJ approves. Never push to main. Record: [0005](docs/decisions/0005-images-from-ci-prs-only.md)
- CI builds and pushes the image; never build or push one by hand. Record: [0005](docs/decisions/0005-images-from-ci-prs-only.md)
- CI bumps the tag in Kubernetes-Manifests by editing the one `newTag` line. A change to env vars, secrets or the schedule needs its own Kubernetes-Manifests PR, merged after the image that reads it. Records: [0011](docs/decisions/0011-ci-bumps-manifests.md), [0012](docs/decisions/0012-tag-edited-in-place.md)
- The code lives here and the manifests live in Kubernetes-Manifests `misc/hevy2garmin`. Records: [0003](docs/decisions/0003-own-repo-and-image.md), [0004](docs/decisions/0004-public-gpl-3.md)
- The repo is public: no tokens, ids or personal data in code, fixtures or logs.

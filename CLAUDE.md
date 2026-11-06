# hevy-trainer-sync

Mirrors the Hevy Trainer program into Hevy routines, has hevy2garmin turn them into Garmin workouts, and sends those to the watch. One Python command, run hourly as a Kubernetes CronJob, plus a `poll` mode that runs as a Deployment and starts hevy2garmin's merge as soon as a workout is saved. Start with [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Documentation

Prose lives in `docs/`. A change that makes any of it untrue updates it in the same PR. The README is TJ's: keep it accurate and in his voice, never restructure it, and change its variable table together with `docs/CONFIGURATION.md`. Record: [0017](docs/architectural-decision-records/0017-docs-and-records.md)

| Doc | Holds |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | The two flows, one run step by step, the modules, the Kubernetes objects |
| [`docs/CICD.md`](docs/CICD.md) | From PR to the running CronJob, with the diagram. Keep it current with every workflow or manifest change |
| [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) | Every variable and flag, and where the cluster sets each one |
| [`docs/USAGE.md`](docs/USAGE.md) | What TJ sees in Hevy, on the watch and on Strava, and what to do when it breaks |
| [`docs/DATA.md`](docs/DATA.md) | What each source returns, and every quirk found, dated |
| [`docs/TRAFFIC.md`](docs/TRAFFIC.md) | Every outbound call per run, timeouts and retries |
| [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) | The CI-first loop, the `make` targets, how to write tests |
| [`docs/architectural-decision-records/`](docs/architectural-decision-records/README.md) | One record per decision. The README is the index and says how to write one. Record: [0028](docs/architectural-decision-records/0028-records-in-architectural-decision-records.md) |

Every decision gets a record in the same PR that makes it, and the rule below that states it links to it.

## How it fits together

- hevy2garmin merges Hevy's sets into the watch's own Garmin activity (Enhance on, sync window from September 2026). Record: [0001](docs/architectural-decision-records/0001-merge-into-the-watch-activity.md)
- This tool reads Trainer's program from Hevy's private API and writes one routine per template into the `Hevy Trainer` folder, which hevy2garmin syncs to Garmin. Record: [0002](docs/architectural-decision-records/0002-mirror-trainer-into-routines.md)
- It runs hourly as CronJob `hevy-trainer-sync`, one run at a time. Record: [0007](docs/architectural-decision-records/0007-hourly-cronjob.md)
- The routines stay in Hevy; hevy2garmin is keyed on their ids. Record: [0014](docs/architectural-decision-records/0014-routines-stay-in-hevy.md)
- Strava keeps exactly what the watch recorded; the merge never reaches it. So the planned workout on the watch must carry the right exercises, sets, rep targets and weights. Garmin's own Strava connection stays on, and this tool never uploads to Strava. Record: [0020](docs/architectural-decision-records/0020-the-watch-recording-is-what-strava-keeps.md)
- `poll` reads Hevy's workout events every 60 seconds from inside the cluster and calls hevy2garmin's webhook route for each new workout, so Garmin Connect has the merge within minutes. Nothing is exposed, and the poller never touches the Hevy session. Record: [0019](docs/architectural-decision-records/0019-poll-hevy-every-minute.md)

## Rules

- **The session has one owner.** The Hevy session is bootstrapped once from the whole `auth2.0-token` cookie and then lives only in `HEVY_STATE_FILE` on the PVC. Never refresh it from a second process, and never run the tool locally against the cluster's session. Record: [0006](docs/architectural-decision-records/0006-session-on-a-volume.md)
- **hevy2garmin owns Garmin.** Never log in to Garmin and never refresh Garmin's token from here. Send to Device borrows hevy2garmin's token read-only from its database; on a 401, ask the dashboard to sync nothing and read the token again. Never write to hevy2garmin's tables. Record: [0009](docs/architectural-decision-records/0009-send-to-device-from-here.md)
- **No calendar.** The calendar step stays off (`SCHEDULE_NEXT` unset). Record: [0008](docs/architectural-decision-records/0008-no-calendar-scheduling.md)
- **Names carry the program week**, counted from the program's `created_at`, and existing routines are matched by base title so a rename updates in place. Record: [0010](docs/architectural-decision-records/0010-program-week-in-names.md)
- **Nothing goes upstream yet.** No issue, PR or fork on drkostas/hevy2garmin until TJ says so; anything posted there is public. Record: [0015](docs/architectural-decision-records/0015-nothing-upstream-yet.md)
- **Only touch the managed folder.** Routines outside `FOLDER_TITLE` are never read for matching or written.
- **`--dry-run` writes nothing** to Hevy, hevy2garmin or Garmin.

## Tests

Every change ships with tests. Coverage aims at 100% of lines and branches without being held to it: CI reports it, every gap gets a test or a written reason, and no test exists only to reach a line. Tests use `unittest` and `unittest.mock`, and never touch the network or a database. Record: [0032](docs/architectural-decision-records/0032-coverage-aims-at-100.md)

CI runs the tests. Commit early, push, open a draft PR and read the `test` job. Run anything locally only when CI cannot answer the question, and then in Docker, never on the host. The commands are in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## Issues

File issues with the `create-issue` skill: the two-sentence summary, the six sections, the hemingway and humanizer passes, one priority, one type, the area labels and the session label. Record: [0013](docs/architectural-decision-records/0013-bluebird-issue-flow.md) The skill is shared across TJ's repos and lives in [zimmertr/ai-config](https://github.com/zimmertr/ai-config), linked into `~/.claude/skills`; it reads the four things below from this section. Record: [0027](docs/architectural-decision-records/0027-shared-create-issue-skill.md)

- **The reader**: someone who lifts and wears the watch, and does not read code.
- **The gates**: the tests pass in CI, and any new coverage gap has a test or a written reason; the README's table of variables and "What it does not do" match the behaviour; the `docs/` page that owns the topic changes in the same PR; a change to env vars, secrets or the schedule ships with a Kubernetes-Manifests PR for `misc/hevy2garmin`.
- **The constraints**: the Hevy session on the volume is the only valid copy, so never refresh it from a second process; everything Garmin goes through hevy2garmin, never a second Garmin login; `--dry-run` must stay write-free; the private Hevy endpoint is undocumented, so log what you depend on.
- **The areas**: `hevy` (the private program endpoint, the public API, the session), `garmin` (Garmin Connect, device messages, the watch), `hevy2garmin` (the dashboard and its database), `ci`, `kubernetes`, `ux`, `security`.

## Working in this repo

- Work in a fresh clone in the session's scratchpad, never in TJ's checkout. Branch from the latest `origin/main`.
- Everything reaches main through a PR that TJ approves. Never push to main. Record: [0005](docs/architectural-decision-records/0005-images-from-ci-prs-only.md)
- **Branch protection enforces it**, admins included: `test`, `PR Title`, `Lint` and `Docker Build` must pass and every conversation must be resolved before a PR can merge. There is no Copilot review ruleset. Renaming any of those jobs means updating the required checks in the same change. Records: [0024](docs/architectural-decision-records/0024-branch-protection.md), [0030](docs/architectural-decision-records/0030-pr-lint-and-image-checks.md), [0033](docs/architectural-decision-records/0033-no-copilot-review-ruleset.md)
- **Dependabot's patch updates are the one exception:** they merge themselves once those checks pass, then release and deploy. Minor, major and digest-only updates wait for TJ. Record: [0025](docs/architectural-decision-records/0025-dependabot-with-patch-auto-merge.md)
- CI builds and pushes the image; never build or push one by hand. Record: [0005](docs/architectural-decision-records/0005-images-from-ci-prs-only.md)
- **Every merge to main is a release.** GitVersion reads the bump from the PR title, so every PR title is `type(scope): summary` with Bluebird's types; `feat` is a minor, a `!` before the colon is a major, the rest are patches, and the body never counts. The `PR Title` check fails any other title. Image tags and git tags are the version, never a SHA, and releases are immutable. Record: [0021](docs/architectural-decision-records/0021-semver-release-per-merge.md)
- **Production moves only onto a scanned image.** A fixable Critical or High in the pushed image holds the release; fix forward with the next one. Record: [0022](docs/architectural-decision-records/0022-scan-before-production.md)
- **Actions are pinned to commit SHAs** with the version in a comment, and the base image to tag@digest; Dependabot moves both. GitVersion's `versionSpec` is pinned exactly and moves by hand. Records: [0023](docs/architectural-decision-records/0023-pinned-actions-and-attestations.md), [0025](docs/architectural-decision-records/0025-dependabot-with-patch-auto-merge.md)
- **Security scanning:** CodeQL default setup, secret scanning with push protection, private vulnerability reporting (`SECURITY.md`), and a weekly Trivy scan of the latest release that reports to the Security tab. Record: [0026](docs/architectural-decision-records/0026-security-scanning.md)
- CI bumps the tag in Kubernetes-Manifests by editing the one `newTag` line. A change to env vars, secrets or the schedule needs its own Kubernetes-Manifests PR, merged after the release that reads it. Records: [0011](docs/architectural-decision-records/0011-ci-bumps-manifests.md), [0012](docs/architectural-decision-records/0012-tag-edited-in-place.md)
- The code lives here and the manifests live in Kubernetes-Manifests `misc/hevy2garmin`. Records: [0003](docs/architectural-decision-records/0003-own-repo-and-image.md), [0004](docs/architectural-decision-records/0004-public-gpl-3.md)
- The repo is public: no tokens, ids or personal data in code, fixtures or logs.

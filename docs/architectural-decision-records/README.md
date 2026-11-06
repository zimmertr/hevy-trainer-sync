# Decision records

One file for each design decision: what was decided, when, who decided, and the evidence that settled it. A record sits beside the [`CLAUDE.md`](../../CLAUDE.md) rule that states the decision today and does not replace it. The guide tells a session what to do. The record keeps why, and since when.

## Write a record

- Copy [`0000-template.md`](0000-template.md) to `NNNN-slug.md` with the next free number. Numbers have four digits and are never reused. The first batch, 0001 to 0018, was backfilled on 2026-11-05 in roughly the order the decisions were made; later records take the next free number whatever their date.
- The title is the decision, as one sentence.
- Take the date and the decider from the conversation or issue that settled it, quoting the decider where the words exist. When nothing records them, use the merge date and the author of the PR that shipped it, and say that git is the source.
- Give every observation the date it was made.
- `Cited in code as` lists the issue and PR numbers that source comments cite for the decision, so a search for `#20` finds the record and the code together.
- Link the record from its `CLAUDE.md` rule as ` Record: [NNNN](docs/architectural-decision-records/NNNN-slug.md)`, right after the sentence that states the decision.
- A decision ships in the same PR as its record. A PR that makes a decision without one is not done.

## Supersede a record

A new record that reverses an old one says `Supersedes 00NN` in its status line. The old record changes its status line to `Superseded by 00MM` and nothing else. The `CLAUDE.md` link moves to the new record in the same PR.

## Index

| Record | Decision | Date | Status |
|---|---|---|---|
| [0001](0001-merge-into-the-watch-activity.md) | hevy2garmin merges Hevy's sets into the watch's own activity | 2026-11-04 | Accepted |
| [0002](0002-mirror-trainer-into-routines.md) | Trainer's program is mirrored into Hevy routines that hevy2garmin carries to the watch | 2026-11-04 | Accepted |
| [0003](0003-own-repo-and-image.md) | The tool lives in its own repo and ships its own image | 2026-11-04 | Accepted |
| [0004](0004-public-gpl-3.md) | The repo is public and licensed GPL-3.0 | 2026-11-04 | Accepted |
| [0005](0005-images-from-ci-prs-only.md) | Images are built only by CI, and main changes only through PRs | 2026-11-04 | Accepted. Tag convention superseded by 0021, approval rule narrowed by 0025 |
| [0006](0006-session-on-a-volume.md) | The Hevy session is bootstrapped once from the whole cookie and then lives only on a volume | 2026-11-04 | Accepted |
| [0007](0007-hourly-cronjob.md) | The mirror runs hourly as a Kubernetes CronJob | 2026-11-04 | Accepted |
| [0008](0008-no-calendar-scheduling.md) | Workouts are not scheduled on the Garmin calendar | 2026-11-04 | Accepted |
| [0009](0009-send-to-device-from-here.md) | This job sends each new Garmin workout to the watch, using hevy2garmin's Garmin session | 2026-11-04 | Accepted |
| [0010](0010-program-week-in-names.md) | Routine names carry the program week, counted from the program's start date | 2026-11-05 | Accepted |
| [0011](0011-ci-bumps-manifests.md) | CI bumps the image tag in Kubernetes-Manifests with one self-merging PR | 2026-11-05 | Accepted |
| [0012](0012-tag-edited-in-place.md) | CI edits the newTag line in place instead of running kustomize edit | 2026-11-05 | Accepted |
| [0013](0013-bluebird-issue-flow.md) | Issues follow Bluebird's create-issue flow and labels | 2026-11-05 | Accepted. Skill location superseded by 0027 |
| [0014](0014-routines-stay-in-hevy.md) | The mirrored routines stay in Hevy after they reach Garmin | 2026-11-05 | Accepted |
| [0015](0015-nothing-upstream-yet.md) | Nothing goes upstream to hevy2garmin until this tool has been polished and tested | 2026-11-05 | Accepted |
| [0016](0016-garmin-keeps-posting-to-strava.md) | Garmin's own Strava connection stays on | 2026-11-05 | Superseded by 0020 |
| [0017](0017-docs-and-records.md) | Docs and decision records are kept the way Bluebird keeps them | 2026-11-05 | Accepted |
| [0018](0018-full-coverage.md) | Every change ships with tests, and coverage stays at 100% of lines and branches | 2026-11-05 | Superseded by 0032 |
| [0019](0019-poll-hevy-every-minute.md) | A poller inside the cluster checks Hevy every 60 seconds and starts hevy2garmin's merge at once | 2026-11-05 | Accepted |
| [0020](0020-the-watch-recording-is-what-strava-keeps.md) | Strava keeps what the watch recorded, so the watch's own recording has to be right, and this tool never uploads to Strava | 2026-11-05 | Accepted. Supersedes 0016 |
| [0021](0021-semver-release-per-merge.md) | Every merge to main cuts a SemVer release, and GitVersion reads the bump from the PR title | 2026-11-05 | Accepted. Supersedes the tag convention of 0005 |
| [0022](0022-scan-before-production.md) | Production moves only onto a scanned image, and the image takes Debian's fixes at build time | 2026-11-05 | Accepted |
| [0023](0023-pinned-actions-and-attestations.md) | Every action is pinned to a commit, and the image carries an SBOM and provenance | 2026-11-05 | Accepted. No-auto-merge consequence superseded by 0025 |
| [0024](0024-branch-protection.md) | Main is protected the way Bluebird's is, with Bluebird's Copilot review ruleset | 2026-11-05 | Accepted; ruleset removed by 0033 |
| [0025](0025-dependabot-with-patch-auto-merge.md) | Dependabot watches pip, Docker and Actions, and patch updates merge themselves | 2026-11-05 | Accepted. Narrows 0005 |
| [0026](0026-security-scanning.md) | GitHub's security scanning is on, and the released image is re-scanned weekly | 2026-11-05 | Accepted |
| [0027](0027-shared-create-issue-skill.md) | The create-issue skill is shared from zimmertr/ai-config, and this repo's specifics live in CLAUDE.md | 2026-11-05 | Accepted |
| [0028](0028-records-in-architectural-decision-records.md) | Decision records live in `docs/architectural-decision-records/`, the name every new project uses | 2026-11-05 | Accepted |
| [0029](0029-repo-files-and-make-targets.md) | The repo carries CONTRIBUTING, NOTICES and a Makefile whose targets mirror CI, each in Docker | 2026-11-05 | Accepted |
| [0030](0030-pr-lint-and-image-checks.md) | Every PR is linted, and builds, scans and smoke-tests the image it would ship | 2026-11-05 | Accepted |
| [0031](0031-immutable-image-tags.md) | Image tags on Docker Hub are immutable | 2026-11-05 | Accepted |
| [0033](0033-no-copilot-review-ruleset.md) | There is no Copilot review ruleset | 2026-11-05 | Accepted |
| [0032](0032-coverage-aims-at-100.md) | Coverage aims at 100% and is reported on every PR, without a floor | 2026-11-05 | Accepted |

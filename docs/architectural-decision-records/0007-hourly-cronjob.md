# 0007. The mirror runs hourly as a Kubernetes CronJob

- Status: Accepted. Amended by 0041
- Date: 2026-11-04 (git: the merge of KM#1818)
- Decider: TJ (git: merger of KM#1818)
- Issues and PRs: KM#1818
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), How it fits together

## Context

The program changes when a workout finishes, when Trainer rotates exercises, and on Monday when the week number moves. None of those need minutes.

## Decision

CronJob `hevy-trainer-sync` in `hevy2garmin-system`, schedule `7 * * * *`, `concurrencyPolicy: Forbid`, one run at a time. The session PVC is mounted read-write.

## Evidence

No dated measurement.

## Alternatives rejected

- A long-running loop: holds the RWO volume permanently and gains nothing for a program that changes a few times a week.

## Consequences

After a workout, the next session's routine gets the new weights within the hour. The Strava path does not wait on this job. Manual runs use `kubectl create job --from=cronjob/hevy-trainer-sync`.

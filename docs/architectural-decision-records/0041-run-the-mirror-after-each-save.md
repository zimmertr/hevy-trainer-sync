# 0041. The poller runs the mirror as soon as a workout is saved, and runs take a lock on the session

- Status: Accepted. Amends 0007
- Date: 2026-11-06
- Decider: TJ ("I AM NOT GOING TO WAIT OR DO THINGS MANUALLY THIS ENTIRE PROCESS MUST BE SEAMLESS", then chose a run on every save over a run every minute)
- Issues and PRs: #52, KM PR to follow
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), How it fits together, the hourly and poller bullets

## Context

The mirror ran only hourly ([0007](0007-hourly-cronjob.md)). Since [0040](0040-the-calendar-carries-workouts-to-the-watch.md) the same run also moves the calendar, so after a session the new weights and the next workout waited up to an hour to reach the watch.

## Decision

- With `RUN_CRONJOB=hevy-trainer-sync` set, the poller creates one Job from that CronJob in its own namespace whenever a poll finds a workout saved or edited after the poller started (`kube.run_cronjob`), the way `kubectl create job --from=cronjob/...` does. Its service account may only get that CronJob and create Jobs.
- Every run holds an exclusive `flock` on `HEVY_STATE_FILE.lock` for its whole length (`state.locked`), so a run started by the poller and one started by the schedule never refresh the session at the same time. The second waits; the Job's 600-second deadline bounds the wait.
- The hourly schedule stays, for Trainer's weekly rotation, Monday's new week name and midnight.

## Evidence

No dated measurement. The program moves when a workout is finished, which is the moment the poller already sees within a minute.

## Alternatives rejected

- The CronJob every minute: about 1,440 reads a day of Hevy's undocumented private API and a dashboard login a minute, nearly all of them finding nothing.
- Running the mirror inside the poller: the poller would need the session volume, which is ReadWriteOnce and belongs to the mirror ([0019](0019-poll-hevy-every-minute.md)).

## Consequences

- The next workout and the new weights reach the calendar a minute or two after Finish in Hevy.
- The poller pod mounts a service account token, which can create Jobs in `hevy2garmin-system`.
- A run that starts while another is on a different node waits for the volume to detach as well as for the lock.
- `test_kube.py`, `test_state.py` (`LockedTest`) and `test_poll.py` (`StartMirrorTest`) hold it.

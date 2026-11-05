# 0008. Workouts are not scheduled on the Garmin calendar

- Status: Accepted
- Date: 2026-11-04 (conversation); the step became opt-in in #17, merged 2026-11-05
- Decider: TJ ("Can't we just delete and recreate without scheduling though? And then automatically send to device?")
- Issues and PRs: #4, #8, #17
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Rules, the calendar bullet

## Context

A Garmin workout reaches the watch on its own only when it is on the calendar. #4 put Trainer's next workout on today's date. Trainer has no fixed training days, so that meant a planned workout on every day until TJ trained.

## Decision

The calendar step stays in the code behind `SCHEDULE_NEXT=1`, off by default, and the CronJob does not set it. Workouts reach the watch through Send to Device instead ([0009](0009-send-to-device-from-here.md)).

## Evidence

- 2026-11-04: TJ's Garmin calendar showed no workout on the Friday he trains arms, because nothing knew which day he would train.
- hevy2garmin's schedule route answers `scheduleId: null` for a single date, so entry ids have to be read from its `routine_schedules` table.

## Alternatives rejected

- Scheduling the next workout on today, every day: a planned entry on every day until you train.
- Fixed weekdays: TJ does not want days assigned statically.

## Consequences

The code is dead until someone sets `SCHEDULE_NEXT=1`. #8 decides whether it stays.

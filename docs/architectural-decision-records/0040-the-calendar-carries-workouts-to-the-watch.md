# 0040. Workouts reach the watch through the Garmin calendar, one planned entry at a time, and Send to Device is off

- Status: Accepted. Supersedes 0008, and turns off the Send to Device step of 0009
- Date: 2026-11-06
- Decider: TJ ("They absolutely cannot just accumulate on my watch. They must be updated in place or disappear after executed.", then chose the calendar over keeping Send to Device)
- Issues and PRs: #8, #51, KM#1916
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Rules, the calendar bullet

## Context

On 2026-11-06 the watch held `Upper` and `Lower` from before the week names, next to `Upper W8` and `Lower W8`. hevy2garmin deletes a Garmin workout and creates a new one whenever its routine changes, and Send to Device ([0009](0009-send-to-device-from-here.md)) copied each new one onto the watch. The watch never drops a copy Send to Device put there. Every weight change after a session and every Monday's new week name would have added another.

## Decision

- The hourly job puts Trainer's next workout on today's date in the Garmin calendar and takes every other entry of its routines off. That covers yesterday's if it was skipped, today's once it's done, and any other date. Exactly one planned entry exists at a time (`schedule.plan`). Finished sessions still show on the calendar as activities.
- After a session, the next workout goes on today at once, so it is on the watch well before the next session.
- When hevy2garmin rebuilds a workout, it moves that workout's calendar entries for today and later onto the new one (`rebookSchedules`), so the calendar entry follows the change.
- The cluster sets `SCHEDULE_NEXT=1`, `SEND_TO_DEVICE=0` and `TZ=America/Los_Angeles`. The defaults in code are unchanged.

## Evidence

- 2026-11-06: TJ found the old `Upper` and `Lower` on the watch after hevy2garmin had deleted them from Garmin Connect. He deleted them on the watch by hand.
- Garmin forum reports agree that Send to Device copies a workout once and does not keep the watch's list in step: an edited or deleted workout stays on the watch until it is deleted there.
- Garmin's manual describes the watch's training calendar as an extension of the Garmin Connect calendar. TrainingPeaks, TrainerRoad and Garmin Coach all deliver workouts through it.
- Still to confirm on the Fenix 8: that a workout taken off the calendar, or replaced by hevy2garmin, leaves the watch at its next sync. This record is updated with the date that is seen.

## Alternatives rejected

- Keeping Send to Device and editing Garmin workouts in place so their ids never change: this tool would have to build Garmin workouts itself instead of hevy2garmin, and nothing shows that the watch replaces a re-sent workout with the same id instead of adding it.
- 0008's reason against the calendar was a planned entry on every day until TJ trained. With every stale entry removed, there is one planned entry at a time.
- 0008's plan kept a finished session's entry. hevy2garmin re-books today's entries onto a rebuilt workout, so that entry turned back into a planned workout that was never done.

## Consequences

- Nothing piles up on the watch, once the calendar is shown to work on it. The copies Send to Device already put there have to be deleted on the watch once.
- The watch offers only Trainer's next workout. A different one has to be picked in Hevy, and the next hourly run moves the calendar to it.
- The calendar code depends on `routine_schedules` in hevy2garmin's database for entry ids ([0009](0009-send-to-device-from-here.md), #13).
- `test_schedule.py` holds the one-entry rule.

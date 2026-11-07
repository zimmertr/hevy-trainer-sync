# 0042. The watch gets Trainer's own prescriptions and cycle week, worked out by the app's rules

- Status: Accepted. Supersedes 0010. Amended by 0043
- Date: 2026-11-06
- Decider: TJ ("It has to come from Hevy. This has to be accurate", then chose following Trainer's progression over the last logged weight, the private API for workout history, warm-up weights, `Upper C2 W2`, and a weekly check for app changes)
- Issues and PRs: #12, #14, #54, #57, #58
- Cited in code as: `trainer_rules.py`, `library.py`, `build.py`, `cli.py`, `hevy_private.py`
- Guide: [`CLAUDE.md`](../../CLAUDE.md), How it fits together, the prescriptions bullet, and Rules, the naming bullet

## Context

Routines carried the last logged weight and a week counted in whole weeks from the program's start time ([0010](0010-program-week-in-names.md)). On 6 Nov 2026 the watch prescribed Chest Fly at 45 lb where Trainer prescribed 50, and the names said `W8` where the app said cycle 2, week 2.

Hevy's servers send neither number (#54, #57). The Android app works both out on the phone, from the program, the user's Trainer workouts and two sets of preferences. Those inputs are all on Hevy's servers.

## Decision

- `trainer_rules.py` follows the app's rules, read from the Android app, version 3.2.5. Each function names the app function it follows. The code is written from the rules, not copied.
  - **Week.** Calendar weeks since the program's `created_at`, starting at local midnight on the user's first weekday. The cycle is 6 weeks, or 7 with deloads, so week 8 is cycle 2, week 2.
  - **Weight.** The app takes the last log of the exercise from the same Trainer template and uses its lightest working set as the base. If every set reached the top of the rep range, the weight goes up 5%. If every set fell short of the bottom, it goes down 5%. Otherwise it stays. The result rounds to a weight the user has. A deload week takes 60%.
  - **Reps.** An exercise logged by reps alone moves its range a rung on a fixed ladder instead.
  - **Warm-ups.** One warm-up gets 60% of the working weight; two get 40% and 60%.
- The inputs come from Hevy:
  - The program.
  - `GET /hevy_trainer/user_preferences`, for the dumbbells, bars and plates the user has.
  - `GET /v2/user_preferences`, for the username, the weight unit and the first weekday.
  - `GET /user_workouts_paged`, because each workout there carries the Trainer template it came from.
  - `library.py`, the app's built-in exercise library, for each exercise's type and equipment. The public API has neither.
- Routines are named `Upper C2 W2`. Old names still match by base title, so the first run renames them in place.
- An exercise Trainer has no prescription for keeps the last logged weight:
  - One new to the program. The app sizes those from a recent one-rep max, which this doesn't follow.
  - One logged by distance or time.
  - One on equipment the app doesn't round to, such as a kettlebell.
- The weekly Hevy App Check downloads the latest app and fingerprints the app functions followed. It also rebuilds the library and opens an issue when either changed. Dropped by [0043](0043-no-check-for-app-updates.md).

## Evidence

- **6 Nov 2026, from the 3 Nov Lower.** The rules raise Side Bend from 35 to 40 lb and move Lying Leg Raise up the ladder. Those are the two exercises the app marked with a green arrow. Everything else stays. Goblet Squat's warm-ups come out at 30 and 50 lb, which is what TJ logged.
- **6 Nov 2026.** The app showed "Cycle 2 (6-Week Program)", week 2/6. `calendar_week` gives week 8, which is cycle 2, week 2.
- **6 Nov 2026.** `current_week` read 5, which is neither number (#14).

## Alternatives rejected

- **The last logged weight:** wrong every time Trainer progresses an exercise.
- **Asking Hevy to put the numbers in its API:** worth asking, but it has no date.
- **Matching workouts to templates by title:** breaks when a workout is renamed.
- **No week in the name:** TJ chose the app's cycle and week.

## Consequences

- An app update can change a rule. The weekly check named the change within a week; since [0043](0043-no-check-for-app-updates.md), a weight that differs from the app's does.
- Each run makes three more private-API reads, on the session the job already owns.
- The repo holds the library's ids, titles, types and equipment, but none of the app's code.
- After a rotation, an exercise new to the program gets the last weight logged for it anywhere, often none, until it has been done once in its template.
- The app rotates exercises on the phone, so the names can show a new cycle before the program's exercises change.
- `test_trainer_rules.py`, and `test_build.py` (`PlanTest`) hold it.

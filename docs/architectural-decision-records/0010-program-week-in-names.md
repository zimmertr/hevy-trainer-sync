# 0010. Routine names carry the program week, counted from the program's start date

- Status: Superseded by [0042](0042-trainer-prescriptions-by-the-apps-rules.md)
- Date: 2026-11-05 (git: the merge of #6)
- Decider: TJ ("Maybe this means we drop cycle and just do Upper - W8 instead")
- Issues and PRs: #6, #14
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Rules, the naming bullet

## Context

Trainer workouts belong to a cycle and a week. A name that says which week a routine was written for makes a stale watch obvious. The API does not expose the app's cycle and week in a usable form.

## Decision

`build.program_week()` counts calendar weeks since the program's `created_at`, 1-based, and `build.title()` names routines `Upper W8`. Existing routines are matched by base title, so Monday's rename updates the routine in place.

## Evidence

- 2026-11-04: the app showed cycle 2, week 2 of a 6-week cycle. The program was created on Monday 14 Sep 2026, and 4 Nov falls in week 8 of that count. The program's `current_week` read 5 the same day.

## Alternatives rejected

- `Upper C2-W2` from `CYCLE_WEEKS=3`: TJ's cycle is 6 weeks, and a guessed cycle length is fragile.
- `current_week`: did not match the app on the one day it was checked.
- No suffix: a stale watch looks the same as a fresh one.

## Consequences

The formula rests on one data point until #14 has a few Mondays of matches. If Hevy regenerates the program, `created_at` moves and the count restarts. `test_build.py` covers the arithmetic and the matching.

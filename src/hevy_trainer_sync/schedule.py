"""Decide what to do with the Garmin calendar. Pure, so the tests cover it.

The calendar is how workouts reach the watch. Garmin keeps calendar workouts
in step with the watch, so a workout that is rebuilt or taken off the calendar
is replaced or removed there too. Send to Device only ever adds, and every
copy it sent stayed on the watch. Decision record 0040.

Trainer has no days, only "next", so the calendar holds exactly one planned
workout of this tool's: the next one, on today's date.
"""

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo


def today_in(tz: str) -> str:
    return datetime.now(ZoneInfo(tz)).date().isoformat()


@dataclass
class Plan:
    unschedule: list[tuple[str, str]] = field(default_factory=list)  # (routine_id, schedule_id)
    schedule: bool = False


def plan(rows: list[tuple[str, str, str | None]], next_routine_id: str, today: str) -> Plan:
    """`rows` are (routine_id, schedule_id, date) for every managed routine.

    Every entry except the next workout on today comes off. A missed day moves
    the entry to today. A finished session's entry comes off too: the
    activity stays on the calendar on its own, and hevy2garmin re-books today's
    entries onto a workout it rebuilds, so the entry would otherwise turn back
    into a planned workout that never gets done. With it gone, the next
    workout goes on today at once and reaches the watch at its next sync.
    """
    out = Plan()
    kept = False
    for routine_id, schedule_id, date in rows:
        if routine_id == next_routine_id and date == today and not kept:
            kept = True
            continue
        out.unschedule.append((routine_id, schedule_id))
    out.schedule = not kept
    return out

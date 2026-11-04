"""Decide what to do with the Garmin calendar. Pure, so the tests cover it.

Trainer has no days, only "next". Putting the next workout on today's date is
what makes the watch offer it as today's workout and, more importantly, what
makes Garmin push it to the watch at all: a workout that only sits in the
library needs Send to Device by hand, and hevy2garmin recreates the Garmin
workout whenever its content changes, which drops that association.
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

    A past entry for the routine that is still "next" was never done, so it
    comes off the calendar instead of lingering as a missed workout. A past
    entry for any other routine was done (Trainer moved on), and stays, since
    Garmin links it to the activity. Nothing is scheduled twice on one day,
    including the day a session was just finished.
    """
    out = Plan()
    for routine_id, schedule_id, date in rows:
        if date and date < today and routine_id == next_routine_id:
            out.unschedule.append((routine_id, schedule_id))
    out.schedule = not any(date == today for _, _, date in rows)
    return out

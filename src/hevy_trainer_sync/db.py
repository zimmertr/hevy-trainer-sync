"""Read hevy2garmin's own Postgres for the one thing its API doesn't return.

The schedule route records the Garmin calendar entry id in `routine_schedules`
but answers with `scheduleId: null`, and nothing lists the table. Unscheduling
needs the id, so it is read straight from the table. Read-only: every write
still goes through the dashboard, which keeps this table in step with Garmin.
"""


def schedules(database_url: str, routine_ids: list[str]) -> list[tuple[str, str, str | None]]:
    """(routine_id, schedule_id, date) for the given routines."""
    if not routine_ids:
        return []
    import psycopg  # imported here so the tests and the dry run need no driver

    with psycopg.connect(database_url, connect_timeout=10) as conn:
        rows = conn.execute(
            "SELECT hevy_routine_id, schedule_id, scheduled_date FROM routine_schedules WHERE hevy_routine_id = ANY(%s)",
            (routine_ids,),
        ).fetchall()
    return [(str(r), str(s), (str(d)[:10] if d else None)) for r, s, d in rows]

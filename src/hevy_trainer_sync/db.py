"""Read hevy2garmin's own Postgres for the things its API doesn't return.

Read-only: every write still goes through the dashboard, which keeps these
tables in step with Garmin. The coupling to its schema is deliberate and
written down in the repo's issues.

- `synced_routines`: the Garmin workout id behind each routine, which Send
  to Device needs and the sync route doesn't return per routine.
- `platform_credentials`: the Garmin DI session the dashboard logged in with,
  so Garmin is never given a second login from here.
- `routine_schedules`: calendar entry ids, for the (optional) calendar step;
  the schedule route answers `scheduleId: null`.
- `synced_workouts`: which Hevy workouts hevy2garmin has finished, so the
  poller knows when to stop waiting on one.
- `app_cache`: the merge settings, so the poller matches a workout to its
  watch activity by the same rules hevy2garmin will.
"""


class DbError(RuntimeError):
    """The database could not be reached or refused the query. The poller waits and tries again."""


def _connect(database_url: str):
    import psycopg  # imported here so the tests and the dry run need no driver

    return psycopg.connect(database_url, connect_timeout=10)


def _rows(database_url: str, sql: str, params: tuple) -> list[tuple]:
    """Run one read for the poller, which must outlive a database restart rather than crash on it."""
    import psycopg

    try:
        with _connect(database_url) as conn:
            return conn.execute(sql, params).fetchall()
    except psycopg.Error as e:
        raise DbError(f"hevy2garmin's database: {e}") from None


def synced_ids(database_url: str, workout_ids: list[str]) -> set[str]:
    """The given Hevy workouts hevy2garmin has a result for: merged, uploaded or skipped."""
    if not workout_ids:
        return set()
    rows = _rows(database_url, "SELECT hevy_id FROM synced_workouts WHERE hevy_id = ANY(%s)", (workout_ids,))
    return {str(r[0]) for r in rows}


def merge_settings(database_url: str) -> dict | None:
    """The `merge_settings` the dashboard's Settings page saved, or None when it never has."""
    rows = _rows(database_url, "SELECT value FROM app_cache WHERE key = %s LIMIT 1", ("merge_settings",))
    value = rows[0][0] if rows else None
    return value if isinstance(value, dict) else None


def schedules(database_url: str, routine_ids: list[str]) -> list[tuple[str, str, str | None]]:
    """(routine_id, schedule_id, date) for the given routines."""
    if not routine_ids:
        return []
    with _connect(database_url) as conn:
        rows = conn.execute(
            "SELECT hevy_routine_id, schedule_id, scheduled_date FROM routine_schedules "
            "WHERE hevy_routine_id = ANY(%s)",
            (routine_ids,),
        ).fetchall()
    return [(str(r), str(s), (str(d)[:10] if d else None)) for r, s, d in rows]


def garmin_workouts(database_url: str, routine_ids: list[str]) -> dict[str, tuple[str, str]]:
    """routine_id -> (garmin_workout_id, title) for routines hevy2garmin has on Garmin."""
    if not routine_ids:
        return {}
    with _connect(database_url) as conn:
        rows = conn.execute(
            "SELECT hevy_routine_id, garmin_workout_id, title FROM synced_routines "
            "WHERE hevy_routine_id = ANY(%s) AND garmin_workout_id IS NOT NULL AND status = 'success'",
            (routine_ids,),
        ).fetchall()
    return {str(r): (str(g), str(t or "")) for r, g, t in rows}


def garmin_di_token(database_url: str) -> str:
    """The dashboard's current Garmin bearer token."""
    rows = _rows(
        database_url,
        "SELECT credentials->'garmin_tokens'->>'di_token' FROM platform_credentials "
        "WHERE platform = 'garmin_tokens'",
        (),
    )
    token = rows[0][0] if rows else None
    if not token:
        raise DbError("hevy2garmin has no Garmin session stored; log in on the dashboard first")
    return token

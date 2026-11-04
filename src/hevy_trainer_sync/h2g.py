"""Drive the hevy2garmin dashboard: push routines to Garmin and put them on the calendar.

The dashboard already holds the Garmin login, so Garmin is never contacted from
here. Its routine routes are session-gated, hence the login first.
"""

from .http import request


class Dashboard:
    def __init__(self, base_url: str, password: str):
        self._base = base_url.rstrip("/")
        _, headers = request("POST", f"{self._base}/api/login", body={"password": password})
        cookie = headers.get("Set-Cookie") or headers.get("set-cookie") or ""
        session = cookie.split(";", 1)[0] if cookie.startswith("h2g_session=") else ""
        self._h = {"Cookie": session} if session else {}

    def sync_routines(self, routine_ids: list[str]) -> dict:
        """Create or replace the Garmin planned workout for each routine."""
        body, _ = request("POST", f"{self._base}/api/routines/sync", headers=self._h, body={"ids": routine_ids}, timeout=300)
        return body or {}

    def schedule(self, routine_id: str, date: str) -> dict:
        """Put the routine's Garmin workout on a calendar date (YYYY-MM-DD)."""
        body, _ = request("POST", f"{self._base}/api/routines/{routine_id}/schedule", headers=self._h, body={"date": date}, timeout=120)
        return body or {}

    def unschedule(self, routine_id: str, schedule_id: str) -> dict:
        body, _ = request("POST", f"{self._base}/api/routines/{routine_id}/unschedule", headers=self._h,
                          body={"scheduleId": schedule_id}, timeout=120)
        return body or {}

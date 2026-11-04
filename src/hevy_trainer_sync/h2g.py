"""Ask the hevy2garmin dashboard to push routines to Garmin as planned workouts.

The dashboard already holds the Garmin login, so Garmin is never contacted from
here. The routine sync route is session-gated, hence the login first.
"""

from .http import request


def sync_routines(base_url: str, password: str, routine_ids: list[str]) -> dict:
    base = base_url.rstrip("/")
    _, headers = request("POST", f"{base}/api/login", body={"password": password})
    cookie = headers.get("Set-Cookie") or headers.get("set-cookie") or ""
    session = cookie.split(";", 1)[0] if cookie.startswith("h2g_session=") else ""
    h = {"Cookie": session} if session else {}
    body, _ = request("POST", f"{base}/api/routines/sync", headers=h, body={"ids": routine_ids}, timeout=300)
    return body or {}

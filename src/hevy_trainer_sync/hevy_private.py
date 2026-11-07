"""Hevy's private API: the one the app uses, not the documented v1 API.

Five calls are made: the session refresh, the Trainer program, Trainer's
preferences, the user's preferences and the user's workouts, the last three
only because the app works out prescribed weights and the program week from
them (trainer_rules.py). The endpoints and headers come from the inventory in
github.com/LovelessCodes/hevy-mcp-unofficial and the Android app (record 0042),
checked live on 4 and 6 Nov 2026. Hevy can change or close them without notice.
"""

import time
from datetime import UTC, datetime

from .http import HttpError, request

BASE = "https://api.hevyapp.com"
# A fixed key the hevy.com web client sends; it identifies the client, not the user.
WEB_API_KEY = "shelobs_hevy_web"
EPOCH = "1970-01-01T00:00:00.000Z"
WORKOUT_PAGE = 10
# A ceiling on paging, far past any program's length at a few workouts a week.
MAX_WORKOUT_PAGES = 50


def parse_time(raw) -> datetime | None:
    """A Hevy time: Unix seconds, as the app keeps a workout's start, or ISO 8601."""
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return datetime.fromtimestamp(raw, UTC)
    if isinstance(raw, str):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return None


def start_of(workout: dict) -> datetime | None:
    return parse_time(workout.get("start_time"))


class Session:
    def __init__(self, tokens: dict, persist):
        self.tokens = tokens
        self._persist = persist

    def _headers(self) -> dict:
        h = {"x-api-key": WEB_API_KEY, "x-client-time": str(time.time())}
        if self.tokens.get("access_token"):
            h["Authorization"] = f"Bearer {self.tokens['access_token']}"
        return h

    def _expired(self) -> bool:
        raw = self.tokens.get("expires_at")
        if not raw or not self.tokens.get("access_token"):
            return True
        exp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return exp <= datetime.now(UTC)

    def refresh(self) -> None:
        # Verified 4 Nov 2026: without the Bearer header, expired or not, Hevy
        # answers 400 "Bad Request" rather than anything that names the cause.
        if not self.tokens.get("access_token"):
            raise RuntimeError("cannot refresh without an access token; bootstrap from the whole auth2.0-token cookie")
        body, _ = request("POST", f"{BASE}/auth/refresh_token", headers=self._headers(),
                          body={"refresh_token": self.tokens["refresh_token"]})
        if not isinstance(body, dict) or not body.get("access_token"):
            raise RuntimeError(f"refresh returned no access token: {body}")
        self.tokens = {
            "access_token": body["access_token"],
            "refresh_token": body.get("refresh_token") or self.tokens["refresh_token"],
            "expires_at": body.get("expires_at"),
        }
        self._persist(self.tokens)

    def _get(self, path: str, query: dict | None = None):
        """GET with the session, refreshed first when it has expired and once more on a 401."""
        if self._expired():
            self.refresh()
        try:
            body, _ = request("GET", f"{BASE}/{path}", headers=self._headers(), query=query)
        except HttpError as e:
            if e.status != 401:
                raise
            self.refresh()
            body, _ = request("GET", f"{BASE}/{path}", headers=self._headers(), query=query)
        return body

    def get_program(self) -> dict:
        """The whole Trainer program: every template plus which one is next."""
        query = {"client_program_updated_at": EPOCH, "client_next_workout_updated_at": EPOCH}
        body = self._get("hevy_trainer/v3/program", query)
        if not isinstance(body, dict) or not isinstance(body.get("program"), dict):
            raise RuntimeError(f"unexpected program response: {str(body)[:200]}")
        return body["program"]

    def _object(self, path: str) -> dict:
        body = self._get(path)
        if not isinstance(body, dict):
            raise RuntimeError(f"unexpected {path} response: {str(body)[:200]}")
        return body

    def trainer_preferences(self) -> dict:
        """Trainer's preferences: `availableWeights` holds the dumbbells, bars and plates weights round to."""
        return self._object("hevy_trainer/user_preferences")

    def user_preferences(self) -> dict:
        """The user's preferences: `username`, `weight_unit` and `first_weekday`."""
        return self._object("v2/user_preferences")

    def workouts_since(self, username: str, since: datetime) -> list[dict]:
        """The user's workouts from `since` on, newest first, each with its `trainer_workout_template_id`.

        The public API's workouts don't say which Trainer template they came
        from, and the app's history for an exercise is that template's alone.
        """
        out: list[dict] = []
        for page in range(MAX_WORKOUT_PAGES):
            body = self._get("user_workouts_paged",
                             {"username": username, "limit": WORKOUT_PAGE, "offset": page * WORKOUT_PAGE})
            batch = body.get("workouts") if isinstance(body, dict) else None
            if not isinstance(batch, list) or not batch:
                break
            out.extend(w for w in batch if (start_of(w) or since) >= since)
            oldest = start_of(batch[-1])
            if len(batch) < WORKOUT_PAGE or (oldest is not None and oldest < since):
                break
        return out

"""Hevy's private API: the one the app uses, not the documented v1 API.

Only two calls are made. The endpoints and headers come from the inventory in
github.com/LovelessCodes/hevy-mcp-unofficial and were checked live on 4 Nov 2026.
Hevy can change or close them without notice.
"""

import json
import logging
import time
from datetime import UTC, datetime

from .http import HttpError, request

BASE = "https://api.hevyapp.com"
# A fixed key the hevy.com web client sends; it identifies the client, not the user.
WEB_API_KEY = "shelobs_hevy_web"
EPOCH = "1970-01-01T00:00:00.000Z"
# Enough for every template's exercises; past it a list is cut short in the log.
SHAPE_ITEMS = 30

log = logging.getLogger("hevy-trainer-sync.trainer")


def shape(value):
    """The reply with every string hidden, so the log shows its structure and numbers but no ids, names or notes.

    Trainer prescribes a weight for each session and the program alone has none
    (#12). The same request also asks for the next workout, which this logs so
    the weights can be found without reading the session from anywhere else.
    """
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        out = [shape(v) for v in value[:SHAPE_ITEMS]]
        if len(value) > SHAPE_ITEMS:
            out.append(f"{len(value) - SHAPE_ITEMS} more")
        return out
    if isinstance(value, str):
        return "str"
    return value


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

    def get_program(self) -> dict:
        """The whole Trainer program: every template plus which one is next."""
        if self._expired():
            self.refresh()
        query = {"client_program_updated_at": EPOCH, "client_next_workout_updated_at": EPOCH}
        try:
            body, _ = request("GET", f"{BASE}/hevy_trainer/v3/program", headers=self._headers(), query=query)
        except HttpError as e:
            if e.status != 401:
                raise
            self.refresh()
            body, _ = request("GET", f"{BASE}/hevy_trainer/v3/program", headers=self._headers(), query=query)
        if not isinstance(body, dict) or not isinstance(body.get("program"), dict):
            raise RuntimeError(f"unexpected program response: {str(body)[:200]}")
        log.info("trainer reply, strings hidden: %s", json.dumps(shape(body), separators=(",", ":")))
        return body["program"]

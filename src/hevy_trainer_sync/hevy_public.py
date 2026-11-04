"""The documented Hevy API (api.hevyapp.com/docs), authenticated with the Pro API key."""

from .http import request

BASE = "https://api.hevyapp.com/v1"
PAGE_SIZE = 10  # the API's maximum for these endpoints


class Client:
    def __init__(self, api_key: str):
        self._h = {"api-key": api_key}

    def _pages(self, path: str, key: str, max_pages: int | None = None):
        page = 1
        while True:
            body, _ = request("GET", f"{BASE}{path}", headers=self._h, query={"page": page, "pageSize": PAGE_SIZE})
            yield from body.get(key, [])
            if page >= int(body.get("page_count") or 1) or (max_pages and page >= max_pages):
                return
            page += 1

    def folders(self) -> list[dict]:
        return list(self._pages("/routine_folders", "routine_folders"))

    def create_folder(self, title: str) -> dict:
        body, _ = request("POST", f"{BASE}/routine_folders", headers=self._h, body={"routine_folder": {"title": title}})
        return body["routine_folder"]

    def routines(self) -> list[dict]:
        return list(self._pages("/routines", "routines"))

    def create_routine(self, routine: dict) -> dict:
        body, _ = request("POST", f"{BASE}/routines", headers=self._h, body={"routine": routine})
        return body["routine"][0] if isinstance(body.get("routine"), list) else body["routine"]

    def update_routine(self, routine_id: str, routine: dict) -> dict:
        body, _ = request("PUT", f"{BASE}/routines/{routine_id}", headers=self._h, body={"routine": routine})
        return body["routine"][0] if isinstance(body.get("routine"), list) else body["routine"]

    def recent_workouts(self, max_pages: int):
        """Newest first."""
        return self._pages("/workouts", "workouts", max_pages=max_pages)

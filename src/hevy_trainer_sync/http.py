"""One thin wrapper over urllib so the three clients share error handling."""

import json
import urllib.error
import urllib.parse
import urllib.request


class HttpError(Exception):
    def __init__(self, status: int, body: str, url: str):
        super().__init__(f"HTTP {status} from {url}: {body[:300]}")
        self.status = status
        self.body = body


def request(method: str, url: str, *, headers: dict | None = None, query: dict | None = None,
            body: dict | list | None = None, timeout: int = 30) -> tuple[dict | list | None, dict]:
    """Return (decoded JSON or None, response headers). Raises HttpError on 4xx/5xx."""
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    data = None
    hdrs = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read()
            return (json.loads(raw) if raw else None), dict(res.headers)
    except urllib.error.HTTPError as e:
        raise HttpError(e.code, e.read().decode(errors="replace"), url) from None

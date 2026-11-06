"""One thin wrapper over urllib so the three clients share error handling."""

import email.utils
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime

# Names this tool to the services it calls, in place of urllib's
# "Python-urllib/3.x". A caller's own User-Agent wins: Garmin's requests carry
# the Android app's (garmin.HEADERS). Decision record 0035.
USER_AGENT = "hevy-trainer-sync (+https://github.com/zimmertr/hevy-trainer-sync)"

# A 429 is retried once, after the wait its Retry-After asks for, when that
# wait is at most this long. A longer wait, or none given, raises: the CronJob
# runs again within the hour and the poller within a minute, so waiting longer
# here only holds a run open. Decision record 0035.
MAX_RETRY_AFTER_S = 60


class HttpError(Exception):
    def __init__(self, status: int, body: str, url: str, headers: dict | None = None):
        super().__init__(f"HTTP {status} from {url}: {body[:300]}")
        self.status = status
        self.body = body
        self.headers = headers or {}


def retry_after_s(value: str | None, *, now=lambda: datetime.now(UTC)) -> float | None:
    """Seconds a Retry-After header asks for, or None when it says nothing usable."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        return None
    return max(0.0, (when - now()).total_seconds())


def _send(req: urllib.request.Request, url: str, timeout: int,
          context: ssl.SSLContext | None = None) -> tuple[dict | list | None, dict]:
    kwargs: dict = {"timeout": timeout}
    if context is not None:
        kwargs["context"] = context
    try:
        with urllib.request.urlopen(req, **kwargs) as res:
            raw = res.read()
            return (json.loads(raw) if raw else None), dict(res.headers)
    except urllib.error.HTTPError as e:
        raise HttpError(e.code, e.read().decode(errors="replace"), url, dict(e.headers or {})) from None


def request(method: str, url: str, *, headers: dict | None = None, query: dict | None = None,
            body: dict | list | None = None, timeout: int = 30, sleep=time.sleep,
            context: ssl.SSLContext | None = None) -> tuple[dict | list | None, dict]:
    """Return (decoded JSON or None, response headers). Raises HttpError on 4xx/5xx.

    `context` verifies a server the system trust store doesn't know, which is
    only the Kubernetes API (kube.py). `sleep` exists for the tests.
    """
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    data = None
    hdrs = {"Accept": "application/json", "User-Agent": USER_AGENT, **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        return _send(req, url, timeout, context)
    except HttpError as e:
        given = {k.lower(): v for k, v in e.headers.items()}.get("retry-after")
        wait = retry_after_s(given) if e.status == 429 else None
        if wait is None or wait > MAX_RETRY_AFTER_S:
            raise
        sleep(wait)
        return _send(req, url, timeout, context)

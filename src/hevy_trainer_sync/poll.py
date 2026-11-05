"""Watch Hevy for finished workouts and start hevy2garmin's merge at once.

hevy2garmin's own schedule holds a workout for two hours so the watch's
activity reaches Garmin first. Its Hevy webhook route skips that wait: it
tries a merge-only sync a few times and uploads a fresh activity only on the
last attempt. Hevy can only call that route from the internet, and nothing in
this cluster is exposed, so this loop stands in for Hevy: it reads the public
API's workout events every POLL_SECONDS and calls the route from inside the
cluster when a workout appears or changes.

It needs no Hevy session and no volume, so it never touches the rotating token
the hourly mirror owns.
"""

import logging
import os
import sys
import time
from datetime import UTC, datetime, timedelta

from .h2g import trigger_merge
from .hevy_public import Client
from .http import HttpError

log = logging.getLogger("hevy-trainer-sync.poll")

# What one failed call can raise: an HTTP status, or no answer at all. URLError,
# timeouts and refused connections are all OSError. Only HttpError was caught
# until 2026-11-05, so a DNS lookup that failed inside the cluster killed the
# loop, and the pod restarted four times in nine hours.
FAILED = (HttpError, OSError)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def new_workouts(events: list[dict], since: datetime) -> list[tuple[str, str, datetime]]:
    """The workouts saved or edited after `since`, oldest first, as (id, title, updated_at).

    Deletions are ignored: there is nothing to merge. Events without a parseable
    `updated_at` are skipped rather than trusted.
    """
    found = []
    for e in events:
        w = e.get("workout") or {}
        if e.get("type") != "updated" or not w.get("id") or not w.get("updated_at"):
            continue
        try:
            updated = parse(w["updated_at"])
        except ValueError:
            continue
        if updated > since:
            found.append((str(w["id"]), str(w.get("title") or ""), updated))
    return sorted(found, key=lambda f: f[2])


def tick(hevy: Client, h2g_url: str, cron_secret: str, since: datetime) -> datetime:
    """One poll. Returns the new high-water mark; unchanged when anything failed, so the next poll tries again."""
    try:
        events = hevy.workout_events(iso(since))
    except FAILED as e:
        log.warning("reading Hevy workout events failed: %s", e)
        return since
    mark = since
    for workout_id, title, updated in new_workouts(events, since):
        try:
            answer = trigger_merge(h2g_url, cron_secret)
        except FAILED as e:
            log.error("asking hevy2garmin to merge %r failed: %s", title, e)
            return mark
        log.info("workout %r (%s) saved; hevy2garmin %s", title, workout_id, answer.get("status") or answer)
        mark = updated
    return mark


def env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name, default)
    if v is None or v == "":
        log.error("%s is not set", name)
        sys.exit(2)
    return v


def main(argv: list[str] | None = None, *, sleep=time.sleep, now=lambda: datetime.now(UTC),
         ticks: int | None = None) -> int:
    """Poll until stopped. `sleep`, `now` and `ticks` exist for the tests."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    hevy = Client(env("HEVY_API_KEY"))
    h2g_url = env("H2G_URL", "http://hevy2garmin")
    cron_secret = env("CRON_SECRET")
    interval = int(env("POLL_SECONDS", "60"))
    # Start one interval back, so a workout saved while the pod was restarting
    # is still picked up. Anything older is the scheduled sync's to handle.
    since = now() - timedelta(seconds=interval)
    log.info("polling Hevy every %ss for saved workouts", interval)
    n = 0
    while ticks is None or n < ticks:
        since = tick(hevy, h2g_url, cron_secret, since)
        n += 1
        if ticks is None or n < ticks:
            sleep(interval)
    return 0

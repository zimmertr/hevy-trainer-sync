"""Watch Hevy for finished workouts and have hevy2garmin merge each one into
the watch's own activity, once that activity is on Garmin.

hevy2garmin's Hevy webhook route tries a merge-only sync a few times, and on
its last attempt uploads a fresh activity when no watch recording turned up.
Garmin posts that upload to Strava as a second activity, and its scheduled
sync does the same after two hours. So this loop does the waiting itself: it
reads the public API's workout events every POLL_SECONDS, holds each new
workout, and looks on Garmin for the watch's recording of it with the same
rules hevy2garmin's merge uses (match.py). Only when the recording is there
does it call the webhook route, whose first attempt then merges. A workout the
watch never recorded is never sent, so nothing but the watch ever reaches
Strava. Decision record 0039.

It needs no Hevy session and no volume, so it never touches the rotating token
the hourly mirror owns. Garmin is read with hevy2garmin's token, borrowed from
its database the way Send to Device does (decision record 0009).
"""

import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from . import db, match
from .garmin import Garmin
from .h2g import Dashboard, trigger_merge
from .hevy_public import Client
from .http import HttpError

log = logging.getLogger("hevy-trainer-sync.poll")

# What one failed call can raise: an HTTP status, no answer at all, or the
# database. URLError, timeouts and refused connections are all OSError. Only
# HttpError was caught until 2026-11-05, so a DNS lookup that failed inside the
# cluster killed the loop, and the pod restarted four times in nine hours.
FAILED = (HttpError, OSError, db.DbError)

# How long a workout waits for its watch recording. A sync that late means the
# watch was left behind; the workout stays in Hevy only. Also how far back the
# poller reads on start, so a restart forgets nothing it was waiting on.
GIVE_UP = timedelta(hours=48)

# hevy2garmin's webhook retry runs for about half an hour. Past that with no
# merge recorded, it is asked again.
ASK_AGAIN = timedelta(minutes=30)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@dataclass
class Workout:
    id: str
    title: str
    updated: datetime
    start: datetime
    end: datetime
    asked: datetime | None = None


def new_workouts(events: list[dict], since: datetime) -> list[Workout]:
    """The workouts saved or edited after `since`, oldest edit first.

    Deletions are ignored: there is nothing to merge. Events without a parseable
    `updated_at`, `start_time` or `end_time` are skipped rather than trusted.
    """
    found = []
    for e in events:
        w = e.get("workout") or {}
        if e.get("type") != "updated" or not w.get("id"):
            continue
        try:
            updated, start, end = parse(w["updated_at"]), parse(w["start_time"]), parse(w["end_time"])
        except (KeyError, TypeError, ValueError):
            continue
        if updated > since:
            found.append(Workout(str(w["id"]), str(w.get("title") or ""), updated, start, end))
    return sorted(found, key=lambda f: f.updated)


class Poller:
    def __init__(self, hevy: Client, h2g_url: str, cron_secret: str, database_url: str, password: str,
                 since: datetime):
        self.hevy = hevy
        self.h2g_url = h2g_url
        self.cron_secret = cron_secret
        self.database_url = database_url
        self.password = password
        self.since = since
        self.waiting: dict[str, Workout] = {}

    def tick(self, now: datetime) -> None:
        """One poll: take in what Hevy saved, then settle what is waiting."""
        self.read_hevy()
        if self.waiting:
            try:
                self.settle(now)
            except FAILED as e:
                log.warning("checking the waiting workouts failed, trying again next poll: %s", e)

    def read_hevy(self) -> None:
        try:
            events = self.hevy.workout_events(iso(self.since))
        except FAILED as e:
            log.warning("reading Hevy workout events failed: %s", e)
            return
        for w in new_workouts(events, self.since):
            old = self.waiting.get(w.id)
            if old is None:
                log.info("workout %r (%s) saved; waiting for the watch's activity on Garmin", w.title, w.id)
            else:
                w.asked = old.asked
            self.waiting[w.id] = w
            self.since = max(self.since, w.updated)

    def settle(self, now: datetime) -> None:
        for wid in db.synced_ids(self.database_url, list(self.waiting)):
            w = self.waiting.pop(wid)
            log.info("workout %r (%s) is on Garmin; done", w.title, wid)
        for w in [w for w in self.waiting.values() if now - w.end > GIVE_UP]:
            del self.waiting[w.id]
            log.warning("no watch activity turned up for %r (%s) in %s; it stays in Hevy only",
                        w.title, w.id, GIVE_UP)
        if not self.waiting:
            return
        # hevy2garmin's webhook route takes no workout id: it syncs the newest
        # workout it has not finished. Asking while a newer one is waiting
        # would have it pick that one, find no watch activity, and upload it on
        # its last attempt. So only the newest waiting workout is ever asked
        # about, and the others wait their turn.
        newest = max(self.waiting.values(), key=lambda w: w.start)
        if newest.asked is not None and now - newest.asked < ASK_AGAIN:
            return
        s = match.settings(db.merge_settings(self.database_url))
        if not s.enabled or s.watch_strategy != "merge":
            # Either way hevy2garmin would upload instead of merging.
            log.error("hevy2garmin's merge is off or not set to merge (%s, %s); not asking it to sync %r",
                      s.enabled, s.watch_strategy, newest.title)
            return
        activity = match.find(newest.start, newest.end, self.activities(newest), s, now)
        if activity is None:
            return
        answer = trigger_merge(self.h2g_url, self.cron_secret)
        newest.asked = now
        log.info("watch activity %s found for %r (%s); hevy2garmin %s", activity.get("activityId"),
                 newest.title, newest.id, answer.get("status") or answer)

    def activities(self, w: Workout) -> list[dict]:
        # A day either side: Garmin searches by the watch's local date, which
        # can be a day off the UTC one. The matcher drops whatever is too far.
        dates = ((w.start - timedelta(days=1)).date().isoformat(), (w.end + timedelta(days=1)).date().isoformat())
        garmin = Garmin(db.garmin_di_token(self.database_url))
        try:
            return garmin.activities(*dates)
        except HttpError as e:
            if e.status != 401:
                raise
        # The dashboard's token had expired. An empty routine sync makes it
        # build its Garmin client, which refreshes and stores the token.
        log.info("Garmin refused the stored token; asking hevy2garmin to refresh it")
        Dashboard(self.h2g_url, self.password).sync_routines([])
        return Garmin(db.garmin_di_token(self.database_url)).activities(*dates)


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
    poller = Poller(
        Client(env("HEVY_API_KEY")),
        env("H2G_URL", "http://hevy2garmin"),
        env("CRON_SECRET"),
        env("DATABASE_URL"),
        env("H2G_PASSWORD"),
        # Back as far as a workout is waited on, so a restart picks up every
        # workout still waiting. Ones hevy2garmin already has drop out on the
        # first poll.
        now() - GIVE_UP,
    )
    interval = int(env("POLL_SECONDS", "60"))
    log.info("polling Hevy every %ss for saved workouts", interval)
    n = 0
    while ticks is None or n < ticks:
        poller.tick(now())
        n += 1
        if ticks is None or n < ticks:
            sleep(interval)
    return 0

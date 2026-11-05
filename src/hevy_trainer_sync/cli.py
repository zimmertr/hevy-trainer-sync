"""One run: read the Trainer program, write one routine per template, tell hevy2garmin, put the next one on today."""

import argparse
import logging
import os
import sys

from . import build, db, schedule, state
from .garmin import Garmin
from .h2g import Dashboard
from .hevy_private import Session
from .hevy_public import Client
from .http import HttpError

log = logging.getLogger("hevy-trainer-sync")

NOTES = "Managed by hevy-trainer-sync from the Hevy Trainer program. Edits here are overwritten."


def env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name, default)
    if v is None or v == "":
        log.error("%s is not set", name)
        sys.exit(2)
    return v


def send_to_device(database_url: str, dashboard: Dashboard, routine_ids: list[str]) -> int:
    """Queue each routine's Garmin workout for the watch; it downloads them at its next phone sync."""
    workouts = db.garmin_workouts(database_url, routine_ids)
    if not workouts:
        log.warning("no Garmin workouts recorded for the routines just synced; nothing sent to the watch")
        return 0
    garmin = Garmin(db.garmin_di_token(database_url))
    device = os.environ.get("GARMIN_DEVICE_ID")
    try:
        device_id = int(device) if device else garmin.last_used_device_id()
    except HttpError as e:
        if e.status != 401:
            raise
        # The dashboard's token had expired after all. An empty sync makes it
        # build its Garmin client, which refreshes and stores the token.
        log.info("Garmin refused the stored token; asking hevy2garmin to refresh it")
        dashboard.sync_routines([])
        garmin = Garmin(db.garmin_di_token(database_url))
        device_id = int(device) if device else garmin.last_used_device_id()
    failed = 0
    for routine_id in routine_ids:
        if routine_id not in workouts:
            continue
        workout_id, title = workouts[routine_id]
        try:
            garmin.send_workout(workout_id, title, device_id)
            log.info("sent %s (Garmin workout %s) to device %s", title, workout_id, device_id)
        except HttpError as e:
            failed += 1
            log.error("send to device failed for %s: %s", title, e)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # `poll` is the long-running watcher (poll.py); everything else is one mirror run.
    if argv[:1] == ["poll"]:
        from . import poll
        return poll.main(argv[1:])
    ap = argparse.ArgumentParser(prog="hevy-trainer-sync")
    ap.add_argument(
        "--dry-run", action="store_true", help="read everything, write nothing (tokens are still refreshed)"
    )
    ap.add_argument("--force", action="store_true", help="trigger the hevy2garmin sync even when no routine changed")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    state_file = env("HEVY_STATE_FILE", "/state/hevy-session.json")
    # First run: the hevy.com cookie, pasted whole, saved to the state file at
    # once. After this the file is the only valid copy, because the refresh
    # token rotates.
    try:
        tokens, bootstrapped = state.load_or_bootstrap(state_file, os.environ.get("HEVY_SESSION"))
    except ValueError as e:
        log.error("%s", e)
        return 2
    if bootstrapped:
        log.info("no state at %s, bootstrapped from HEVY_SESSION and saved it", state_file)

    session = Session(tokens, lambda t: state.save(state_file, t))
    program = session.get_program()
    templates = sorted(program.get("templates", []), key=lambda t: t.get("index", 0))
    nxt = program.get("next_workout_index")
    next_template = templates[nxt] if isinstance(nxt, int) and 0 <= nxt < len(templates) else None
    log.info("program %s: %d templates, next is %s, variety=%s, rotated %s",
             program.get("id"), len(templates),
             build.title_from_key(next_template["key"]) if next_template else "?",
             program.get("program_variety"), program.get("exercises_rotated_at"))
    if not templates:
        log.error("the program has no templates; nothing to mirror")
        return 1

    hevy = Client(env("HEVY_API_KEY"))
    wanted = {ex["exercise_template_id"] for t in templates for ex in t.get("exercises", [])}
    weights = build.last_weights(hevy.recent_workouts(int(env("WORKOUT_PAGES", "4"))), wanted)
    log.info("weights known for %d of %d exercises", len(weights), len(wanted))

    folder_title = env("FOLDER_TITLE", "Hevy Trainer")
    folder = next((f for f in hevy.folders() if f.get("title") == folder_title), None)
    if folder is None:
        log.info("creating routine folder %r", folder_title)
        folder = {"id": None} if args.dry_run else hevy.create_folder(folder_title)
    folder_id = folder.get("id")
    existing = (
        {r["title"]: r for r in hevy.routines() if r.get("folder_id") == folder_id} if folder_id is not None else {}
    )

    # Every routine this job owns, by base title, whether it existed or was just made.
    week = build.program_week(program.get("created_at"))
    log.info("program week %s (started %s)", week, program.get("created_at"))
    managed: dict[str, str] = {}
    changed: list[str] = []
    for t in templates:
        base = build.title_from_key(t["key"])
        payload = build.routine_from_template(t, folder_id, weights, NOTES,
                                              title_override=build.title(t["key"], week))
        # Matched by base title, so a routine named for last week is renamed, not duplicated.
        current = next((r for title, r in existing.items() if build.is_titled_from(title, t["key"])), None)
        if current:
            managed[base] = str(current["id"])
        if current and build.normalize(current) == build.normalize(payload):
            log.info("%s: unchanged", payload["title"])
            continue
        verb = (
            f"update ({current['title']} -> {payload['title']})"
            if current and current["title"] != payload["title"]
            else ("update" if current else "create")
        )
        log.info(
            "%s: %s (%d exercises)%s",
            payload["title"],
            verb,
            len(payload["exercises"]),
            " [dry run]" if args.dry_run else "",
        )
        if args.dry_run:
            continue
        saved = hevy.update_routine(current["id"], payload) if current else hevy.create_routine(payload)
        managed[base] = str(saved["id"])
        changed.append(str(saved["id"]))

    if args.dry_run:
        log.info("dry run: not touching hevy2garmin")
        return 0

    dashboard = Dashboard(env("H2G_URL", "http://hevy2garmin"), env("H2G_PASSWORD"))
    to_push = list(managed.values()) if args.force else changed
    if to_push:
        result = dashboard.sync_routines(to_push)
        log.info(
            "hevy2garmin: synced=%s skipped=%s failed=%s",
            result.get("synced"),
            result.get("skipped"),
            result.get("failed"),
        )
        for r in result.get("results", []):
            log.info("  %s: %s %s", r.get("title"), r.get("status"), r.get("error") or "")
        if not result.get("ok"):
            return 1
    else:
        log.info("nothing to push to Garmin")

    database_url = os.environ.get("DATABASE_URL")

    # Send to Device, for every routine that just got a new Garmin workout. The
    # sync call above made hevy2garmin touch Garmin, so its stored token is fresh.
    if database_url and to_push and os.environ.get("SEND_TO_DEVICE", "1") == "1":
        if send_to_device(database_url, dashboard, to_push) != 0:
            return 1

    # The calendar, opt-in: puts the next workout on today's date (see schedule.py).
    if not database_url or next_template is None or os.environ.get("SCHEDULE_NEXT", "0") != "1":
        return 0
    next_id = managed.get(build.title_from_key(next_template["key"]))
    if not next_id:
        log.warning("next workout %r has no routine yet; nothing scheduled", build.title_from_key(next_template["key"]))
        return 0
    today = schedule.today_in(env("TZ", "UTC"))
    rows = db.schedules(database_url, list(managed.values()))
    plan = schedule.plan(rows, next_id, today)
    for routine_id, schedule_id in plan.unschedule:
        r = dashboard.unschedule(routine_id, schedule_id)
        log.info("unscheduled stale entry %s: %s", schedule_id, "ok" if r.get("ok") else r.get("error"))
    if plan.schedule:
        r = dashboard.schedule(next_id, today)
        log.info(
            "scheduled %s on %s: %s",
            build.title_from_key(next_template["key"]),
            today,
            "ok" if r.get("ok") else r.get("error"),
        )
        if not r.get("ok"):
            return 1
    else:
        log.info("calendar already has a workout on %s", today)
    return 0

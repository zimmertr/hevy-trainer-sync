"""One run: read the Trainer program, write one routine per template, tell hevy2garmin."""

import argparse
import logging
import os
import sys

from . import build, h2g, state
from .hevy_private import Session
from .hevy_public import Client

log = logging.getLogger("hevy-trainer-sync")

NOTES = "Managed by hevy-trainer-sync from the Hevy Trainer program. Edits here are overwritten."


def env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name, default)
    if v is None or v == "":
        log.error("%s is not set", name)
        sys.exit(2)
    return v


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hevy-trainer-sync")
    ap.add_argument("--dry-run", action="store_true", help="read everything, write nothing (tokens are still refreshed)")
    ap.add_argument("--force", action="store_true", help="trigger the hevy2garmin sync even when no routine changed")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    state_file = env("HEVY_STATE_FILE", "/state/hevy-session.json")
    tokens = state.load(state_file)
    if tokens is None:
        # First run: the refresh token pasted from the hevy.com cookie. After this
        # the file is the only valid copy, because the token rotates.
        tokens = {"refresh_token": env("HEVY_REFRESH_TOKEN")}
        log.info("no state at %s, bootstrapping from HEVY_REFRESH_TOKEN", state_file)

    session = Session(tokens, lambda t: state.save(state_file, t))
    program = session.get_program()
    templates = sorted(program.get("templates", []), key=lambda t: t.get("index", 0))
    nxt = program.get("next_workout_index")
    log.info("program %s: %d templates, next is %s, variety=%s, rotated %s",
             program.get("id"), len(templates),
             build.title_from_key(templates[nxt]["key"]) if isinstance(nxt, int) and nxt < len(templates) else "?",
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
    existing = {r["title"]: r for r in hevy.routines() if r.get("folder_id") == folder_id} if folder_id is not None else {}

    changed: list[str] = []
    for t in templates:
        payload = build.routine_from_template(t, folder_id, weights, NOTES)
        current = existing.get(payload["title"])
        if current and build.normalize(current) == build.normalize(payload):
            log.info("%s: unchanged", payload["title"])
            continue
        verb = "update" if current else "create"
        log.info("%s: %s (%d exercises)%s", payload["title"], verb, len(payload["exercises"]), " [dry run]" if args.dry_run else "")
        if args.dry_run:
            continue
        saved = hevy.update_routine(current["id"], payload) if current else hevy.create_routine(payload)
        changed.append(str(saved["id"]))

    if args.force and not args.dry_run:
        changed = [str(r["id"]) for r in existing.values()] + [c for c in changed if c not in {str(r["id"]) for r in existing.values()}]
    if not changed:
        log.info("nothing to push to Garmin")
        return 0
    result = h2g.sync_routines(env("H2G_URL", "http://hevy2garmin"), env("H2G_PASSWORD"), changed)
    log.info("hevy2garmin: synced=%s skipped=%s failed=%s", result.get("synced"), result.get("skipped"), result.get("failed"))
    for r in result.get("results", []):
        log.info("  %s: %s %s", r.get("title"), r.get("status"), r.get("error") or "")
    return 0 if result.get("ok") else 1

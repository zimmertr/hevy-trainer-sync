"""Pure functions: Trainer template in, routine payload out. No I/O, so this is what the tests cover."""

import re
from datetime import datetime, timezone

_FREQ = re.compile(r"^\d+x$")


def title_from_key(key: str) -> str:
    """'lower_2x_a' -> 'Lower', 'full_body_3x_b' -> 'Full Body'.

    The private API only exposes the template key; the app's display title is
    the words before the weekly-frequency token.
    """
    words = []
    for tok in key.split("_"):
        if _FREQ.match(tok):
            break
        words.append(tok.capitalize())
    return " ".join(words) or key


def program_week(created_at: str | None, now: datetime | None = None) -> int | None:
    """Calendar weeks since the program started, 1-based: what the app's cycle and week multiply out to.

    The program's own `current_week` is not this (it read 5 when the app showed
    cycle 2, week 2 of a 6-week cycle, i.e. week 8), so it is not used.
    """
    if not created_at:
        return None
    try:
        start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    now = now or datetime.now(timezone.utc)
    days = (now - start).days
    return days // 7 + 1 if days >= 0 else None


def title(key: str, week: int | None) -> str:
    """'Upper W8': the base title plus the program week, so a stale watch is obvious at a glance."""
    base = title_from_key(key)
    return f"{base} W{week}" if isinstance(week, int) and week >= 1 else base


def is_titled_from(routine_title: str, key: str) -> bool:
    """Whether an existing routine is this template's, whatever week it was named for."""
    base = title_from_key(key)
    return routine_title == base or routine_title.startswith(f"{base} W")


def routine_from_template(template: dict, folder_id: int | None, weights_kg: dict[str, float], notes: str,
                          title_override: str | None = None) -> dict:
    """A create/update payload for the public API, in Trainer's exercise order.

    Warm-up sets carry no weight: Trainer decides those on the day. Working sets
    get the rep range Trainer prescribes and the weight from the last logged
    session, which is the best guess the public API can give.
    """
    exercises = []
    for ex in sorted(template.get("exercises", []), key=lambda e: e.get("index", 0)):
        tid = ex["exercise_template_id"]
        rr = ex.get("rep_range") or {}
        rep_range = {"start": rr["start"], "end": rr["end"]} if "start" in rr and "end" in rr else None
        # rep_range is sent only when there is one. POST /routines accepts
        # rep_range: null, but PUT /routines/{id} rejects it with "Expected
        # object, received null", which failed the first rename on 2026-11-05.
        warmup = {"type": "warmup", "weight_kg": None, "reps": None}
        working = {"type": "normal", "weight_kg": weights_kg.get(tid), "reps": None}
        if rep_range:
            working["rep_range"] = rep_range
        sets = [dict(warmup) for _ in range(int(ex.get("warmup_set_count") or 0))]
        sets += [dict(working) for _ in range(int(ex.get("set_count") or 0))]
        exercises.append({
            "exercise_template_id": tid,
            "superset_id": None,
            "rest_seconds": ex.get("rest_seconds"),
            "notes": None,
            "sets": sets,
        })
    return {"title": title_override or title_from_key(template["key"]), "folder_id": folder_id, "notes": notes, "exercises": exercises}


def _norm_set(s: dict) -> tuple:
    rr = s.get("rep_range") or {}
    w = s.get("weight_kg")
    return (s.get("type"), round(float(w), 2) if w is not None else None, s.get("reps"),
            (rr.get("start"), rr.get("end")) if rr else None)


def normalize(routine: dict) -> tuple:
    """The parts of a routine that matter, in a comparable shape, from either a payload or a GET response."""
    return (
        routine.get("title"),
        tuple(
            (e.get("exercise_template_id"), e.get("rest_seconds"), tuple(_norm_set(s) for s in e.get("sets", [])))
            for e in routine.get("exercises", [])
        ),
    )


def last_weights(workouts, template_ids: set[str]) -> dict[str, float]:
    """The last working-set weight per exercise, scanning workouts newest first.

    Hevy progresses weight only when every set hits the top of the range, so the
    final working set of the most recent session is the number to pre-fill.
    """
    found: dict[str, float] = {}
    wanted = set(template_ids)
    for w in workouts:
        for ex in w.get("exercises", []):
            tid = ex.get("exercise_template_id")
            if tid not in wanted:
                continue
            working = [s for s in ex.get("sets", []) if s.get("type") != "warmup" and s.get("weight_kg") is not None]
            if working:
                found[tid] = float(working[-1]["weight_kg"])
                wanted.discard(tid)
        if not wanted:
            break
    return found

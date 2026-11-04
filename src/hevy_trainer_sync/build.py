"""Pure functions: Trainer template in, routine payload out. No I/O, so this is what the tests cover."""

import re

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


def routine_from_template(template: dict, folder_id: int | None, weights_kg: dict[str, float], notes: str) -> dict:
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
        sets = [{"type": "warmup", "weight_kg": None, "reps": None, "rep_range": None}
                for _ in range(int(ex.get("warmup_set_count") or 0))]
        sets += [{"type": "normal", "weight_kg": weights_kg.get(tid), "reps": None, "rep_range": rep_range}
                 for _ in range(int(ex.get("set_count") or 0))]
        exercises.append({
            "exercise_template_id": tid,
            "superset_id": None,
            "rest_seconds": ex.get("rest_seconds"),
            "notes": None,
            "sets": sets,
        })
    return {"title": title_from_key(template["key"]), "folder_id": folder_id, "notes": notes, "exercises": exercises}


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

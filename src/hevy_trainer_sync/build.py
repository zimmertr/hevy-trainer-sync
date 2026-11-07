"""Pure functions: Trainer template in, routine payload out. No I/O, so this is what the tests cover."""

import re
from dataclasses import dataclass

from . import library, trainer_rules
from .hevy_private import start_of

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


def title(key: str, cycle: int | None = None, week: int | None = None) -> str:
    """'Upper C2 W2': the base title plus Trainer's cycle and week, as the app shows them."""
    base = title_from_key(key)
    return f"{base} C{cycle} W{week}" if cycle and week else base


def is_titled_from(routine_title: str, key: str) -> bool:
    """Whether an existing routine is this template's, whatever week it was named for, old style or new."""
    return re.fullmatch(rf"{re.escape(title_from_key(key))}( C\d+)?( W\d+)?", routine_title) is not None


@dataclass(frozen=True)
class Planned:
    """One exercise as Trainer would prescribe it today, in kilograms for the routine."""
    direction: str
    weight_kg: float | None
    warmups_kg: tuple
    rep_range: dict | None
    weight: float | None = None
    unit: str = "kg"


def to_log(sets: list[dict]) -> list[dict]:
    """toExerciseLog: a missing rep count or weight counts as zero."""
    return [
        {"indicator": s.get("indicator") or s.get("type"), "reps": s.get("reps") or 0,
         "weight_kg": s.get("weight_kg") or 0}
        for s in sets
    ]


def exercise_logs(workouts: list[dict], template_id: str, exercise_id: str, deload_on) -> list[list[dict]]:
    """extractExerciseLogs: this exercise's sets from this template's workouts, oldest first, deload weeks out."""
    picked = []
    for w in workouts:
        if w.get("trainer_workout_template_id") != template_id:
            continue
        ex = next((e for e in w.get("exercises") or [] if e.get("exercise_template_id") == exercise_id), None)
        start = start_of(w)
        if ex is None or start is None or deload_on(start):
            continue
        picked.append((start, to_log(ex.get("sets") or [])))
    return [log for _, log in sorted(picked, key=lambda p: p[0])]


def _kg(weight: float, unit: str) -> float:
    return weight if unit == "kg" else trainer_rules.lbs_to_kg(weight)


def plan_exercise(template: dict, ex: dict, workouts: list[dict], available: dict, unit: str, deload: bool,
                  deload_on) -> Planned | None:
    """getTrainerExerciseProgression for one exercise: by weight, by reps, or None when Trainer suggests nothing."""
    tid = ex["exercise_template_id"]
    known = library.EXERCISES.get(tid)
    if known is None or ex.get("kind") != "resistance" or not template.get("id"):
        return None
    _, kind, category = known
    rep_range = ex.get("rep_range") or {}
    if "start" not in rep_range or "end" not in rep_range:
        return None
    logs = exercise_logs(workouts, template["id"], tid, deload_on)
    set_count = int(ex.get("set_count") or 0)
    if kind == "reps_only":
        p = trainer_rules.reps_prescription(logs, set_count, rep_range, deload)
        return Planned(p.direction, None, (), p.rep_range)
    eq = trainer_rules.equipment_for(category, unit, available)
    if kind not in trainer_rules.WEIGHT_TYPES or eq is None:
        return None
    p = trainer_rules.weight_prescription(logs, set_count, rep_range, ex.get("warmup_set_count"), eq, deload)
    if p is None:
        return None
    return Planned(p.direction, _kg(p.weight, unit), tuple(_kg(w, unit) for w in p.warmups), None, p.weight, unit)


def plan(templates: list[dict], workouts: list[dict], available: dict, unit: str, deload: bool,
         deload_on) -> dict[str, dict[str, Planned]]:
    """Trainer's prescription for every exercise, by template id, then exercise template id."""
    out: dict[str, dict[str, Planned]] = {}
    for t in templates:
        planned = {}
        for ex in t.get("exercises", []):
            p = plan_exercise(t, ex, workouts, available, unit, deload, deload_on)
            if p is not None:
                planned[ex["exercise_template_id"]] = p
        out[str(t.get("id"))] = planned
    return out


def routine_from_template(template: dict, folder_id: int | None, weights_kg: dict[str, float], notes: str,
                          title_override: str | None = None, planned: dict[str, Planned] | None = None) -> dict:
    """A create/update payload for the public API, in Trainer's exercise order.

    Each exercise takes Trainer's prescription where there is one (`planned`):
    the working weight, the warm-up weights and, for exercises logged by reps
    alone, the rep range. Without one, working sets keep the last logged
    weight and warm-ups go without.
    """
    planned = planned or {}
    exercises = []
    for ex in sorted(template.get("exercises", []), key=lambda e: e.get("index", 0)):
        tid = ex["exercise_template_id"]
        p = planned.get(tid)
        rr = (p.rep_range if p and p.rep_range else None) or ex.get("rep_range") or {}
        rep_range = {"start": rr["start"], "end": rr["end"]} if "start" in rr and "end" in rr else None
        # rep_range is sent only when there is one. POST /routines accepts
        # rep_range: null, but PUT /routines/{id} rejects it with "Expected
        # object, received null", which failed the first rename on 2026-11-05.
        weight = p.weight_kg if p and p.weight_kg is not None else weights_kg.get(tid)
        working = {"type": "normal", "weight_kg": weight, "reps": None}
        if rep_range:
            working["rep_range"] = rep_range
        warmups = p.warmups_kg if p else ()
        sets = [
            {"type": "warmup", "weight_kg": warmups[i] if i < len(warmups) else None, "reps": None}
            for i in range(int(ex.get("warmup_set_count") or 0))
        ]
        sets += [dict(working) for _ in range(int(ex.get("set_count") or 0))]
        exercises.append({
            "exercise_template_id": tid,
            "superset_id": None,
            "rest_seconds": ex.get("rest_seconds"),
            "notes": None,
            "sets": sets,
        })
    return {
        "title": title_override or title_from_key(template["key"]),
        "folder_id": folder_id,
        "notes": notes,
        "exercises": exercises,
    }


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

    The fallback for an exercise Trainer has no prescription for, such as one
    new to the program, which the app sizes from a recent one-rep max instead.
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

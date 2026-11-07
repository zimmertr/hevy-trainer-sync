"""Hevy Trainer's own rules for the program week, the weights, the rep ranges and the warm-ups.

Hevy's servers send none of these: the app works them out on the phone, from
the program, the user's Trainer workouts and two sets of preferences. These
functions follow the Android app's, read from version 3.2.5 on 2026-11-06, and
each docstring names the app function it follows. They are written from the
rules, not copied. Nothing watches for an app update that changes them: the
app shows its own weight beside the watch's every session, so a mismatch is
how it shows. Decision records 0042 and 0043, docs/DATA.md.

Weights inside these functions are in the exercise's unit (lbs or kg) except
where a name ends in _kg, as in the app.
"""

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo

LBS_PER_KG = 2.20462
CYCLE_WEEKS = 6
FIRST_WEEK = 1
REP_LADDER = ((4, 6), (6, 8), (8, 12), (12, 15), (15, 20), (20, 25), (25, 30))
WARMUP_SHARES = {0: (), 1: (0.6,), 2: (0.4, 0.6)}
WEEKDAYS = {"sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4, "friday": 5, "saturday": 6}
# The app's DEFAULT_AVAILABLE_WEIGHTS, used where Trainer's preferences have no list.
DEFAULT_WEIGHTS = {
    "platesKg": [25, 20, 15, 10, 5, 2.5, 1.25],
    "platesLbs": [45, 25, 10, 5, 2.5],
    "barsKg": [20],
    "barsLbs": [45],
    "dumbbellsKg": [2.5, 5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5, 25, 27.5, 30, 35, 40, 45, 50],
    "dumbbellsLbs": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100],
}
SUPPORTED_EQUIPMENT = ("machine", "dumbbell", "barbell")
WEIGHT_TYPES = ("weight_reps", "bodyweight_reps")


def js_round(x: float) -> int:
    """JavaScript's Math.round: halves go up, not to even."""
    return math.floor(x + 0.5)


def round2(x: float) -> float:
    """roundToTwoDecimal."""
    return js_round(x * 100) / 100


def round3(x: float) -> float:
    """roundToThreeDecimals."""
    return js_round(x * 1000) / 1000


def lbs_to_kg(lbs: float) -> float:
    """exactLbsToKg."""
    return lbs / LBS_PER_KG


def in_unit(kg: float, unit: str) -> float:
    """weight: a kilogram value in the exercise's unit, to two decimals."""
    return round2(kg * LBS_PER_KG if unit == "lbs" else kg)


# The program week


def _start_of_week(d: date, first: int) -> date:
    """startOfWeek: back a day at a time until the weekday is the first one."""
    js_day = (d.weekday() + 1) % 7
    return d - timedelta(days=(js_day - first) % 7)


def calendar_week(created_at: datetime, now: datetime, first_weekday: str, tz: tzinfo) -> int:
    """calendarWeekOf: whole weeks between the weeks holding the program's start and now, plus one.

    Weeks start at midnight on the user's first weekday, in their own time zone.
    """
    first = WEEKDAYS.get(first_weekday, WEEKDAYS["monday"])
    start = _start_of_week(created_at.astimezone(tz).date(), first)
    current = _start_of_week(now.astimezone(tz).date(), first)
    return (current - start).days // 7 + FIRST_WEEK


def weeks_in_cycle(deloads: bool) -> int:
    """getWeeksInCycle: a deload week makes a seventh."""
    return CYCLE_WEEKS + 1 if deloads else CYCLE_WEEKS


def cycle_number(week: int, deloads: bool) -> int:
    """getCycleNumber."""
    return (max(FIRST_WEEK, week) - FIRST_WEEK) // weeks_in_cycle(deloads) + 1


def week_of_cycle(week: int, deloads: bool) -> int:
    """getWeekOfCycle."""
    return (max(FIRST_WEEK, week) - FIRST_WEEK) % weeks_in_cycle(deloads) + 1


def is_deload_week(week: int, deloads: bool) -> bool:
    """isDeloadWeek."""
    return week_of_cycle(week, deloads) > CYCLE_WEEKS


# Equipment and rounding


@dataclass(frozen=True)
class Equipment:
    kind: str
    unit: str
    increment: float = 0
    available: tuple = ()
    bars: tuple = ()
    plates: tuple = ()


def equipment_for(category: str | None, unit: str, weights: dict) -> Equipment | None:
    """getWeightSuggestionEquipment, for the three kinds the app suggests weights for."""
    kg = unit == "kg"

    def pick(key: str) -> tuple:
        name = f"{key}{'Kg' if kg else 'Lbs'}"
        values = weights.get(name)
        return tuple(values if isinstance(values, list) else DEFAULT_WEIGHTS[name])

    if category == "machine":
        return Equipment("machine", unit, increment=2.5 if kg else 5)
    if category == "dumbbell":
        return Equipment("dumbbell", unit, available=pick("dumbbells"))
    if category == "barbell":
        return Equipment("barbell", unit, bars=pick("bars"), plates=pick("plates"))
    return None


def _nearest(target: float, options: list[float]) -> float | None:
    best = None
    for w in options:
        if best is None or abs(w - target) < abs(best - target):
            best = w
    return best


def _in_direction(target: float, options: list[float], direction: str, current: float) -> float | None:
    """pickWeightInDirection: the target if it is available, else the closest step in that direction."""
    if direction == "none":
        return current
    exact = target if target in options else None
    if direction == "increase":
        between = [w for w in options if current < w < target]
        above = next((w for w in options if w > target), None)
        candidates = (exact, between[-1] if between else None, above)
    else:
        between = next((w for w in options if target < w < current), None)
        below = next((w for w in reversed(options) if w < target), None)
        candidates = (exact, between, below)
    return next((c for c in candidates if c is not None), None)


def _pick(target: float, options: list[float], direction: str | None, current: float | None) -> float | None:
    """pickWeight: the nearest option unless a direction and the current weight are known."""
    if not direction or current is None:
        return _nearest(target, options)
    return _in_direction(target, options, direction, current)


def _plate_loads(plates: tuple, limit: float) -> set[float]:
    """fewestPlatesForEachLoad's keys: every per-side load the plates can make, up to the limit."""
    usable = [p for p in plates if p > 0]
    seen = {0.0}
    frontier = [0.0]
    while frontier:
        nxt = []
        for load in frontier:
            for p in usable:
                total = round3(load + p)
                if total <= limit and total not in seen:
                    seen.add(total)
                    nxt.append(total)
        frontier = nxt
    return seen


def loadable_barbell_weights(eq: Equipment, limit: float) -> list[float]:
    """loadableBarbellWeights: every bar plus two equal sides, up to the limit plus two of the biggest plate."""
    ceiling = limit + 2 * max([0, *eq.plates])
    bars = [b for b in eq.bars if b > 0] or DEFAULT_WEIGHTS["barsKg" if eq.unit == "kg" else "barsLbs"]
    out = set()
    for bar in bars:
        for load in _plate_loads(eq.plates, (ceiling - bar) / 2):
            out.add(round3(bar + load * 2))
    return sorted(out)


def adjust(target_kg: float, eq: Equipment, direction: str | None = None, current: float | None = None) -> float | None:
    """adjustWeightForEquipment: the target as a weight the user can actually load, or None."""
    target = in_unit(target_kg, eq.unit)
    if eq.kind == "machine":
        steps = target / eq.increment
        if direction == "increase":
            return math.ceil(steps) * eq.increment
        if direction == "decrease":
            return math.floor(steps) * eq.increment
        return js_round(steps) * eq.increment
    if eq.kind == "dumbbell":
        if not eq.available:
            return None
        # The app rounds dumbbell exercises to pairs: the logged weight is both dumbbells.
        return _pick(target, [w * 2 for w in sorted(eq.available)], direction, current)
    loads = loadable_barbell_weights(eq, max(target, current or 0))
    return _pick(target, loads, direction, current)


# Weight progression


def _normal_sets(log: list[dict]) -> list[dict]:
    return [s for s in log if s.get("indicator") == "normal"]


def evaluate(log: list[dict], set_count: int, rep_range: dict) -> tuple[str, float, float] | None:
    """evaluateLastPerformance: direction, base weight and target weight, all from the working sets.

    The base is the lightest working set. Every set at or past the top of the
    range adds 5%; every set short of the bottom takes 5% off; fewer sets than
    the target, or anything in between, keeps the base.
    """
    sets = _normal_sets(log)
    if not sets:
        return None
    base = min(s["weight_kg"] for s in sets)
    if len(sets) < set_count:
        return ("none", base, base)
    if all(s["reps"] >= rep_range["end"] for s in sets):
        return ("increase", base, base * 1.05)
    if all(s["reps"] < rep_range["start"] for s in sets):
        return ("decrease", base, base * 0.95)
    return ("none", base, base)


def warmup_weights(weight: float | None, count: int, eq: Equipment) -> list[float]:
    """calculateWarmupWeights: 60% for one warm-up; 40% and 60% for two."""
    if not weight or count == 0:
        return []
    kg = weight if eq.unit == "kg" else lbs_to_kg(weight)
    out = [w for share in WARMUP_SHARES[count] if (w := adjust(kg * share, eq)) is not None]
    return out[:2]


def normalize_warmups(count) -> int:
    """normalizeWarmupSetCount: none, one or two."""
    if not isinstance(count, (int, float)) or not math.isfinite(count) or count <= 0:
        return 0
    return 2 if count >= 2 else 1


@dataclass(frozen=True)
class Prescription:
    """What the watch should show for one exercise. A None weight means Trainer has no suggestion."""
    direction: str
    weight: float | None = None
    warmups: tuple = ()
    rep_range: dict | None = None


def weight_prescription(logs: list[list[dict]], set_count: int, rep_range: dict, warmup_count: int,
                        eq: Equipment, deload: bool) -> Prescription | None:
    """calculateTrainerWeightSuggestion for an exercise Trainer has seen before.

    `logs` are the exercise's sets from this template's past workouts, oldest
    first, deload weeks left out; the newest is the one that counts. With no
    past log the app guesses from a recent one-rep max, which this doesn't
    follow, so it returns None and the caller keeps the last logged weight.
    """
    if not logs:
        return None
    ev = evaluate(logs[-1], set_count, rep_range)
    if ev is None:
        return None
    direction, base_kg, target_kg = ev
    weight = adjust(target_kg, eq, direction, in_unit(base_kg, eq.unit))
    if weight is None:
        return None
    warmups = normalize_warmups(warmup_count)
    if deload:
        # lightenForDeload: 60% of the suggestion, rounded to the nearest weight
        # there is. Rounding to the nearest can't fail where the step above
        # succeeded, so the `or` only mirrors the app keeping the suggestion.
        kg = weight if eq.unit == "kg" else lbs_to_kg(weight)
        light = adjust(kg * 0.6, eq) or weight
        return Prescription("deload", light, tuple(warmup_weights(light, warmups, eq)))
    return Prescription(direction, weight, tuple(warmup_weights(weight, warmups, eq)))


# Rep-range progression, for exercises logged by reps alone


def next_range_up(rep_range: dict) -> dict | None:
    """nextRepRangeUp: the first rung that starts at or past this range's top."""
    rung = next(((s, e) for s, e in REP_LADDER if s >= rep_range["end"]), None)
    return {"start": rung[0], "end": rung[1]} if rung else None


def next_range_down(rep_range: dict) -> dict | None:
    """nextRepRangeDown: the last rung that starts below this range's bottom."""
    rung = next(((s, e) for s, e in reversed(REP_LADDER) if s < rep_range["start"]), None)
    return {"start": rung[0], "end": rung[1]} if rung else None


def _reps_step(log: list[dict], set_count: int, rep_range: dict) -> tuple[str, dict] | None:
    """computeRepsProgression: the same test as for weight, moving the range a rung instead."""
    sets = _normal_sets(log)
    if not sets:
        return None
    if len(sets) < set_count:
        return ("none", rep_range)
    if all(s["reps"] >= rep_range["end"] for s in sets):
        up = next_range_up(rep_range)
        return ("increase", up) if up else ("none", rep_range)
    if all(s["reps"] < rep_range["start"] for s in sets):
        down = next_range_down(rep_range)
        return ("decrease", down) if down else ("none", rep_range)
    return ("none", rep_range)


def reps_prescription(logs: list[list[dict]], set_count: int, base_range: dict, deload: bool) -> Prescription:
    """calculateTrainerRepsSuggestion: replay every past log from the program's range, a rung at a time."""
    rep_range, direction = base_range, "none"
    for log in logs:
        step = _reps_step(log, set_count, rep_range)
        if step:
            direction, rep_range = step
    if deload:
        return Prescription("deload", rep_range=next_range_down(rep_range) or rep_range)
    if not logs:
        return Prescription("learning", rep_range=base_range)
    return Prescription(direction, rep_range=rep_range)

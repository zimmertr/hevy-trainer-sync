"""Decide whether Garmin already has the watch's recording of a Hevy workout.

A port of hevy2garmin's `findMergeMatch` (typescript/src/merge-match.ts), with
every rule and the score kept the same. It has to agree with hevy2garmin: the
poller asks for a merge only once this finds the watch activity, and
hevy2garmin then runs its own copy of these rules. If ours said yes and its
said no, its webhook retry would end by uploading a second activity, which
Garmin would post to Strava. Decision record 0039.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

# Garmin sets `duration` only once an activity is saved, and a clock slightly
# ahead can make a finished one look as if it ends in the future.
FUTURE_MARGIN = timedelta(minutes=5)


@dataclass(frozen=True)
class Settings:
    """The merge half of hevy2garmin's Settings page, as its sync engine reads it."""

    enabled: bool = True
    watch_strategy: str = "merge"
    activity_types: tuple[str, ...] = ("strength_training",)
    overlap: float = 0.7
    max_drift_minutes: float = 20


def _num(stored: dict, key: str, fallback: float) -> float:
    # JavaScript's Number(): a missing key is NaN and takes the default, but
    # null and "" are 0. Kept, so a strange stored value means the same here.
    if key not in stored:
        return fallback
    v = stored[key]
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return fallback


def settings(stored: dict | None) -> Settings:
    """Settings from hevy2garmin's `merge_settings` row, the way its loadSyncSettings parses them."""
    d = Settings()
    if not isinstance(stored, dict):
        return d
    enabled = stored.get("merge_mode")
    strategy = str(stored.get("merge_watch_strategy", d.watch_strategy))
    types = stored.get("merge_activity_types")
    types = tuple(str(t) for t in types if t) if isinstance(types, list) else d.activity_types
    return Settings(
        enabled=enabled if isinstance(enabled, bool) else d.enabled,
        watch_strategy=strategy if strategy in ("merge", "replace", "describe") else d.watch_strategy,
        activity_types=types or d.activity_types,
        # Stored as a percentage for the form, used as a fraction.
        overlap=_num(stored, "merge_overlap_pct", 70) / 100,
        max_drift_minutes=_num(stored, "merge_max_drift_min", d.max_drift_minutes),
    )


def utc(ts: str | None) -> datetime | None:
    """hevy2garmin's toUtcDate: a time with no zone is UTC."""
    if not ts:
        return None
    iso = ts if "T" in ts else ts.replace(" ", "T", 1)
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def find(start: datetime, end: datetime, activities: list[dict], s: Settings, now: datetime) -> dict | None:
    """The best saved watch activity for a workout from `start` to `end`, or None."""
    workout_s = (end - start).total_seconds()
    if workout_s <= 0:
        return None
    best, best_score = None, None
    for act in activities:
        if ((act.get("activityType") or {}).get("typeKey") or "") not in s.activity_types:
            continue
        duration = act.get("duration") or 0
        if duration <= 0:
            continue
        act_start = utc(act.get("startTimeGMT") or act.get("startTimeLocal"))
        if act_start is None:
            continue
        act_end = act_start + timedelta(seconds=duration)
        if act_end > now + FUTURE_MARGIN:
            continue
        overlap_s = max(0.0, (min(end, act_end) - max(start, act_start)).total_seconds())
        overlap = overlap_s / workout_s
        if overlap < s.overlap:
            continue
        drift = abs((act_start - start).total_seconds()) / 60
        if drift > s.max_drift_minutes:
            continue
        score = overlap * 100 - drift * 0.5
        if best_score is None or score > best_score:
            best, best_score = act, score
    return best

import unittest
from datetime import UTC, datetime, timedelta

from hevy_trainer_sync import match

START = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)
END = START + timedelta(minutes=60)
NOW = END + timedelta(minutes=10)
S = match.Settings()


def act(aid=1, start="2026-11-06 18:02:00", minutes=60, kind="strength_training", **extra):
    return {"activityId": aid, "startTimeGMT": start, "duration": minutes * 60,
            "activityType": {"typeKey": kind}, **extra}


class SettingsTest(unittest.TestCase):
    def test_nothing_saved_is_hevy2garmins_defaults(self):
        for stored in (None, "text", []):
            self.assertEqual(match.settings(stored), match.Settings())
        self.assertEqual(match.settings({}), match.Settings())

    def test_saved_values_are_read_like_the_dashboard_reads_them(self):
        s = match.settings({"merge_mode": False, "merge_watch_strategy": "replace",
                            "merge_activity_types": ["strength_training", "", "hiit"],
                            "merge_overlap_pct": 50, "merge_max_drift_min": "30"})
        self.assertEqual(s, match.Settings(False, "replace", ("strength_training", "hiit"), 0.5, 30.0))

    def test_odd_values_fall_back_as_javascript_would(self):
        s = match.settings({"merge_mode": "yes", "merge_watch_strategy": "other", "merge_activity_types": [],
                            "merge_overlap_pct": None, "merge_max_drift_min": "soon"})
        # Number(null) is 0, so a null overlap matches anything; Number("soon") is NaN, so the default.
        self.assertEqual(s, match.Settings(True, "merge", ("strength_training",), 0.0, 20))
        self.assertEqual(match.settings({"merge_overlap_pct": ""}).overlap, 0.0)
        self.assertEqual(match.settings({"merge_overlap_pct": [1]}).overlap, 0.7)
        self.assertEqual(match.settings({"merge_activity_types": "strength"}).activity_types, ("strength_training",))


class UtcTest(unittest.TestCase):
    def test_a_time_without_a_zone_is_utc(self):
        self.assertEqual(match.utc("2026-11-06 18:00:00"), START)
        self.assertEqual(match.utc("2026-11-06T18:00:00"), START)

    def test_zones_are_honoured(self):
        self.assertEqual(match.utc("2026-11-06T18:00:00Z"), START)
        self.assertEqual(match.utc("2026-11-06T10:00:00-08:00"), START)

    def test_nothing_or_nonsense_is_none(self):
        for ts in (None, "", "yesterday"):
            self.assertIsNone(match.utc(ts))


class FindTest(unittest.TestCase):
    def test_the_watch_recording_matches(self):
        self.assertEqual(match.find(START, END, [act()], S, NOW)["activityId"], 1)

    def test_local_time_is_used_when_gmt_is_missing(self):
        a = act(start=None, startTimeLocal="2026-11-06 18:02:00")
        self.assertIsNotNone(match.find(START, END, [a], S, NOW))

    def test_each_rule_rejects(self):
        cases = {
            "another sport": act(kind="indoor_climbing"),
            "no type at all": {**act(), "activityType": None},
            "still recording": act(minutes=0),
            "no duration": {k: v for k, v in act().items() if k != "duration"},
            "no start": act(start=None),
            "ends in the future": act(minutes=200),
            "covers too little": act(minutes=30),
            "starts too far off": act(start="2026-11-06 17:30:00", minutes=120),
        }
        for why, a in cases.items():
            with self.subTest(why):
                self.assertIsNone(match.find(START, END, [a], S, NOW + timedelta(minutes=60)
                                             if why != "ends in the future" else NOW))

    def test_a_workout_with_no_length_matches_nothing(self):
        self.assertIsNone(match.find(START, START, [act()], S, NOW))

    def test_the_best_score_wins(self):
        later = act(aid=2, start="2026-11-06 18:10:00", minutes=55)
        closer = act(aid=3, start="2026-11-06 18:01:00", minutes=60)
        self.assertEqual(match.find(START, END, [later, closer, act(aid=4, start="2026-11-06 18:05:00")],
                                    S, NOW)["activityId"], 3)

    def test_settings_widen_the_rules(self):
        wide = match.Settings(activity_types=("hiit",), overlap=0.4, max_drift_minutes=40)
        hiit = act(kind="hiit", start="2026-11-06 18:30:00", minutes=30)
        self.assertIsNotNone(match.find(START, END, [hiit], wide, NOW))


if __name__ == "__main__":
    unittest.main()

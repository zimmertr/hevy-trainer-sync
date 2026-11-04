import unittest

from hevy_trainer_sync import build

TEMPLATE = {
    "key": "upper_2x_a",
    "index": 1,
    "exercises": [
        {"exercise_template_id": "B", "index": 1, "kind": "resistance", "set_count": 3, "warmup_set_count": 0,
         "rep_range": {"start": 10, "end": 12}, "rest_seconds": 90},
        {"exercise_template_id": "A", "index": 0, "kind": "resistance", "set_count": 3, "warmup_set_count": 2,
         "rep_range": {"start": 4, "end": 6}, "rest_seconds": 150},
    ],
}


class TitleTest(unittest.TestCase):
    def test_strips_frequency_and_variant(self):
        self.assertEqual(build.title_from_key("lower_2x_a"), "Lower")
        self.assertEqual(build.title_from_key("full_body_3x_b"), "Full Body")
        self.assertEqual(build.title_from_key("push"), "Push")


class RoutineTest(unittest.TestCase):
    def test_orders_by_index_and_expands_sets(self):
        r = build.routine_from_template(TEMPLATE, 7, {"A": 36.29}, "n")
        self.assertEqual(r["title"], "Upper")
        self.assertEqual(r["folder_id"], 7)
        self.assertEqual([e["exercise_template_id"] for e in r["exercises"]], ["A", "B"])
        a = r["exercises"][0]
        self.assertEqual(a["rest_seconds"], 150)
        self.assertEqual([s["type"] for s in a["sets"]], ["warmup", "warmup", "normal", "normal", "normal"])
        self.assertIsNone(a["sets"][0]["weight_kg"])
        self.assertEqual(a["sets"][2]["weight_kg"], 36.29)
        self.assertEqual(a["sets"][2]["rep_range"], {"start": 4, "end": 6})
        self.assertIsNone(r["exercises"][1]["sets"][0]["weight_kg"])  # unknown weight stays empty

    def test_normalize_matches_get_response_shape(self):
        payload = build.routine_from_template(TEMPLATE, 7, {"A": 36.29}, "n")
        # What GET /v1/routines returns: extra fields, index, title, float weight.
        fetched = {
            "id": "x", "title": "Upper", "folder_id": 7, "updated_at": "…",
            "exercises": [
                {"index": 0, "title": "Seal Row", "exercise_template_id": "A", "rest_seconds": 150, "notes": None,
                 "superset_id": None, "sets": [
                     {"index": 0, "type": "warmup", "weight_kg": None, "reps": None, "rep_range": None},
                     {"index": 1, "type": "warmup", "weight_kg": None, "reps": None, "rep_range": None},
                     {"index": 2, "type": "normal", "weight_kg": 36.290001, "reps": None, "rep_range": {"start": 4, "end": 6}},
                     {"index": 3, "type": "normal", "weight_kg": 36.29, "reps": None, "rep_range": {"start": 4, "end": 6}},
                     {"index": 4, "type": "normal", "weight_kg": 36.29, "reps": None, "rep_range": {"start": 4, "end": 6}}]},
                {"index": 1, "title": "Fly", "exercise_template_id": "B", "rest_seconds": 90, "notes": None,
                 "superset_id": None, "sets": [
                     {"index": 0, "type": "normal", "weight_kg": None, "reps": None, "rep_range": {"start": 10, "end": 12}},
                     {"index": 1, "type": "normal", "weight_kg": None, "reps": None, "rep_range": {"start": 10, "end": 12}},
                     {"index": 2, "type": "normal", "weight_kg": None, "reps": None, "rep_range": {"start": 10, "end": 12}}]},
            ],
        }
        self.assertEqual(build.normalize(payload), build.normalize(fetched))
        fetched["exercises"][1]["rest_seconds"] = 120
        self.assertNotEqual(build.normalize(payload), build.normalize(fetched))


class WeightsTest(unittest.TestCase):
    def test_newest_session_last_working_set_wins(self):
        workouts = [
            {"exercises": [{"exercise_template_id": "A", "sets": [
                {"type": "warmup", "weight_kg": 20}, {"type": "normal", "weight_kg": 40}, {"type": "normal", "weight_kg": 42.5}]}]},
            {"exercises": [{"exercise_template_id": "A", "sets": [{"type": "normal", "weight_kg": 30}]},
                           {"exercise_template_id": "B", "sets": [{"type": "normal", "weight_kg": 10}]}]},
        ]
        self.assertEqual(build.last_weights(iter(workouts), {"A", "B", "C"}), {"A": 42.5, "B": 10.0})

    def test_stops_scanning_once_everything_is_found(self):
        def gen():
            yield {"exercises": [{"exercise_template_id": "A", "sets": [{"type": "normal", "weight_kg": 1}]}]}
            raise AssertionError("scanned further than needed")
        self.assertEqual(build.last_weights(gen(), {"A"}), {"A": 1.0})


if __name__ == "__main__":
    unittest.main()

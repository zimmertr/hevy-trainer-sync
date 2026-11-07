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

    def test_never_sends_rep_range_null(self):
        # PUT /routines/{id} rejects rep_range: null ("Expected object, received null").
        no_range = {"key": "lower_2x_a", "exercises": [
            {"exercise_template_id": "C", "index": 0, "set_count": 2, "warmup_set_count": 1, "rest_seconds": 60}]}
        for template in (TEMPLATE, no_range):
            r = build.routine_from_template(template, 7, {}, "n")
            for ex in r["exercises"]:
                for s in ex["sets"]:
                    self.assertFalse("rep_range" in s and s["rep_range"] is None, s)
        self.assertNotIn("rep_range", build.routine_from_template(TEMPLATE, 7, {}, "n")["exercises"][0]["sets"][0])

    def test_normalize_matches_get_response_shape(self):
        payload = build.routine_from_template(TEMPLATE, 7, {"A": 36.29}, "n")
        # What GET /v1/routines returns: extra fields, index, title, float weight.
        fetched = {
            "id": "x",
            "title": "Upper",
            "folder_id": 7,
            "updated_at": "…",
            "exercises": [
                {
                    "index": 0,
                    "title": "Seal Row",
                    "exercise_template_id": "A",
                    "rest_seconds": 150,
                    "notes": None,
                    "superset_id": None,
                    "sets": [
                        {"index": 0, "type": "warmup", "weight_kg": None, "reps": None, "rep_range": None},
                        {"index": 1, "type": "warmup", "weight_kg": None, "reps": None, "rep_range": None},
                        {
                            "index": 2,
                            "type": "normal",
                            "weight_kg": 36.290001,
                            "reps": None,
                            "rep_range": {"start": 4, "end": 6},
                        },
                        {
                            "index": 3,
                            "type": "normal",
                            "weight_kg": 36.29,
                            "reps": None,
                            "rep_range": {"start": 4, "end": 6},
                        },
                        {
                            "index": 4,
                            "type": "normal",
                            "weight_kg": 36.29,
                            "reps": None,
                            "rep_range": {"start": 4, "end": 6},
                        },
                    ],
                },
                {
                    "index": 1,
                    "title": "Fly",
                    "exercise_template_id": "B",
                    "rest_seconds": 90,
                    "notes": None,
                    "superset_id": None,
                    "sets": [
                        {
                            "index": 0,
                            "type": "normal",
                            "weight_kg": None,
                            "reps": None,
                            "rep_range": {"start": 10, "end": 12},
                        },
                        {
                            "index": 1,
                            "type": "normal",
                            "weight_kg": None,
                            "reps": None,
                            "rep_range": {"start": 10, "end": 12},
                        },
                        {
                            "index": 2,
                            "type": "normal",
                            "weight_kg": None,
                            "reps": None,
                            "rep_range": {"start": 10, "end": 12},
                        },
                    ],
                },
            ],
        }
        self.assertEqual(build.normalize(payload), build.normalize(fetched))
        fetched["exercises"][1]["rest_seconds"] = 120
        self.assertNotEqual(build.normalize(payload), build.normalize(fetched))


class WeightsTest(unittest.TestCase):
    def test_newest_session_last_working_set_wins(self):
        workouts = [
            {
                "exercises": [
                    {
                        "exercise_template_id": "A",
                        "sets": [
                            {"type": "warmup", "weight_kg": 20},
                            {"type": "normal", "weight_kg": 40},
                            {"type": "normal", "weight_kg": 42.5},
                        ],
                    }
                ]
            },
            {
                "exercises": [
                    {"exercise_template_id": "A", "sets": [{"type": "normal", "weight_kg": 30}]},
                    {"exercise_template_id": "B", "sets": [{"type": "normal", "weight_kg": 10}]},
                ]
            },
        ]
        self.assertEqual(build.last_weights(iter(workouts), {"A", "B", "C"}), {"A": 42.5, "B": 10.0})

    def test_stops_scanning_once_everything_is_found(self):
        def gen():
            yield {"exercises": [{"exercise_template_id": "A", "sets": [{"type": "normal", "weight_kg": 1}]}]}
            raise AssertionError("scanned further than needed")
        self.assertEqual(build.last_weights(gen(), {"A"}), {"A": 1.0})

    def test_session_without_a_weighted_working_set_is_skipped(self):
        workouts = [
            {"exercises": [{"exercise_template_id": "A", "sets": [
                {"type": "warmup", "weight_kg": 20}, {"type": "normal", "weight_kg": None}]}]},
            {"exercises": [{"exercise_template_id": "A", "sets": [{"type": "normal", "weight_kg": 35}]}]},
        ]
        self.assertEqual(build.last_weights(workouts, {"A"}), {"A": 35.0})


if __name__ == "__main__":
    unittest.main()


LB = 2.20462


def _set(lbs, reps, indicator="normal"):
    return {"indicator": indicator, "reps": reps, "weight_kg": None if lbs is None else lbs / LB}


def _ex(tid, n=3, warmups=0, rr=(10, 12), kind="resistance", index=0):
    return {"index": index, "exercise_template_id": tid, "kind": kind, "set_count": n, "warmup_set_count": warmups,
            "rep_range": {"start": rr[0], "end": rr[1]}}


# Real library ids: Side Bend (Dumbbell), Lying Leg Raise (reps only), Goblet
# Squat (dumbbell) and Walking Lunge (Dumbbell, logged by distance).
SIDE_BEND, LEG_RAISE, GOBLET, LUNGE = "026FD047", "09C9F635", "3D0C7C75", "A733CC5B"
DUMBBELLS = {"dumbbellsLbs": [5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5, 25, 30, 35, 40, 45, 50]}
NEVER = lambda dt: False  # noqa: E731


def _workout(template_id, start, *exercises):
    return {"trainer_workout_template_id": template_id, "start_time": start,
            "exercises": [{"exercise_template_id": tid, "sets": sets} for tid, sets in exercises]}


class WeekTitleTest(unittest.TestCase):
    def test_title_with_and_without_cycle_and_week(self):
        self.assertEqual(build.title("upper_2x_a", 2, 2), "Upper C2 W2")
        self.assertEqual(build.title("full_body_3x_b"), "Full Body")
        self.assertEqual(build.title("upper_2x_a", None, 2), "Upper")

    def test_existing_routine_is_recognised_across_weeks_and_styles(self):
        for title in ("Upper", "Upper W8", "Upper C2 W2", "Upper C10 W6"):
            self.assertTrue(build.is_titled_from(title, "upper_2x_a"), title)
        for title in ("Upper Body", "Lower W7", "Upper C2 W2 copy", "Upper Chest"):
            self.assertFalse(build.is_titled_from(title, "upper_2x_a"), title)

    def test_override_sets_the_payload_title(self):
        r = build.routine_from_template(TEMPLATE, 7, {}, "n", title_override="Upper C2 W2")
        self.assertEqual(r["title"], "Upper C2 W2")


class LogsTest(unittest.TestCase):
    def test_to_log_reads_either_set_shape_and_zeroes_blanks(self):
        self.assertEqual(build.to_log([{"indicator": "normal", "reps": 8, "weight_kg": 20},
                                       {"type": "warmup", "reps": None, "weight_kg": None}]),
                         [{"indicator": "normal", "reps": 8, "weight_kg": 20},
                          {"indicator": "warmup", "reps": 0, "weight_kg": 0}])

    def test_only_this_templates_workouts_with_the_exercise_oldest_first(self):
        workouts = [
            _workout("L", 300, (SIDE_BEND, [_set(40, 12)])),
            _workout("U", 250, (SIDE_BEND, [_set(99, 12)])),          # another template
            _workout("L", 200, (GOBLET, [_set(80, 4)])),               # without the exercise
            _workout("L", None, (SIDE_BEND, [_set(1, 1)])),             # no start
            _workout("L", 100, (SIDE_BEND, [_set(35, 12)])),
            _workout("L", 150, (SIDE_BEND, [_set(37, 12)])),
        ]
        logs = build.exercise_logs(workouts, "L", SIDE_BEND, lambda dt: dt.timestamp() == 150)
        self.assertEqual([round(log[0]["weight_kg"] * LB) for log in logs], [35, 40])


class PlanTest(unittest.TestCase):
    TEMPLATE = {"id": "L", "key": "lower_2x_a", "exercises": [
        _ex(GOBLET, warmups=2, rr=(4, 6), index=0), _ex(LUNGE, index=1), _ex(LEG_RAISE, index=2),
        _ex(SIDE_BEND, index=3)]}
    WORKOUTS = [_workout("L", 1762211594,
                         (GOBLET, [_set(30, 6, "warmup"), _set(50, 4, "warmup"), *[_set(80, 4)] * 3]),
                         (LUNGE, [_set(25, None)] * 3),
                         (LEG_RAISE, [_set(None, 15)] * 3),
                         (SIDE_BEND, [_set(35, 15), _set(35, 12), _set(35, 12)]))]

    def test_the_3_november_lower_gives_what_the_app_showed(self):
        plan = build.plan([self.TEMPLATE], self.WORKOUTS, DUMBBELLS, "lbs", False, NEVER)["L"]
        side = plan[SIDE_BEND]
        self.assertEqual((side.direction, side.weight, side.unit), ("increase", 40, "lbs"))
        self.assertAlmostEqual(side.weight_kg, 40 / LB)
        goblet = plan[GOBLET]
        self.assertEqual((goblet.direction, goblet.weight), ("none", 80))
        self.assertEqual([round(w * LB) for w in goblet.warmups_kg], [30, 50])
        self.assertEqual(plan[LEG_RAISE].rep_range, {"start": 12, "end": 15})
        self.assertIsNone(plan[LEG_RAISE].weight_kg)
        self.assertNotIn(LUNGE, plan)  # logged by distance: Trainer suggests nothing

    def test_kilograms_stay_kilograms(self):
        workouts = [_workout("L", 1, (SIDE_BEND, [{"indicator": "normal", "reps": 12, "weight_kg": 20}] * 3))]
        p = build.plan([self.TEMPLATE], workouts, {"dumbbellsKg": [10, 10.5, 11]}, "kg", False, NEVER)["L"][SIDE_BEND]
        self.assertEqual((p.weight, p.weight_kg, p.unit), (21, 21, "kg"))

    def test_nothing_without_a_template_id_library_entry_resistance_kind_or_rep_range(self):
        cases = [
            {"id": None, "key": "x", "exercises": [_ex(SIDE_BEND)]},
            {"id": "L", "key": "x", "exercises": [_ex("NOTINLIB")]},
            {"id": "L", "key": "x", "exercises": [_ex(SIDE_BEND, kind="cardio")]},
            {"id": "L", "key": "x", "exercises": [{**_ex(SIDE_BEND), "rep_range": {}}]},
            {"id": "L", "key": "x", "exercises": [_ex("4F5866F8")]},  # Back Extension: reps only, but no logs below
        ]
        for t in cases[:4]:
            self.assertEqual(build.plan([t], self.WORKOUTS, DUMBBELLS, "lbs", False, NEVER), {str(t["id"]): {}})
        learning = build.plan([cases[4]], [], DUMBBELLS, "lbs", False, NEVER)["L"]["4F5866F8"]
        self.assertEqual((learning.direction, learning.rep_range), ("learning", {"start": 10, "end": 12}))

    def test_no_weight_without_history_or_supported_equipment(self):
        self.assertEqual(build.plan([self.TEMPLATE], [], DUMBBELLS, "lbs", False, NEVER)["L"].keys(), {LEG_RAISE})
        # Gorilla Row (Kettlebell): the app suggests weights for dumbbells, barbells and machines only.
        row = {"id": "U", "key": "u", "exercises": [_ex("05487216")]}
        workouts = [_workout("U", 1, ("05487216", [_set(10, 12)] * 3))]
        self.assertEqual(build.plan([row], workouts, {}, "lbs", False, NEVER), {"U": {}})

    def test_a_log_without_working_sets_gives_nothing(self):
        workouts = [_workout("L", 1, (SIDE_BEND, [_set(35, 12, "warmup")]))]
        self.assertNotIn(SIDE_BEND, build.plan([self.TEMPLATE], workouts, DUMBBELLS, "lbs", False, NEVER)["L"])

    def test_routine_takes_the_prescription_and_falls_back_per_exercise(self):
        plan = build.plan([self.TEMPLATE], self.WORKOUTS, DUMBBELLS, "lbs", False, NEVER)["L"]
        r = build.routine_from_template(self.TEMPLATE, 7, {LUNGE: 11.34, SIDE_BEND: 1.0}, "n", planned=plan)
        by_id = {e["exercise_template_id"]: e["sets"] for e in r["exercises"]}
        self.assertAlmostEqual(by_id[SIDE_BEND][0]["weight_kg"], 40 / LB)
        self.assertEqual([round(s["weight_kg"] * LB) for s in by_id[GOBLET][:2]], [30, 50])
        self.assertEqual(by_id[LUNGE][0]["weight_kg"], 11.34)
        self.assertEqual(by_id[LEG_RAISE][0]["rep_range"], {"start": 12, "end": 15})
        self.assertIsNone(by_id[LEG_RAISE][0]["weight_kg"])

    def test_warm_ups_past_the_prescription_stay_empty(self):
        template = {"id": "L", "key": "l", "exercises": [_ex(SIDE_BEND, warmups=3)]}
        planned = {SIDE_BEND: build.Planned("none", 20.0, (5.0,), None)}
        sets = build.routine_from_template(template, 7, {}, "n", planned=planned)["exercises"][0]["sets"]
        self.assertEqual([s["weight_kg"] for s in sets[:3]], [5.0, None, None])

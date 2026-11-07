import unittest
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from hevy_trainer_sync import trainer_rules as tr

LA = ZoneInfo("America/Los_Angeles")
START = datetime(2026, 9, 14, 20, 26, 40, tzinfo=UTC)  # the program's created_at
LBS = (5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5, 25, 30, 35, 40, 45, 50)


def kg(lbs):
    return lbs / tr.LBS_PER_KG


def sets(*reps, weight=35, indicator="normal"):
    return [{"indicator": indicator, "reps": r, "weight_kg": kg(weight)} for r in reps]


class RoundingTest(unittest.TestCase):
    def test_halves_round_up_as_in_javascript(self):
        self.assertEqual(tr.js_round(2.5), 3)
        self.assertEqual(tr.js_round(-2.5), -2)
        self.assertEqual(tr.round2(1.005 + 1e-9), 1.01)
        self.assertEqual(tr.round3(0.0005), 0.001)

    def test_units(self):
        self.assertEqual(tr.in_unit(kg(50), "lbs"), 50)
        self.assertEqual(tr.in_unit(22.6796, "kg"), 22.68)
        self.assertAlmostEqual(tr.lbs_to_kg(2.20462), 1)


class WeekTest(unittest.TestCase):
    def week(self, *args, first="monday"):
        return tr.calendar_week(START, datetime(*args, tzinfo=LA), first, LA)

    def test_counts_calendar_weeks_from_the_program_start(self):
        self.assertEqual(self.week(2026, 9, 14, 13, 30), 1)
        self.assertEqual(self.week(2026, 9, 20, 23, 59), 1)
        self.assertEqual(self.week(2026, 9, 21, 0, 0), 2)
        # 6 Nov 2026: the app showed "Cycle 2 (6-Week Program)", week 2/6.
        self.assertEqual(self.week(2026, 11, 6, 18, 0), 8)
        self.assertEqual(self.week(2026, 11, 8, 23, 59), 8)
        self.assertEqual(self.week(2026, 11, 9, 0, 0), 9)

    def test_first_weekday_and_its_default(self):
        self.assertEqual(self.week(2026, 11, 8, 0, 0, first="sunday"), 9)
        self.assertEqual(self.week(2026, 11, 8, 0, 0, first="nonsense"), 8)

    def test_cycles(self):
        self.assertEqual((tr.cycle_number(8, False), tr.week_of_cycle(8, False)), (2, 2))
        self.assertEqual((tr.cycle_number(6, False), tr.week_of_cycle(6, False)), (1, 6))
        self.assertEqual((tr.cycle_number(0, False), tr.week_of_cycle(0, False)), (1, 1))
        self.assertEqual((tr.cycle_number(8, True), tr.week_of_cycle(8, True)), (2, 1))
        self.assertEqual(tr.weeks_in_cycle(True), 7)
        self.assertTrue(tr.is_deload_week(7, True))
        self.assertFalse(tr.is_deload_week(6, True))
        self.assertFalse(tr.is_deload_week(7, False))


class EquipmentTest(unittest.TestCase):
    def test_kinds_units_and_defaults(self):
        self.assertEqual(tr.equipment_for("machine", "lbs", {}).increment, 5)
        self.assertEqual(tr.equipment_for("machine", "kg", {}).increment, 2.5)
        self.assertEqual(tr.equipment_for("dumbbell", "lbs", {"dumbbellsLbs": [5, 10]}).available, (5, 10))
        self.assertEqual(tr.equipment_for("dumbbell", "kg", {}).available, tuple(tr.DEFAULT_WEIGHTS["dumbbellsKg"]))
        bar = tr.equipment_for("barbell", "lbs", {"barsLbs": [45], "platesLbs": [10, 5]})
        self.assertEqual((bar.bars, bar.plates), ((45,), (10, 5)))
        self.assertIsNone(tr.equipment_for("kettlebell", "lbs", {}))
        self.assertIsNone(tr.equipment_for(None, "lbs", {}))


class PickTest(unittest.TestCase):
    OPTIONS = [40, 50, 60, 70]

    def test_nearest_keeps_the_first_on_a_tie(self):
        self.assertEqual(tr._pick(55, self.OPTIONS, None, 50), 50)
        self.assertEqual(tr._pick(66, self.OPTIONS, "increase", None), 70)
        self.assertIsNone(tr._nearest(1, []))

    def test_increase(self):
        self.assertEqual(tr._pick(60, self.OPTIONS, "increase", 50), 60)       # exact
        self.assertEqual(tr._pick(65, self.OPTIONS, "increase", 40), 60)       # largest between
        self.assertEqual(tr._pick(52.5, self.OPTIONS, "increase", 50), 60)     # next above
        self.assertIsNone(tr._pick(73.5, self.OPTIONS, "increase", 70))        # nothing heavier

    def test_decrease(self):
        self.assertEqual(tr._pick(50, self.OPTIONS, "decrease", 60), 50)       # exact
        self.assertEqual(tr._pick(45, self.OPTIONS, "decrease", 70), 50)       # smallest between
        self.assertEqual(tr._pick(57, self.OPTIONS, "decrease", 60), 50)       # next below
        self.assertIsNone(tr._pick(38, self.OPTIONS, "decrease", 40))          # nothing lighter

    def test_none_keeps_the_current_weight(self):
        self.assertEqual(tr._pick(52, self.OPTIONS, "none", 50), 50)


class AdjustTest(unittest.TestCase):
    def test_machine_steps(self):
        m = tr.Equipment("machine", "lbs", increment=5)
        self.assertEqual(tr.adjust(kg(101), m, "increase"), 105)
        self.assertEqual(tr.adjust(kg(104), m, "decrease"), 100)
        self.assertEqual(tr.adjust(kg(102.5), m), 105)

    def test_dumbbells_round_to_pairs(self):
        d = tr.Equipment("dumbbell", "lbs", available=(25, 22.5, 30))
        self.assertEqual(tr.adjust(kg(47.25), d, "increase", 45), 50)
        self.assertEqual(tr.adjust(kg(52), d), 50)
        self.assertIsNone(tr.adjust(kg(50), tr.Equipment("dumbbell", "lbs")))

    def test_barbell_loads(self):
        b = tr.Equipment("barbell", "lbs", bars=(45,), plates=(10, 5, 0))
        self.assertEqual(tr.loadable_barbell_weights(b, 70), [45, 55, 65, 75, 85])
        self.assertEqual(tr.adjust(kg(68), b, "increase", 65), 75)
        no_bar = tr.Equipment("barbell", "kg", bars=(0,), plates=(5,))
        self.assertEqual(tr.loadable_barbell_weights(no_bar, 25), [20, 30])
        self.assertEqual(tr.adjust(22, no_bar), 20)


class WeightTest(unittest.TestCase):
    D = tr.Equipment("dumbbell", "lbs", available=LBS)
    RANGE = {"start": 10, "end": 12}

    def test_evaluate(self):
        self.assertIsNone(tr.evaluate(sets(12, indicator="warmup"), 3, self.RANGE))
        self.assertEqual(tr.evaluate(sets(12, 12), 3, self.RANGE)[0], "none")
        direction, base, target = tr.evaluate(sets(15, 12, 12), 3, self.RANGE)
        self.assertEqual(direction, "increase")
        self.assertAlmostEqual(target, base * 1.05)
        self.assertEqual(tr.evaluate(sets(9, 8, 9), 3, self.RANGE)[0], "decrease")
        self.assertEqual(tr.evaluate(sets(12, 12, 11), 3, self.RANGE)[0], "none")

    def test_the_lightest_working_set_is_the_base(self):
        log = sets(12, weight=50) + sets(12, 12, weight=30)
        self.assertAlmostEqual(tr.evaluate(log, 3, self.RANGE)[1], kg(30))

    def test_prescription(self):
        p = tr.weight_prescription([sets(9, 9, 9), sets(15, 12, 12)], 3, self.RANGE, 0, self.D, False)
        self.assertEqual((p.direction, p.weight, p.warmups), ("increase", 40, ()))
        self.assertIsNone(tr.weight_prescription([], 3, self.RANGE, 0, self.D, False))
        self.assertIsNone(tr.weight_prescription([sets(1, indicator="warmup")], 3, self.RANGE, 0, self.D, False))
        self.assertIsNone(tr.weight_prescription([sets(12, 12, 12, weight=100)], 3, self.RANGE, 0, self.D, False))

    def test_deload_is_60_percent(self):
        p = tr.weight_prescription([sets(12, 12, 12, weight=50)], 3, self.RANGE, 1, self.D, True)
        self.assertEqual((p.direction, p.weight, p.warmups), ("deload", 35, (20,)))

    def test_warm_ups(self):
        self.assertEqual(tr.warmup_weights(80, 2, self.D), [30, 50])
        self.assertEqual(tr.warmup_weights(80, 1, self.D), [50])
        self.assertEqual(tr.warmup_weights(None, 2, self.D), [])
        self.assertEqual(tr.warmup_weights(80, 0, self.D), [])
        self.assertEqual(tr.warmup_weights(40, 1, tr.Equipment("machine", "kg", increment=2.5)), [25])
        self.assertEqual(tr.warmup_weights(80, 2, tr.Equipment("dumbbell", "lbs")), [])

    def test_warm_up_count(self):
        for given, want in ((None, 0), (float("inf"), 0), (-1, 0), (0, 0), (1, 1), (1.5, 1), (2, 2), (5, 2)):
            self.assertEqual(tr.normalize_warmups(given), want, given)


class RepsTest(unittest.TestCase):
    def test_ladder(self):
        self.assertEqual(tr.next_range_up({"start": 10, "end": 12}), {"start": 12, "end": 15})
        self.assertIsNone(tr.next_range_up({"start": 25, "end": 30}))
        self.assertEqual(tr.next_range_down({"start": 15, "end": 20}), {"start": 12, "end": 15})
        self.assertIsNone(tr.next_range_down({"start": 4, "end": 6}))

    def test_each_log_moves_the_range_a_rung(self):
        base = {"start": 10, "end": 12}
        logs = [sets(12, 13, 12), sets(15, 15, 15), sets(16, 15, 15), sets(1, indicator="warmup")]
        p = tr.reps_prescription(logs, 3, base, False)
        self.assertEqual((p.direction, p.rep_range), ("none", {"start": 15, "end": 20}))
        p = tr.reps_prescription(logs[:2], 3, base, False)
        self.assertEqual((p.direction, p.rep_range), ("increase", {"start": 15, "end": 20}))

    def test_down_short_and_the_ends_of_the_ladder(self):
        self.assertEqual(tr.reps_prescription([sets(5, 5, 5)], 3, {"start": 10, "end": 12}, False).rep_range,
                         {"start": 8, "end": 12})
        self.assertEqual(tr.reps_prescription([sets(5, 5)], 3, {"start": 10, "end": 12}, False).direction, "none")
        top = {"start": 25, "end": 30}
        self.assertEqual(tr.reps_prescription([sets(30, 30, 30)], 3, top, False).rep_range, top)
        bottom = {"start": 4, "end": 6}
        self.assertEqual(tr.reps_prescription([sets(1, 1, 1)], 3, bottom, False).rep_range, bottom)

    def test_learning_and_deload(self):
        base = {"start": 10, "end": 12}
        self.assertEqual(tr.reps_prescription([], 3, base, False).direction, "learning")
        self.assertEqual(tr.reps_prescription([], 3, base, True).rep_range, {"start": 8, "end": 12})
        self.assertEqual(tr.reps_prescription([], 3, {"start": 4, "end": 6}, True).rep_range, {"start": 4, "end": 6})


if __name__ == "__main__":
    unittest.main()

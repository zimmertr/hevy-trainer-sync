import unittest

from hevy_trainer_sync import schedule


class PlanTest(unittest.TestCase):
    def test_empty_calendar_schedules_today(self):
        p = schedule.plan([], "upper", "2026-11-05")
        self.assertTrue(p.schedule)
        self.assertEqual(p.unschedule, [])

    def test_already_on_today_does_nothing(self):
        p = schedule.plan([("upper", "s1", "2026-11-05")], "upper", "2026-11-05")
        self.assertFalse(p.schedule)
        self.assertEqual(p.unschedule, [])

    def test_missed_day_moves_the_entry(self):
        p = schedule.plan([("upper", "s1", "2026-11-04")], "upper", "2026-11-05")
        self.assertTrue(p.schedule)
        self.assertEqual(p.unschedule, [("upper", "s1")])

    def test_done_session_keeps_its_entry(self):
        # Upper was done on the 4th, Trainer moved on to Lower.
        p = schedule.plan([("upper", "s1", "2026-11-04")], "lower", "2026-11-05")
        self.assertTrue(p.schedule)
        self.assertEqual(p.unschedule, [])

    def test_never_two_on_one_day(self):
        # Upper done today; next is Lower now, but it waits until tomorrow.
        p = schedule.plan([("upper", "s1", "2026-11-05")], "lower", "2026-11-05")
        self.assertFalse(p.schedule)

    def test_today_in_zone_is_a_date(self):
        self.assertRegex(schedule.today_in("America/Los_Angeles"), r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    unittest.main()

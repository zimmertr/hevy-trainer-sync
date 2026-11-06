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

    def test_a_finished_session_makes_way_for_the_next_one_at_once(self):
        # Upper done today, so Trainer moved on to Lower. hevy2garmin re-booked
        # today's Upper entry onto the rebuilt workout; it comes off, and Lower
        # goes on today.
        p = schedule.plan([("upper", "s1", "2026-11-05")], "lower", "2026-11-05")
        self.assertTrue(p.schedule)
        self.assertEqual(p.unschedule, [("upper", "s1")])

    def test_old_and_future_entries_of_any_routine_come_off(self):
        rows = [("upper", "s1", "2026-11-04"), ("lower", "s2", "2026-11-03"),
                ("lower", "s3", "2026-11-09"), ("lower", "s4", None)]
        p = schedule.plan(rows, "upper", "2026-11-05")
        self.assertTrue(p.schedule)
        self.assertEqual(p.unschedule, [("upper", "s1"), ("lower", "s2"), ("lower", "s3"), ("lower", "s4")])

    def test_only_one_entry_on_today_is_kept(self):
        p = schedule.plan([("upper", "s1", "2026-11-05"), ("upper", "s2", "2026-11-05")], "upper", "2026-11-05")
        self.assertFalse(p.schedule)
        self.assertEqual(p.unschedule, [("upper", "s2")])

    def test_today_in_zone_is_a_date(self):
        self.assertRegex(schedule.today_in("America/Los_Angeles"), r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    unittest.main()

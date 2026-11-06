import datetime
import sys
import types
import unittest
from unittest import mock

from hevy_trainer_sync import db

URL = "postgresql://ro@db/hevy2garmin"


class FakePsycopg(unittest.TestCase):
    """Stands in for psycopg, which db.py imports only when it connects."""

    def setUp(self):
        self.conn = mock.MagicMock()
        self.conn.__enter__.return_value = self.conn
        self.conn.__exit__.return_value = False  # a truthy MagicMock would swallow exceptions
        self.cursor = self.conn.execute.return_value
        self.psycopg = types.ModuleType("psycopg")
        self.psycopg.connect = mock.MagicMock(return_value=self.conn)
        self.psycopg.Error = type("Error", (Exception,), {})
        patcher = mock.patch.dict(sys.modules, {"psycopg": self.psycopg})
        patcher.start()
        self.addCleanup(patcher.stop)

    def assert_connected_once(self):
        self.psycopg.connect.assert_called_once_with(URL, connect_timeout=10)
        self.conn.__exit__.assert_called_once()


class SchedulesTest(FakePsycopg):
    def test_no_routines_never_connects(self):
        self.assertEqual(db.schedules(URL, []), [])
        self.psycopg.connect.assert_not_called()

    def test_rows_become_strings_and_dates(self):
        self.cursor.fetchall.return_value = [
            (123, 456, datetime.date(2026, 11, 5)),
            ("r2", "s2", "2026-11-04T00:00:00"),
            ("r3", "s3", None),
        ]
        self.assertEqual(db.schedules(URL, ["123", "r2", "r3"]), [
            ("123", "456", "2026-11-05"),
            ("r2", "s2", "2026-11-04"),
            ("r3", "s3", None),
        ])
        self.assert_connected_once()
        sql, params = self.conn.execute.call_args.args
        self.assertIn("FROM routine_schedules", sql)
        self.assertEqual(params, (["123", "r2", "r3"],))


class GarminWorkoutsTest(FakePsycopg):
    def test_no_routines_never_connects(self):
        self.assertEqual(db.garmin_workouts(URL, []), {})
        self.psycopg.connect.assert_not_called()

    def test_rows_map_routine_to_workout_and_title(self):
        self.cursor.fetchall.return_value = [("r1", 111, "Upper W8"), ("r2", 222, None)]
        self.assertEqual(db.garmin_workouts(URL, ["r1", "r2", "r3"]),
                         {"r1": ("111", "Upper W8"), "r2": ("222", "")})
        self.assert_connected_once()
        sql, params = self.conn.execute.call_args.args
        self.assertIn("FROM synced_routines", sql)
        self.assertIn("status = 'success'", sql)
        self.assertEqual(params, (["r1", "r2", "r3"],))


class GarminDiTokenTest(FakePsycopg):
    def test_returns_the_stored_token(self):
        self.cursor.fetchall.return_value = [("di-token",)]
        self.assertEqual(db.garmin_di_token(URL), "di-token")
        self.assert_connected_once()
        self.assertIn("FROM platform_credentials", self.conn.execute.call_args.args[0])

    def test_no_row_or_empty_token_is_an_error(self):
        for rows in ([], [(None,)], [("",)]):
            self.cursor.fetchall.return_value = rows
            with self.assertRaisesRegex(db.DbError, "no Garmin session stored"):
                db.garmin_di_token(URL)


class SyncedIdsTest(FakePsycopg):
    def test_no_workouts_never_connects(self):
        self.assertEqual(db.synced_ids(URL, []), set())
        self.psycopg.connect.assert_not_called()

    def test_returns_the_ids_hevy2garmin_has(self):
        self.cursor.fetchall.return_value = [("w1",)]
        self.assertEqual(db.synced_ids(URL, ["w1", "w2"]), {"w1"})
        self.assert_connected_once()
        sql, params = self.conn.execute.call_args.args
        self.assertIn("FROM synced_workouts", sql)
        self.assertEqual(params, (["w1", "w2"],))


class MergeSettingsTest(FakePsycopg):
    def test_returns_the_stored_object(self):
        self.cursor.fetchall.return_value = [({"merge_mode": True},)]
        self.assertEqual(db.merge_settings(URL), {"merge_mode": True})
        sql, params = self.conn.execute.call_args.args
        self.assertIn("FROM app_cache", sql)
        self.assertEqual(params, ("merge_settings",))

    def test_missing_or_not_an_object_is_none(self):
        for rows in ([], [("text",)], [(None,)]):
            self.cursor.fetchall.return_value = rows
            self.assertIsNone(db.merge_settings(URL))


class DbErrorTest(FakePsycopg):
    def test_a_database_failure_becomes_db_error(self):
        self.psycopg.connect.side_effect = self.psycopg.Error("connection refused")
        with self.assertRaisesRegex(db.DbError, "hevy2garmin's database: connection refused"):
            db.synced_ids(URL, ["w1"])

    def test_a_failed_query_becomes_db_error(self):
        self.conn.execute.side_effect = self.psycopg.Error("relation does not exist")
        with self.assertRaises(db.DbError):
            db.merge_settings(URL)


if __name__ == "__main__":
    unittest.main()

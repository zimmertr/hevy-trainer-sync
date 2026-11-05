import os
import runpy
import unittest
from unittest import mock

from hevy_trainer_sync import build, cli
from hevy_trainer_sync.http import HttpError

TOKENS = {"access_token": "A", "refresh_token": "R", "expires_at": None}
TODAY = "2026-11-05"
DB = "postgresql://ro@db/hevy2garmin"
BASE_ENV = {"HEVY_STATE_FILE": "/state/s.json", "HEVY_API_KEY": "key", "H2G_PASSWORD": "pw"}


def template(key, index, tid):
    return {"key": key, "index": index, "exercises": [
        {"exercise_template_id": tid, "index": 0, "set_count": 2, "warmup_set_count": 1,
         "rep_range": {"start": 6, "end": 8}, "rest_seconds": 120}]}


def program(**over):
    # Out of index order on purpose: Upper (index 0) is first and next.
    p = {"id": "prog", "templates": [template("lower_2x_a", 1, "L1"), template("upper_2x_a", 0, "U1")],
         "next_workout_index": 0, "created_at": None, "program_variety": "varied", "exercises_rotated_at": None}
    p.update(over)
    return p


def routine(key, tid, rid, folder_id=7, title=None):
    """What GET /v1/routines would hand back for a routine this job wrote."""
    r = build.routine_from_template(template(key, 0, tid), folder_id, {}, cli.NOTES, title_override=title)
    r["id"] = rid
    return r


class EnvTest(unittest.TestCase):
    def test_set_value_wins_over_default(self):
        with mock.patch.dict(os.environ, {"X_VAR": "v"}):
            self.assertEqual(cli.env("X_VAR", "d"), "v")

    def test_default_when_unset(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(cli.env("X_VAR", "d"), "d")

    def test_unset_or_empty_exits_2(self):
        for environ in ({}, {"X_VAR": ""}):
            with mock.patch.dict(os.environ, environ, clear=True), self.assertLogs("hevy-trainer-sync") as logs:
                with self.assertRaises(SystemExit) as cm:
                    cli.env("X_VAR")
            self.assertEqual(cm.exception.code, 2)
            self.assertEqual(logs.output, ["ERROR:hevy-trainer-sync:X_VAR is not set"])


class MainTest(unittest.TestCase):
    def setUp(self):
        self.load = self._patch(cli.state, "load_or_bootstrap", return_value=(TOKENS, False))
        self.save = self._patch(cli.state, "save")
        self.Session = self._patch(cli, "Session")
        self.Session.return_value.get_program.return_value = program()
        self.Client = self._patch(cli, "Client")
        self.hevy = self.Client.return_value
        self.hevy.recent_workouts.return_value = []
        self.hevy.folders.return_value = [{"id": 7, "title": "Hevy Trainer"}]
        self.hevy.routines.return_value = []
        self.hevy.create_routine.side_effect = lambda payload: {"id": "new-" + payload["title"]}
        self.hevy.update_routine.side_effect = lambda rid, payload: {"id": rid}
        self.Dashboard = self._patch(cli, "Dashboard")
        self.dash = self.Dashboard.return_value
        self.dash.sync_routines.return_value = {"ok": True, "synced": 2, "skipped": 0, "failed": 0, "results": []}
        self.send = self._patch(cli, "send_to_device", return_value=0)
        self.schedules = self._patch(cli.db, "schedules", return_value=[])
        self.today_in = self._patch(cli.schedule, "today_in", return_value=TODAY)
        self._patch(cli.logging, "basicConfig")

    def _patch(self, target, attr, **kw):
        p = mock.patch.object(target, attr, **kw)
        m = p.start()
        self.addCleanup(p.stop)
        return m

    def run_main(self, *argv, **env):
        """main(argv) with BASE_ENV plus `env` (None unsets); returns (exit code, log text)."""
        environ = {k: v for k, v in {**BASE_ENV, **env}.items() if v is not None}
        with mock.patch.dict(os.environ, environ, clear=True), self.assertLogs("hevy-trainer-sync", "INFO") as logs:
            rc = cli.main(list(argv))
        return rc, "\n".join(logs.output)

    def existing_upper_and_lower(self):
        self.hevy.routines.return_value = [
            routine("upper_2x_a", "U1", "u"),
            routine("lower_2x_a", "L1", "l"),
            routine("upper_2x_a", "U1", "elsewhere", folder_id=99),
        ]

    # Session state

    def test_unreadable_state_returns_2(self):
        self.load.side_effect = ValueError("no state at /state/s.json and HEVY_SESSION is not set")
        rc, logs = self.run_main()
        self.assertEqual(rc, 2)
        self.assertIn("ERROR:hevy-trainer-sync:no state at /state/s.json", logs)
        self.Session.assert_not_called()

    def test_bootstrap_is_logged_and_refreshes_persist_to_the_state_file(self):
        self.load.return_value = (TOKENS, True)
        rc, logs = self.run_main("--dry-run", HEVY_STATE_FILE=None, HEVY_SESSION="cookie")
        self.assertEqual(rc, 0)
        self.load.assert_called_once_with("/state/hevy-session.json", "cookie")
        self.assertIn("no state at /state/hevy-session.json, bootstrapped from HEVY_SESSION", logs)
        tokens, persist = self.Session.call_args.args
        self.assertIs(tokens, TOKENS)
        persist({"access_token": "A2"})
        self.save.assert_called_once_with("/state/hevy-session.json", {"access_token": "A2"})

    def test_existing_state_is_not_reported_as_bootstrapped(self):
        _, logs = self.run_main("--dry-run")
        self.load.assert_called_once_with("/state/s.json", None)
        self.assertNotIn("bootstrapped", logs)

    # The program

    def test_program_with_no_templates_returns_1(self):
        self.Session.return_value.get_program.return_value = {"id": "prog"}
        rc, logs = self.run_main()
        self.assertEqual(rc, 1)
        self.assertIn("program prog: 0 templates, next is ?", logs)
        self.assertIn("the program has no templates", logs)
        self.Client.assert_not_called()

    def test_next_template_is_logged_by_title(self):
        _, logs = self.run_main("--dry-run")
        self.assertIn("program prog: 2 templates, next is Upper, variety=varied, rotated None", logs)

    def test_out_of_range_or_non_int_next_index_means_unknown(self):
        for nxt in (2, -1, "0", None):
            self.Session.return_value.get_program.return_value = program(next_workout_index=nxt)
            _, logs = self.run_main("--dry-run")
            self.assertIn("next is ?", logs)

    def test_missing_api_key_exits_2(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_main(HEVY_API_KEY=None)
        self.assertEqual(cm.exception.code, 2)

    # Weights

    def test_weights_from_recent_workouts_fill_the_working_sets(self):
        self.hevy.recent_workouts.return_value = [
            {"exercises": [{"exercise_template_id": "U1", "sets": [{"type": "normal", "weight_kg": 50}]}]}]
        rc, logs = self.run_main(WORKOUT_PAGES="2")
        self.assertEqual(rc, 0)
        self.Client.assert_called_once_with("key")
        self.hevy.recent_workouts.assert_called_once_with(2)
        self.assertIn("weights known for 1 of 2 exercises", logs)
        upper = self.hevy.create_routine.call_args_list[0].args[0]
        self.assertEqual([s["weight_kg"] for s in upper["exercises"][0]["sets"]], [None, 50.0, 50.0])

    def test_four_pages_of_workouts_by_default(self):
        self.run_main("--dry-run")
        self.hevy.recent_workouts.assert_called_once_with(4)

    # The folder

    def test_missing_folder_is_created(self):
        self.hevy.folders.return_value = [{"id": 1, "title": "Something else"}]
        self.hevy.create_folder.return_value = {"id": 9, "title": "Hevy Trainer"}
        rc, logs = self.run_main()
        self.assertEqual(rc, 0)
        self.hevy.create_folder.assert_called_once_with("Hevy Trainer")
        self.assertIn("creating routine folder 'Hevy Trainer'", logs)
        self.assertEqual([c.args[0]["folder_id"] for c in self.hevy.create_routine.call_args_list], [9, 9])

    def test_folder_title_comes_from_the_environment(self):
        self.hevy.folders.return_value = [{"id": 7, "title": "Hevy Trainer"}, {"id": 8, "title": "Trainer"}]
        self.run_main(FOLDER_TITLE="Trainer")
        self.hevy.create_folder.assert_not_called()
        self.assertEqual(self.hevy.create_routine.call_args.args[0]["folder_id"], 8)

    def test_dry_run_with_no_folder_writes_nothing(self):
        self.hevy.folders.return_value = []
        rc, logs = self.run_main("--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("creating routine folder 'Hevy Trainer'", logs)
        self.hevy.create_folder.assert_not_called()
        # No folder id, so no routine can be in it.
        self.hevy.routines.assert_not_called()
        self.assertIn("Upper: create (1 exercises) [dry run]", logs)
        self.assertIn("Lower: create (1 exercises) [dry run]", logs)
        self.assertIn("dry run: not touching hevy2garmin", logs)
        self.hevy.create_routine.assert_not_called()
        self.hevy.update_routine.assert_not_called()
        self.Dashboard.assert_not_called()

    # Routines

    def test_routines_are_created_in_program_order_and_pushed(self):
        rc, logs = self.run_main()
        self.assertEqual(rc, 0)
        payloads = [c.args[0] for c in self.hevy.create_routine.call_args_list]
        self.assertEqual([p["title"] for p in payloads], ["Upper", "Lower"])
        self.assertEqual(payloads[0]["notes"], cli.NOTES)
        self.assertEqual(payloads[0]["folder_id"], 7)
        self.assertIn("Upper: create (1 exercises)", logs)
        self.assertNotIn("[dry run]", logs)
        self.Dashboard.assert_called_once_with("http://hevy2garmin", "pw")
        self.dash.sync_routines.assert_called_once_with(["new-Upper", "new-Lower"])
        self.assertIn("hevy2garmin: synced=2 skipped=0 failed=0", logs)
        self.send.assert_not_called()

    def test_week_goes_in_the_title(self):
        with mock.patch.object(cli.build, "program_week", return_value=8) as week:
            self.Session.return_value.get_program.return_value = program(created_at="2026-09-14T20:26:40Z")
            _, logs = self.run_main()
        week.assert_called_once_with("2026-09-14T20:26:40Z")
        self.assertIn("program week 8 (started 2026-09-14T20:26:40Z)", logs)
        self.assertEqual(
            [c.args[0]["title"] for c in self.hevy.create_routine.call_args_list], ["Upper W8", "Lower W8"]
        )

    def test_unchanged_routines_are_left_alone(self):
        self.existing_upper_and_lower()
        rc, logs = self.run_main()
        self.assertEqual(rc, 0)
        self.assertIn("Upper: unchanged", logs)
        self.assertIn("Lower: unchanged", logs)
        self.hevy.create_routine.assert_not_called()
        self.hevy.update_routine.assert_not_called()
        self.dash.sync_routines.assert_not_called()
        self.assertIn("nothing to push to Garmin", logs)

    def test_changed_routine_is_updated_in_place(self):
        self.existing_upper_and_lower()
        self.hevy.routines.return_value[0]["exercises"][0]["rest_seconds"] = 60
        rc, logs = self.run_main()
        self.assertEqual(rc, 0)
        self.assertIn("Upper: update (1 exercises)", logs)
        self.hevy.update_routine.assert_called_once()
        rid, payload = self.hevy.update_routine.call_args.args
        self.assertEqual(rid, "u")
        self.assertEqual(payload["exercises"][0]["rest_seconds"], 120)
        self.dash.sync_routines.assert_called_once_with(["u"])

    def test_last_weeks_routine_is_renamed_not_duplicated(self):
        self.hevy.routines.return_value = [routine("upper_2x_a", "U1", "u", title="Upper W7"),
                                           routine("lower_2x_a", "L1", "l")]
        with mock.patch.object(cli.build, "program_week", return_value=8):
            rc, logs = self.run_main()
        self.assertEqual(rc, 0)
        self.assertIn("Upper W8: update (Upper W7 -> Upper W8) (1 exercises)", logs)
        self.assertIn("Lower W8: update (Lower -> Lower W8) (1 exercises)", logs)
        self.hevy.create_routine.assert_not_called()
        self.assertEqual([c.args[0] for c in self.hevy.update_routine.call_args_list], ["u", "l"])

    def test_dry_run_update_writes_nothing(self):
        self.existing_upper_and_lower()
        self.hevy.routines.return_value[1]["exercises"][0]["rest_seconds"] = 60
        rc, logs = self.run_main("--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("Lower: update (1 exercises) [dry run]", logs)
        self.hevy.update_routine.assert_not_called()
        self.Dashboard.assert_not_called()

    # hevy2garmin

    def test_force_pushes_every_managed_routine(self):
        self.existing_upper_and_lower()
        rc, _ = self.run_main("--force")
        self.assertEqual(rc, 0)
        self.dash.sync_routines.assert_called_once_with(["u", "l"])

    def test_dashboard_url_comes_from_the_environment(self):
        self.run_main(H2G_URL="http://h2g:8080")
        self.Dashboard.assert_called_once_with("http://h2g:8080", "pw")

    def test_missing_dashboard_password_exits_2(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_main(H2G_PASSWORD=None)
        self.assertEqual(cm.exception.code, 2)

    def test_failed_sync_returns_1_and_logs_each_result(self):
        self.dash.sync_routines.return_value = {"ok": False, "synced": 1, "skipped": 0, "failed": 1, "results": [
            {"title": "Upper", "status": "synced"}, {"title": "Lower", "status": "failed", "error": "boom"}]}
        rc, logs = self.run_main(DATABASE_URL=DB, SCHEDULE_NEXT="1")
        self.assertEqual(rc, 1)
        self.assertIn("INFO:hevy-trainer-sync:  Upper: synced \n", logs + "\n")
        self.assertIn("  Lower: failed boom", logs)
        self.send.assert_not_called()
        self.schedules.assert_not_called()

    # Send to Device

    def test_pushed_routines_are_sent_to_the_watch(self):
        rc, _ = self.run_main(DATABASE_URL=DB)
        self.assertEqual(rc, 0)
        self.send.assert_called_once_with(DB, self.dash, ["new-Upper", "new-Lower"])
        self.schedules.assert_not_called()

    def test_failed_send_returns_1(self):
        self.send.return_value = 1
        rc, _ = self.run_main(DATABASE_URL=DB, SCHEDULE_NEXT="1")
        self.assertEqual(rc, 1)
        self.schedules.assert_not_called()

    def test_send_to_device_can_be_turned_off(self):
        rc, _ = self.run_main(DATABASE_URL=DB, SEND_TO_DEVICE="0")
        self.assertEqual(rc, 0)
        self.send.assert_not_called()

    def test_nothing_pushed_means_nothing_sent(self):
        self.existing_upper_and_lower()
        self.run_main(DATABASE_URL=DB)
        self.send.assert_not_called()

    # The calendar

    def test_calendar_is_opt_in(self):
        self.run_main(DATABASE_URL=DB)
        self.schedules.assert_not_called()
        self.run_main(SCHEDULE_NEXT="1")
        self.schedules.assert_not_called()

    def test_unknown_next_workout_schedules_nothing(self):
        self.Session.return_value.get_program.return_value = program(next_workout_index=None)
        rc, _ = self.run_main(DATABASE_URL=DB, SCHEDULE_NEXT="1")
        self.assertEqual(rc, 0)
        self.schedules.assert_not_called()

    def test_next_workout_without_a_routine_id_schedules_nothing(self):
        # Hevy answering a create with an empty id is the only way here.
        self.hevy.create_routine.side_effect = lambda payload: {"id": ""}
        rc, logs = self.run_main(DATABASE_URL=DB, SCHEDULE_NEXT="1")
        self.assertEqual(rc, 0)
        self.assertIn("WARNING:hevy-trainer-sync:next workout 'Upper' has no routine yet; nothing scheduled", logs)
        self.schedules.assert_not_called()

    def test_next_workout_goes_on_today_and_a_missed_one_comes_off(self):
        self.existing_upper_and_lower()
        self.schedules.return_value = [("u", "s1", "2026-11-04"), ("l", "s0", "2026-11-03")]
        self.dash.unschedule.return_value = {"ok": True}
        self.dash.schedule.return_value = {"ok": True}
        rc, logs = self.run_main(DATABASE_URL=DB, SCHEDULE_NEXT="1", TZ="America/Los_Angeles")
        self.assertEqual(rc, 0)
        self.today_in.assert_called_once_with("America/Los_Angeles")
        self.schedules.assert_called_once_with(DB, ["u", "l"])
        self.dash.unschedule.assert_called_once_with("u", "s1")
        self.assertIn("unscheduled stale entry s1: ok", logs)
        self.dash.schedule.assert_called_once_with("u", TODAY)
        self.assertIn(f"scheduled Upper on {TODAY}: ok", logs)

    def test_today_is_utc_by_default(self):
        self.existing_upper_and_lower()
        self.dash.schedule.return_value = {"ok": True}
        self.run_main(DATABASE_URL=DB, SCHEDULE_NEXT="1")
        self.today_in.assert_called_once_with("UTC")

    def test_failed_unschedule_is_logged_and_scheduling_continues(self):
        self.existing_upper_and_lower()
        self.schedules.return_value = [("u", "s1", "2026-11-04")]
        self.dash.unschedule.return_value = {"ok": False, "error": "gone"}
        self.dash.schedule.return_value = {"ok": True}
        rc, logs = self.run_main(DATABASE_URL=DB, SCHEDULE_NEXT="1")
        self.assertEqual(rc, 0)
        self.assertIn("unscheduled stale entry s1: gone", logs)
        self.dash.schedule.assert_called_once_with("u", TODAY)

    def test_failed_schedule_returns_1(self):
        self.existing_upper_and_lower()
        self.dash.schedule.return_value = {"ok": False, "error": "no workout"}
        rc, logs = self.run_main(DATABASE_URL=DB, SCHEDULE_NEXT="1")
        self.assertEqual(rc, 1)
        self.assertIn(f"scheduled Upper on {TODAY}: no workout", logs)

    def test_a_workout_already_on_today_is_left_alone(self):
        self.existing_upper_and_lower()
        self.schedules.return_value = [("l", "s2", TODAY)]
        rc, logs = self.run_main(DATABASE_URL=DB, SCHEDULE_NEXT="1")
        self.assertEqual(rc, 0)
        self.assertIn(f"calendar already has a workout on {TODAY}", logs)
        self.dash.schedule.assert_not_called()
        self.dash.unschedule.assert_not_called()


class SendToDeviceTest(unittest.TestCase):
    def setUp(self):
        self.workouts = self._patch(cli.db, "garmin_workouts",
                                    return_value={"r1": ("111", "Upper W8"), "r2": ("222", "Lower W8")})
        self.token = self._patch(cli.db, "garmin_di_token", side_effect=["tok1", "tok2"])
        self.Garmin = self._patch(cli, "Garmin")
        self.garmin = self.Garmin.return_value
        self.garmin.last_used_device_id.return_value = 42
        self.dash = mock.MagicMock()

    def _patch(self, target, attr, **kw):
        p = mock.patch.object(target, attr, **kw)
        m = p.start()
        self.addCleanup(p.stop)
        return m

    def send(self, routine_ids, **env):
        with mock.patch.dict(os.environ, env, clear=True), self.assertLogs("hevy-trainer-sync", "INFO") as logs:
            rc = cli.send_to_device(DB, self.dash, routine_ids)
        return rc, "\n".join(logs.output)

    def test_nothing_recorded_sends_nothing(self):
        self.workouts.return_value = {}
        rc, logs = self.send(["r1"])
        self.assertEqual(rc, 0)
        self.assertIn("WARNING:hevy-trainer-sync:no Garmin workouts recorded", logs)
        self.workouts.assert_called_once_with(DB, ["r1"])
        self.Garmin.assert_not_called()

    def test_sends_each_recorded_workout_to_the_last_used_device(self):
        rc, logs = self.send(["r1", "r3", "r2"])
        self.assertEqual(rc, 0)
        self.Garmin.assert_called_once_with("tok1")
        self.garmin.last_used_device_id.assert_called_once_with()
        # r3 has no Garmin workout and is skipped.
        self.assertEqual(self.garmin.send_workout.call_args_list,
                         [mock.call("111", "Upper W8", 42), mock.call("222", "Lower W8", 42)])
        self.assertIn("sent Upper W8 (Garmin workout 111) to device 42", logs)

    def test_configured_device_skips_the_lookup(self):
        rc, _ = self.send(["r1"], GARMIN_DEVICE_ID="3456789012")
        self.assertEqual(rc, 0)
        self.garmin.last_used_device_id.assert_not_called()
        self.garmin.send_workout.assert_called_once_with("111", "Upper W8", 3456789012)

    def test_expired_token_is_refreshed_through_hevy2garmin_and_retried(self):
        stale, fresh = mock.MagicMock(), mock.MagicMock()
        stale.last_used_device_id.side_effect = HttpError(401, "expired", "https://connectapi")
        fresh.last_used_device_id.return_value = 42
        self.Garmin.side_effect = [stale, fresh]
        rc, logs = self.send(["r1"])
        self.assertEqual(rc, 0)
        self.dash.sync_routines.assert_called_once_with([])
        self.assertEqual(self.Garmin.call_args_list, [mock.call("tok1"), mock.call("tok2")])
        stale.send_workout.assert_not_called()
        fresh.send_workout.assert_called_once_with("111", "Upper W8", 42)
        self.assertIn("asking hevy2garmin to refresh it", logs)

    def test_other_garmin_errors_propagate(self):
        self.garmin.last_used_device_id.side_effect = HttpError(500, "down", "https://connectapi")
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(HttpError):
            cli.send_to_device(DB, self.dash, ["r1"])
        self.dash.sync_routines.assert_not_called()
        self.garmin.send_workout.assert_not_called()

    def test_one_failed_send_returns_1_but_the_rest_still_go(self):
        self.garmin.send_workout.side_effect = [HttpError(500, "nope", "https://connectapi"), None]
        rc, logs = self.send(["r1", "r2"])
        self.assertEqual(rc, 1)
        self.assertEqual(self.garmin.send_workout.call_count, 2)
        self.assertIn("ERROR:hevy-trainer-sync:send to device failed for Upper W8: HTTP 500", logs)
        self.assertIn("sent Lower W8 (Garmin workout 222) to device 42", logs)


class EntryPointTest(unittest.TestCase):
    def test_python_dash_m_exits_with_mains_code(self):
        with mock.patch.object(cli, "main", return_value=3) as main:
            with self.assertRaises(SystemExit) as cm:
                runpy.run_module("hevy_trainer_sync", run_name="__main__")
        self.assertEqual(cm.exception.code, 3)
        main.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()


class PollDispatchTest(unittest.TestCase):
    def test_poll_runs_the_watcher_with_the_remaining_args(self):
        from hevy_trainer_sync import poll
        with mock.patch.object(poll, "main", return_value=0) as watcher:
            self.assertEqual(cli.main(["poll", "--x"]), 0)
        watcher.assert_called_once_with(["--x"])

    def test_no_argv_reads_sys_argv(self):
        from hevy_trainer_sync import poll
        with mock.patch.object(cli.sys, "argv", ["hevy-trainer-sync", "poll"]), \
                mock.patch.object(poll, "main", return_value=3) as watcher:
            self.assertEqual(cli.main(), 3)
        watcher.assert_called_once_with([])

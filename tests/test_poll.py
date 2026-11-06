import os
import unittest
import urllib.error
from datetime import UTC, datetime, timedelta, timezone
from unittest import mock

from hevy_trainer_sync import db, poll
from hevy_trainer_sync.http import HttpError

T0 = datetime(2026, 11, 6, 18, 0, tzinfo=UTC)


def event(kind="updated", wid="w1", title="Upper W8", updated="2026-11-06T19:01:00Z",
          start="2026-11-06T18:00:00Z", end="2026-11-06T19:00:00Z"):
    return {"type": kind, "workout": {"id": wid, "title": title, "updated_at": updated,
                                      "start_time": start, "end_time": end}}


def activity(aid=99, start="2026-11-06 18:01:00", minutes=60):
    return {"activityId": aid, "startTimeGMT": start, "duration": minutes * 60,
            "activityType": {"typeKey": "strength_training"}}


def workout(wid="w1", start=T0, minutes=60, asked=None):
    return poll.Workout(wid, f"title {wid}", start + timedelta(minutes=minutes + 1), start,
                        start + timedelta(minutes=minutes), asked)


class TimeTest(unittest.TestCase):
    def test_iso_is_utc_with_z(self):
        local = T0.astimezone(timezone(timedelta(hours=-8)))
        self.assertEqual(poll.iso(local), "2026-11-06T18:00:00Z")

    def test_parse_accepts_z_and_offsets(self):
        self.assertEqual(poll.parse("2026-11-06T18:00:00Z"), T0)
        self.assertEqual(poll.parse("2026-11-06T18:00:00.000+00:00"), T0)


class NewWorkoutsTest(unittest.TestCase):
    def test_only_updates_after_since_oldest_edit_first(self):
        events = [
            event(wid="late", updated="2026-11-06T18:05:00Z"),
            event(wid="early", updated="2026-11-06T18:01:00Z"),
            event(wid="old", updated="2026-11-06T17:59:00Z"),
            event(wid="same", updated="2026-11-06T18:00:00Z"),
        ]
        got = poll.new_workouts(events, T0)
        self.assertEqual([w.id for w in got], ["early", "late"])
        self.assertEqual(got[0], poll.Workout("early", "Upper W8", T0 + timedelta(minutes=1), T0,
                                              T0 + timedelta(hours=1)))

    def test_deletions_and_malformed_events_are_skipped(self):
        no_end = event()
        del no_end["workout"]["end_time"]
        events = [
            event(kind="deleted"),
            {"type": "updated"},
            {"type": "updated", "workout": {"updated_at": "2026-11-06T18:01:00Z"}},
            event(updated="not a time"),
            event(start=None),
            no_end,
        ]
        self.assertEqual(poll.new_workouts(events, T0), [])

    def test_missing_title_is_empty(self):
        e = event()
        del e["workout"]["title"]
        self.assertEqual(poll.new_workouts([e], T0)[0].title, "")


class PollerCase(unittest.TestCase):
    def setUp(self):
        self.hevy = mock.Mock()
        self.hevy.workout_events.return_value = []
        self.poller = poll.Poller(self.hevy, "http://h2g", "secret", "postgres://db", "pw", T0)
        self.db = self.patch(poll, "db")
        self.db.synced_ids.return_value = set()
        self.db.merge_settings.return_value = None
        self.db.garmin_di_token.return_value = "tok"
        self.garmin = self.patch(poll, "Garmin")
        self.garmin.return_value.activities.return_value = [activity()]
        self.trigger = self.patch(poll, "trigger_merge", return_value={"ok": True, "status": "accepted"})
        self.dashboard = self.patch(poll, "Dashboard")

    def patch(self, target, name, **kw):
        p = mock.patch.object(target, name, **kw)
        self.addCleanup(p.stop)
        return p.start()

    def wait_on(self, *workouts):
        for w in workouts:
            self.poller.waiting[w.id] = w


class ReadHevyTest(PollerCase):
    def test_reads_events_since_the_mark(self):
        self.poller.read_hevy()
        self.hevy.workout_events.assert_called_once_with("2026-11-06T18:00:00Z")
        self.assertEqual(self.poller.since, T0)

    def test_new_workouts_wait_and_move_the_mark(self):
        self.hevy.workout_events.return_value = [
            event(wid="a", updated="2026-11-06T19:01:00Z"),
            event(wid="b", title="Lower W8", updated="2026-11-06T19:02:00Z"),
        ]
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            self.poller.read_hevy()
        self.assertEqual(set(self.poller.waiting), {"a", "b"})
        self.assertEqual(self.poller.since, T0 + timedelta(hours=1, minutes=2))
        self.assertIn("workout 'Lower W8' (b) saved; waiting for the watch's activity", "\n".join(logs.output))
        self.trigger.assert_not_called()

    def test_an_edit_keeps_when_hevy2garmin_was_last_asked(self):
        asked = T0 + timedelta(hours=2)
        self.wait_on(workout("w1", asked=asked))
        self.hevy.workout_events.return_value = [event(wid="w1", title="Upper W8 edited")]
        with self.assertNoLogs("hevy-trainer-sync.poll", "INFO"):
            self.poller.read_hevy()
        self.assertEqual(self.poller.waiting["w1"].title, "Upper W8 edited")
        self.assertEqual(self.poller.waiting["w1"].asked, asked)

    def test_hevy_failures_keep_the_mark(self):
        for failure in (HttpError(503, "down", "u"),
                        # What killed the pod on 2026-11-05: the lookup of api.hevyapp.com failed.
                        urllib.error.URLError(OSError(-2, "Name or service not known")),
                        TimeoutError("timed out")):
            self.hevy.workout_events.side_effect = failure
            with self.subTest(failure=failure), self.assertLogs("hevy-trainer-sync.poll", "WARNING") as logs:
                self.poller.read_hevy()
            self.assertIn("reading Hevy workout events failed", logs.output[0])
            self.assertEqual(self.poller.since, T0)


class StartMirrorTest(PollerCase):
    def setUp(self):
        super().setUp()
        self.kube = self.patch(poll, "kube")
        self.kube.run_cronjob.return_value = "hevy-trainer-sync-save-abc"
        self.poller.started = T0 + timedelta(hours=1)
        self.poller.run_cronjob = "hevy-trainer-sync"

    def test_a_save_after_start_runs_the_mirror_once_per_poll(self):
        self.hevy.workout_events.return_value = [event(wid="a"), event(wid="b", updated="2026-11-06T19:02:00Z")]
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            self.poller.read_hevy()
        self.kube.run_cronjob.assert_called_once_with("hevy-trainer-sync")
        self.assertIn("started hevy-trainer-sync-save-abc to update the routines and the calendar",
                      "\n".join(logs.output))

    def test_saves_read_back_on_start_do_not(self):
        self.hevy.workout_events.return_value = [event(updated="2026-11-06T18:59:00Z")]
        with self.assertLogs("hevy-trainer-sync.poll", "INFO"):
            self.poller.read_hevy()
        self.kube.run_cronjob.assert_not_called()

    def test_off_without_a_cronjob(self):
        self.poller.run_cronjob = None
        self.hevy.workout_events.return_value = [event()]
        with self.assertLogs("hevy-trainer-sync.poll", "INFO"):
            self.poller.read_hevy()
        self.kube.run_cronjob.assert_not_called()

    def test_a_failure_waits_for_the_hourly_run(self):
        self.kube.run_cronjob.side_effect = HttpError(403, "forbidden", "u")
        self.hevy.workout_events.return_value = [event()]
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            self.poller.read_hevy()
        self.assertIn("starting hevy-trainer-sync failed, the hourly run will catch up", "\n".join(logs.output))
        self.assertIn("w1", self.poller.waiting)


class TickTest(PollerCase):
    def test_nothing_waiting_touches_nothing_else(self):
        self.poller.tick(T0)
        self.db.synced_ids.assert_not_called()

    def test_a_failure_while_settling_waits_for_the_next_poll(self):
        self.wait_on(workout())
        for failure in (db.DbError("database restarting"), ConnectionRefusedError(111, "refused"),
                        HttpError(502, "bad", "u")):
            self.db.synced_ids.side_effect = failure
            with self.subTest(failure=failure), self.assertLogs("hevy-trainer-sync.poll", "WARNING") as logs:
                self.poller.tick(T0 + timedelta(hours=2))
            self.assertIn("checking the waiting workouts failed", logs.output[0])
            self.assertIn("w1", self.poller.waiting)

    def test_a_bug_is_not_swallowed(self):
        # Only call failures keep the loop going; anything else still crashes loudly.
        self.hevy.workout_events.side_effect = KeyError("events")
        with self.assertRaises(KeyError):
            self.poller.tick(T0)

    def test_a_saved_workout_is_merged_on_the_same_poll(self):
        self.hevy.workout_events.return_value = [event()]
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            self.poller.tick(T0 + timedelta(hours=1, minutes=5))
        self.trigger.assert_called_once_with("http://h2g", "secret")
        self.assertIn("watch activity 99 found for 'Upper W8' (w1); hevy2garmin accepted", "\n".join(logs.output))


class SettleTest(PollerCase):
    NOW = T0 + timedelta(hours=1, minutes=5)

    def test_finished_workouts_stop_waiting(self):
        self.wait_on(workout("w1"))
        self.db.synced_ids.return_value = {"w1"}
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            self.poller.settle(self.NOW)
        self.assertEqual(self.poller.waiting, {})
        self.assertIn("'title w1' (w1) is on Garmin; done", logs.output[0])
        self.db.synced_ids.assert_called_once_with("postgres://db", ["w1"])
        self.garmin.assert_not_called()

    def test_a_workout_the_watch_never_recorded_is_given_up_without_an_upload(self):
        self.wait_on(workout("w1"))
        with self.assertLogs("hevy-trainer-sync.poll", "WARNING") as logs:
            self.poller.settle(T0 + timedelta(hours=1) + poll.GIVE_UP + timedelta(seconds=1))
        self.assertEqual(self.poller.waiting, {})
        self.assertIn("it stays in Hevy only", logs.output[0])
        self.trigger.assert_not_called()

    def test_no_watch_activity_yet_keeps_waiting(self):
        self.wait_on(workout())
        self.garmin.return_value.activities.return_value = [activity(start="2026-11-06 21:00:00")]
        self.poller.settle(self.NOW)
        self.trigger.assert_not_called()
        self.assertIsNone(self.poller.waiting["w1"].asked)

    def test_the_watch_activity_starts_the_merge(self):
        self.wait_on(workout())
        with self.assertLogs("hevy-trainer-sync.poll", "INFO"):
            self.poller.settle(self.NOW)
        self.trigger.assert_called_once_with("http://h2g", "secret")
        self.assertEqual(self.poller.waiting["w1"].asked, self.NOW)
        # A day either side of the workout, in Garmin's date format.
        self.garmin.assert_called_once_with("tok")
        self.garmin.return_value.activities.assert_called_once_with("2026-11-05", "2026-11-07")

    def test_an_answer_without_status_is_logged_whole(self):
        self.trigger.return_value = {}
        self.wait_on(workout())
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            self.poller.settle(self.NOW)
        self.assertIn("hevy2garmin {}", logs.output[0])

    def test_hevy2garmin_is_asked_again_only_after_its_retry_is_over(self):
        self.wait_on(workout(asked=self.NOW))
        self.poller.settle(self.NOW + poll.ASK_AGAIN - timedelta(seconds=1))
        self.trigger.assert_not_called()
        with self.assertLogs("hevy-trainer-sync.poll", "INFO"):
            self.poller.settle(self.NOW + poll.ASK_AGAIN)
        self.trigger.assert_called_once()

    def test_only_the_newest_waiting_workout_is_asked_about(self):
        # hevy2garmin syncs the newest unfinished workout. The older one has its
        # watch activity, but asking now would have hevy2garmin take the newer.
        self.wait_on(workout("older", start=T0), workout("newer", start=T0 + timedelta(hours=3)))
        self.poller.settle(T0 + timedelta(hours=4, minutes=5))
        self.trigger.assert_not_called()
        self.db.synced_ids.return_value = {"newer"}
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            self.poller.settle(T0 + timedelta(hours=4, minutes=6))
        self.assertIn("watch activity 99 found for 'title older'", "\n".join(logs.output))

    def test_merge_off_or_another_strategy_never_asks(self):
        for stored in ({"merge_mode": False}, {"merge_watch_strategy": "replace"}):
            self.db.merge_settings.return_value = stored
            self.wait_on(workout())
            with self.subTest(stored=stored), self.assertLogs("hevy-trainer-sync.poll", "ERROR") as logs:
                self.poller.settle(self.NOW)
            self.assertIn("not asking it to sync 'title w1'", logs.output[0])
        self.trigger.assert_not_called()
        self.garmin.assert_not_called()

    def test_the_saved_settings_decide_the_match(self):
        self.db.merge_settings.return_value = {"merge_overlap_pct": 100}
        self.garmin.return_value.activities.return_value = [activity(start="2026-11-06 18:05:00")]
        self.wait_on(workout())
        self.poller.settle(self.NOW)
        self.trigger.assert_not_called()


class ActivitiesTest(PollerCase):
    def test_an_expired_token_is_refreshed_through_the_dashboard(self):
        first, second = mock.Mock(), mock.Mock()
        first.activities.side_effect = HttpError(401, "expired", "u")
        second.activities.return_value = [activity()]
        self.garmin.side_effect = [first, second]
        self.db.garmin_di_token.side_effect = ["old", "new"]
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            got = self.poller.activities(workout())
        self.assertEqual(got, [activity()])
        self.assertEqual(self.garmin.call_args_list, [mock.call("old"), mock.call("new")])
        self.dashboard.assert_called_once_with("http://h2g", "pw")
        self.dashboard.return_value.sync_routines.assert_called_once_with([])
        self.assertIn("asking hevy2garmin to refresh it", logs.output[0])

    def test_other_garmin_errors_are_raised(self):
        self.garmin.return_value.activities.side_effect = HttpError(500, "oops", "u")
        with self.assertRaises(HttpError):
            self.poller.activities(workout())
        self.dashboard.assert_not_called()


class MainTest(unittest.TestCase):
    ENV = {"HEVY_API_KEY": "k", "CRON_SECRET": "s", "DATABASE_URL": "postgres://db", "H2G_PASSWORD": "pw"}

    def run_main(self, env, ticks=2, sleep=None):
        sleep = sleep or mock.Mock()
        with (
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(poll, "Client") as client,
            mock.patch.object(poll.Poller, "tick", autospec=True) as tick,
            mock.patch.object(poll.logging, "basicConfig"),
            self.assertLogs("hevy-trainer-sync.poll", "INFO"),
        ):
            rc = poll.main([], sleep=sleep, now=lambda: T0, ticks=ticks)
        return rc, client, tick, sleep

    def test_polls_every_interval_and_reads_back_as_far_as_it_waits(self):
        rc, client, tick, sleep = self.run_main({**self.ENV, "POLL_SECONDS": "30"}, ticks=3)
        self.assertEqual(rc, 0)
        client.assert_called_once_with("k")
        self.assertEqual(tick.call_count, 3)
        poller, now = tick.call_args.args
        self.assertEqual(now, T0)
        self.assertEqual((poller.h2g_url, poller.cron_secret, poller.database_url, poller.password),
                         ("http://hevy2garmin", "s", "postgres://db", "pw"))
        self.assertEqual(poller.since, T0 - poll.GIVE_UP)
        self.assertEqual(poller.started, T0)
        self.assertIsNone(poller.run_cronjob)
        self.assertEqual(sleep.call_args_list, [mock.call(30)] * 2)

    def test_run_cronjob_names_the_mirror(self):
        _, _, tick, _ = self.run_main({**self.ENV, "RUN_CRONJOB": "hevy-trainer-sync"}, ticks=1)
        self.assertEqual(tick.call_args.args[0].run_cronjob, "hevy-trainer-sync")

    def test_defaults(self):
        _, _, tick, sleep = self.run_main(self.ENV, ticks=1)
        tick.assert_called_once()
        sleep.assert_not_called()

    def test_missing_settings_exit_2(self):
        for missing in self.ENV:
            env = {k: v for k, v in self.ENV.items() if k != missing}
            with self.subTest(missing=missing), mock.patch.dict(os.environ, env, clear=True), \
                    mock.patch.object(poll, "Client"), \
                    mock.patch.object(poll.logging, "basicConfig"), \
                    self.assertLogs("hevy-trainer-sync.poll", "ERROR") as logs, \
                    self.assertRaises(SystemExit) as exit_:
                poll.main([], sleep=mock.Mock(), now=lambda: T0, ticks=1)
            self.assertEqual(exit_.exception.code, 2)
            self.assertIn(f"{missing} is not set", logs.output[0])

    def test_runs_forever_without_ticks(self):
        sleep = mock.Mock(side_effect=[None, KeyboardInterrupt])
        with self.assertRaises(KeyboardInterrupt):
            self.run_main(self.ENV, ticks=None, sleep=sleep)
        self.assertEqual(sleep.call_count, 2)


if __name__ == "__main__":
    unittest.main()

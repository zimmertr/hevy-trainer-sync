import os
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from unittest import mock

from hevy_trainer_sync import poll
from hevy_trainer_sync.http import HttpError

T0 = datetime(2026, 11, 5, 18, 0, tzinfo=timezone.utc)


def event(kind="updated", wid="w1", title="Upper", updated="2026-11-05T18:01:00Z"):
    return {"type": kind, "workout": {"id": wid, "title": title, "updated_at": updated}}


class TimeTest(unittest.TestCase):
    def test_iso_is_utc_with_z(self):
        local = T0.astimezone(timezone(timedelta(hours=-8)))
        self.assertEqual(poll.iso(local), "2026-11-05T18:00:00Z")

    def test_parse_accepts_z_and_offsets(self):
        self.assertEqual(poll.parse("2026-11-05T18:00:00Z"), T0)
        self.assertEqual(poll.parse("2026-11-05T18:00:00.000+00:00"), T0)


class NewWorkoutsTest(unittest.TestCase):
    def test_only_updates_after_since_oldest_first(self):
        events = [
            event(wid="late", updated="2026-11-05T18:05:00Z"),
            event(wid="early", updated="2026-11-05T18:01:00Z"),
            event(wid="old", updated="2026-11-05T17:59:00Z"),
            event(wid="same", updated="2026-11-05T18:00:00Z"),
        ]
        got = poll.new_workouts(events, T0)
        self.assertEqual([w[0] for w in got], ["early", "late"])
        self.assertEqual(got[0][2], T0 + timedelta(minutes=1))

    def test_deletions_and_malformed_events_are_skipped(self):
        events = [
            event(kind="deleted"),
            {"type": "updated"},
            {"type": "updated", "workout": {"updated_at": "2026-11-05T18:01:00Z"}},
            {"type": "updated", "workout": {"id": "w1"}},
            event(updated="not a time"),
        ]
        self.assertEqual(poll.new_workouts(events, T0), [])

    def test_missing_title_is_empty(self):
        e = event()
        del e["workout"]["title"]
        self.assertEqual(poll.new_workouts([e], T0)[0][1], "")


class TickTest(unittest.TestCase):
    def setUp(self):
        self.hevy = mock.Mock()
        p = mock.patch.object(poll, "trigger_merge", return_value={"ok": True, "status": "accepted"})
        self.trigger = p.start()
        self.addCleanup(p.stop)

    def test_reads_events_since_the_mark(self):
        self.hevy.workout_events.return_value = []
        self.assertEqual(poll.tick(self.hevy, "http://h2g", "s", T0), T0)
        self.hevy.workout_events.assert_called_once_with("2026-11-05T18:00:00Z")
        self.trigger.assert_not_called()

    def test_each_new_workout_triggers_a_merge_and_moves_the_mark(self):
        self.hevy.workout_events.return_value = [
            event(wid="a", updated="2026-11-05T18:01:00Z"),
            event(wid="b", title="Lower", updated="2026-11-05T18:02:00Z"),
        ]
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            mark = poll.tick(self.hevy, "http://h2g", "s", T0)
        self.assertEqual(mark, T0 + timedelta(minutes=2))
        self.assertEqual(self.trigger.call_args_list, [mock.call("http://h2g", "s")] * 2)
        self.assertIn("workout 'Lower' (b) saved; hevy2garmin accepted", "\n".join(logs.output))

    def test_answer_without_status_is_logged_whole(self):
        self.trigger.return_value = {}
        self.hevy.workout_events.return_value = [event()]
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            poll.tick(self.hevy, "http://h2g", "s", T0)
        self.assertIn("hevy2garmin {}", "\n".join(logs.output))

    def test_hevy_failure_keeps_the_mark(self):
        self.hevy.workout_events.side_effect = HttpError(503, "down", "u")
        with self.assertLogs("hevy-trainer-sync.poll", "WARNING") as logs:
            self.assertEqual(poll.tick(self.hevy, "http://h2g", "s", T0), T0)
        self.assertIn("reading Hevy workout events failed", logs.output[0])
        self.trigger.assert_not_called()

    def test_trigger_failure_stops_before_that_workout(self):
        self.hevy.workout_events.return_value = [
            event(wid="a", updated="2026-11-05T18:01:00Z"),
            event(wid="b", updated="2026-11-05T18:02:00Z"),
        ]
        self.trigger.side_effect = [{"status": "accepted"}, HttpError(502, "bad", "u")]
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            mark = poll.tick(self.hevy, "http://h2g", "s", T0)
        # The first one went through, so the next poll starts after it and retries the second.
        self.assertEqual(mark, T0 + timedelta(minutes=1))
        self.assertIn("asking hevy2garmin to merge 'Upper' failed", "\n".join(logs.output))


    def test_a_network_failure_reading_hevy_keeps_the_mark(self):
        # What killed the pod on 2026-11-05: the lookup of api.hevyapp.com failed.
        self.hevy.workout_events.side_effect = urllib.error.URLError(OSError(-2, "Name or service not known"))
        with self.assertLogs("hevy-trainer-sync.poll", "WARNING") as logs:
            self.assertEqual(poll.tick(self.hevy, "http://h2g", "s", T0), T0)
        self.assertIn("reading Hevy workout events failed: <urlopen error", logs.output[0])
        self.trigger.assert_not_called()

    def test_a_timeout_reading_hevy_keeps_the_mark(self):
        self.hevy.workout_events.side_effect = TimeoutError("timed out")
        with self.assertLogs("hevy-trainer-sync.poll", "WARNING"):
            self.assertEqual(poll.tick(self.hevy, "http://h2g", "s", T0), T0)

    def test_hevy2garmin_unreachable_stops_before_that_workout(self):
        # The dashboard pod restarting: the connection is refused, not answered.
        self.hevy.workout_events.return_value = [
            event(wid="a", updated="2026-11-05T18:01:00Z"),
            event(wid="b", updated="2026-11-05T18:02:00Z"),
        ]
        self.trigger.side_effect = [{"status": "accepted"}, ConnectionRefusedError(111, "Connection refused")]
        with self.assertLogs("hevy-trainer-sync.poll", "INFO") as logs:
            mark = poll.tick(self.hevy, "http://h2g", "s", T0)
        self.assertEqual(mark, T0 + timedelta(minutes=1))
        self.assertIn("asking hevy2garmin to merge 'Upper' failed", "\n".join(logs.output))

    def test_a_bug_is_not_swallowed(self):
        # Only call failures keep the loop going; anything else still crashes loudly.
        self.hevy.workout_events.side_effect = KeyError("events")
        with self.assertRaises(KeyError):
            poll.tick(self.hevy, "http://h2g", "s", T0)


class MainTest(unittest.TestCase):
    ENV = {"HEVY_API_KEY": "k", "CRON_SECRET": "s"}

    def run_main(self, env, ticks=2):
        sleep = mock.Mock()
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(poll, "Client") as client, \
                mock.patch.object(poll, "tick", side_effect=lambda h, u, s, since: since + timedelta(seconds=1)) as tick, \
                mock.patch.object(poll.logging, "basicConfig"), \
                self.assertLogs("hevy-trainer-sync.poll", "INFO"):
            rc = poll.main([], sleep=sleep, now=lambda: T0, ticks=ticks)
        return rc, client, tick, sleep

    def test_polls_every_interval_from_one_interval_back(self):
        rc, client, tick, sleep = self.run_main({**self.ENV, "POLL_SECONDS": "30"}, ticks=3)
        self.assertEqual(rc, 0)
        client.assert_called_once_with("k")
        self.assertEqual(tick.call_count, 3)
        first = tick.call_args_list[0].args
        self.assertEqual(first[1:], ("http://hevy2garmin", "s", T0 - timedelta(seconds=30)))
        # Each tick gets the mark the previous one returned.
        self.assertEqual(tick.call_args_list[2].args[3], T0 - timedelta(seconds=28))
        self.assertEqual(sleep.call_args_list, [mock.call(30)] * 2)

    def test_defaults(self):
        rc, _, tick, sleep = self.run_main(self.ENV, ticks=1)
        self.assertEqual(tick.call_args.args[3], T0 - timedelta(seconds=60))
        sleep.assert_not_called()

    def test_missing_secret_exits_2(self):
        for missing in ("HEVY_API_KEY", "CRON_SECRET"):
            env = {k: v for k, v in self.ENV.items() if k != missing}
            with self.subTest(missing=missing), mock.patch.dict(os.environ, env, clear=True), \
                    mock.patch.object(poll.logging, "basicConfig"), \
                    self.assertLogs("hevy-trainer-sync.poll", "ERROR") as logs, \
                    self.assertRaises(SystemExit) as exit_:
                poll.main([], sleep=mock.Mock(), now=lambda: T0, ticks=1)
            self.assertEqual(exit_.exception.code, 2)
            self.assertIn(f"{missing} is not set", logs.output[0])

    def test_runs_forever_without_ticks(self):
        sleep = mock.Mock(side_effect=[None, KeyboardInterrupt])
        with mock.patch.dict(os.environ, self.ENV, clear=True), \
                mock.patch.object(poll, "Client"), \
                mock.patch.object(poll, "tick", side_effect=lambda h, u, s, since: since) as tick, \
                mock.patch.object(poll.logging, "basicConfig"), \
                self.assertLogs("hevy-trainer-sync.poll", "INFO"), \
                self.assertRaises(KeyboardInterrupt):
            poll.main([], sleep=sleep, now=lambda: T0)
        self.assertEqual(tick.call_count, 2)


if __name__ == "__main__":
    unittest.main()

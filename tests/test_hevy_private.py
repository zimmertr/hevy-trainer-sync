import unittest
from unittest import mock

from hevy_trainer_sync import hevy_private
from hevy_trainer_sync.http import HttpError

FUTURE = "2999-01-01T00:00:00.000Z"
PAST = "2000-01-01T00:00:00.000Z"
PROGRAM_URL = "https://api.hevyapp.com/hevy_trainer/v3/program"
REFRESH_URL = "https://api.hevyapp.com/auth/refresh_token"


def session(**tokens):
    persisted = []
    return hevy_private.Session(dict(tokens), persisted.append), persisted


class HeadersTest(unittest.TestCase):
    def test_bearer_only_with_an_access_token(self):
        s, _ = session(access_token="A", refresh_token="R")
        h = s._headers()
        self.assertEqual(h["x-api-key"], "shelobs_hevy_web")
        self.assertIn("x-client-time", h)
        self.assertEqual(h["Authorization"], "Bearer A")
        s, _ = session(refresh_token="R")
        self.assertNotIn("Authorization", s._headers())


class ExpiredTest(unittest.TestCase):
    def test_expiry(self):
        self.assertFalse(session(access_token="A", expires_at=FUTURE)[0]._expired())
        self.assertTrue(session(access_token="A", expires_at=PAST)[0]._expired())
        self.assertTrue(session(access_token="A")[0]._expired())
        self.assertTrue(session(expires_at=FUTURE)[0]._expired())


@mock.patch.object(hevy_private, "request")
class RefreshTest(unittest.TestCase):
    def test_needs_an_access_token(self, request):
        s, persisted = session(refresh_token="R")
        with self.assertRaisesRegex(RuntimeError, "without an access token"):
            s.refresh()
        request.assert_not_called()
        self.assertEqual(persisted, [])

    def test_rotated_tokens_are_persisted(self, request):
        request.return_value = ({"access_token": "A2", "refresh_token": "R2", "expires_at": FUTURE}, {})
        s, persisted = session(access_token="A", refresh_token="R", expires_at=PAST)
        s.refresh()
        method, url = request.call_args.args
        self.assertEqual((method, url), ("POST", REFRESH_URL))
        self.assertEqual(request.call_args.kwargs["body"], {"refresh_token": "R"})
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer A")
        want = {"access_token": "A2", "refresh_token": "R2", "expires_at": FUTURE}
        self.assertEqual(s.tokens, want)
        self.assertEqual(persisted, [want])

    def test_refresh_token_kept_when_not_rotated(self, request):
        request.return_value = ({"access_token": "A2"}, {})
        s, persisted = session(access_token="A", refresh_token="R")
        s.refresh()
        self.assertEqual(persisted, [{"access_token": "A2", "refresh_token": "R", "expires_at": None}])

    def test_no_access_token_in_the_answer_is_an_error(self, request):
        for answer in (None, [], {"refresh_token": "R2"}):
            request.return_value = (answer, {})
            s, persisted = session(access_token="A", refresh_token="R")
            with self.assertRaisesRegex(RuntimeError, "refresh returned no access token"):
                s.refresh()
            self.assertEqual(persisted, [])
            self.assertEqual(s.tokens["access_token"], "A")


@mock.patch.object(hevy_private, "request")
class GetProgramTest(unittest.TestCase):
    QUERY = {"client_program_updated_at": hevy_private.EPOCH, "client_next_workout_updated_at": hevy_private.EPOCH}

    def test_valid_token_goes_straight_to_the_program(self, request):
        request.return_value = ({"program": {"id": "p"}}, {})
        s, persisted = session(access_token="A", refresh_token="R", expires_at=FUTURE)
        self.assertEqual(s.get_program(), {"id": "p"})
        request.assert_called_once()
        self.assertEqual(request.call_args.args, ("GET", PROGRAM_URL))
        self.assertEqual(request.call_args.kwargs["query"], self.QUERY)
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer A")
        self.assertEqual(persisted, [])

    def test_expired_token_is_refreshed_first(self, request):
        request.side_effect = [({"access_token": "A2", "expires_at": FUTURE}, {}), ({"program": {"id": "p"}}, {})]
        s, persisted = session(access_token="A", refresh_token="R", expires_at=PAST)
        self.assertEqual(s.get_program(), {"id": "p"})
        self.assertEqual([c.args[1] for c in request.call_args_list], [REFRESH_URL, PROGRAM_URL])
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer A2")
        self.assertEqual(len(persisted), 1)

    def test_401_refreshes_and_retries_once(self, request):
        request.side_effect = [
            HttpError(401, "expired", PROGRAM_URL),
            ({"access_token": "A2", "expires_at": FUTURE}, {}),
            ({"program": {"id": "p"}}, {}),
        ]
        s, persisted = session(access_token="A", refresh_token="R", expires_at=FUTURE)
        self.assertEqual(s.get_program(), {"id": "p"})
        self.assertEqual([c.args[1] for c in request.call_args_list], [PROGRAM_URL, REFRESH_URL, PROGRAM_URL])
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer A2")
        self.assertEqual(persisted[0]["access_token"], "A2")

    def test_other_http_errors_are_not_retried(self, request):
        request.side_effect = HttpError(500, "down", PROGRAM_URL)
        s, persisted = session(access_token="A", refresh_token="R", expires_at=FUTURE)
        with self.assertRaises(HttpError) as cm:
            s.get_program()
        self.assertEqual(cm.exception.status, 500)
        request.assert_called_once()
        self.assertEqual(persisted, [])

    def test_the_reply_is_logged_without_its_strings(self, request):
        request.return_value = ({"program": {"id": "p"}, "next_workout": {"weight_kg": 22.68, "title": "Fly"}}, {})
        s, _ = session(access_token="A", refresh_token="R", expires_at=FUTURE)
        with self.assertLogs("hevy-trainer-sync.trainer") as logs:
            s.get_program()
        self.assertIn('"next_workout":{"weight_kg":22.68,"title":"str"}', logs.output[0])
        self.assertNotIn("Fly", logs.output[0])

    def test_unexpected_shape_is_an_error(self, request):
        for answer in (None, {"program": None}, {"program": []}):
            request.side_effect = None
            request.return_value = (answer, {})
            s, _ = session(access_token="A", refresh_token="R", expires_at=FUTURE)
            with self.assertRaisesRegex(RuntimeError, "unexpected program response"):
                s.get_program()


class ShapeTest(unittest.TestCase):
    def test_strings_are_hidden_and_numbers_kept(self):
        self.assertEqual(
            hevy_private.shape({"id": "abc", "sets": [{"reps": 12, "kg": 22.5, "warmup": False, "rpe": None}]}),
            {"id": "str", "sets": [{"reps": 12, "kg": 22.5, "warmup": False, "rpe": None}]},
        )

    def test_long_lists_are_cut_short(self):
        out = hevy_private.shape(list(range(hevy_private.SHAPE_ITEMS + 5)))
        self.assertEqual(len(out), hevy_private.SHAPE_ITEMS + 1)
        self.assertEqual(out[-1], "5 more")


if __name__ == "__main__":
    unittest.main()

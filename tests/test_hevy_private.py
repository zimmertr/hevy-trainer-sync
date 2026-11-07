import unittest
from datetime import UTC, datetime
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

    def test_unexpected_shape_is_an_error(self, request):
        for answer in (None, {"program": None}, {"program": []}):
            request.side_effect = None
            request.return_value = (answer, {})
            s, _ = session(access_token="A", refresh_token="R", expires_at=FUTURE)
            with self.assertRaisesRegex(RuntimeError, "unexpected program response"):
                s.get_program()


@mock.patch.object(hevy_private, "request")
class PreferencesTest(unittest.TestCase):
    def test_both_preferences_with_the_session(self, request):
        request.side_effect = [({"availableWeights": {}}, {}), ({"username": "u"}, {})]
        s, _ = session(access_token="A", refresh_token="R", expires_at=FUTURE)
        self.assertEqual(s.trainer_preferences(), {"availableWeights": {}})
        self.assertEqual(s.user_preferences(), {"username": "u"})
        self.assertEqual([c.args[1] for c in request.call_args_list], [
            "https://api.hevyapp.com/hevy_trainer/user_preferences", "https://api.hevyapp.com/v2/user_preferences"])
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer A")

    def test_anything_but_an_object_is_an_error(self, request):
        request.return_value = ([], {})
        s, _ = session(access_token="A", refresh_token="R", expires_at=FUTURE)
        with self.assertRaisesRegex(RuntimeError, "unexpected v2/user_preferences response"):
            s.user_preferences()


def _page(*starts):
    return ({"workouts": [{"id": str(t), "start_time": t} for t in starts]}, {})


@mock.patch.object(hevy_private, "request")
@mock.patch.object(hevy_private, "WORKOUT_PAGE", 2)
class WorkoutsTest(unittest.TestCase):
    SINCE = datetime.fromtimestamp(100, UTC)

    def ids(self, workouts):
        return [w["id"] for w in workouts]

    def test_pages_back_until_a_workout_predates_the_program(self, request):
        request.side_effect = [_page(400, 300), _page(200, 50), _page(10)]
        s, _ = session(access_token="A", refresh_token="R", expires_at=FUTURE)
        self.assertEqual(self.ids(s.workouts_since("tj", self.SINCE)), ["400", "300", "200"])
        self.assertEqual([c.kwargs["query"] for c in request.call_args_list],
                         [{"username": "tj", "limit": 2, "offset": 0}, {"username": "tj", "limit": 2, "offset": 2}])
        self.assertTrue(request.call_args.args[1].endswith("/user_workouts_paged"))

    def test_stops_on_a_short_or_empty_page_or_an_odd_answer(self, request):
        s, _ = session(access_token="A", refresh_token="R", expires_at=FUTURE)
        for pages, want in (([_page(400)], ["400"]), ([_page(400, 300), _page()], ["400", "300"]),
                            ([({"workouts": None}, {})], []), ([([], {})], [])):
            request.reset_mock()
            request.side_effect = pages
            self.assertEqual(self.ids(s.workouts_since("tj", self.SINCE)), want)

    def test_a_workout_without_a_start_is_kept_and_paging_goes_on(self, request):
        request.side_effect = [({"workouts": [{"id": "a", "start_time": 400}, {"id": "b"}]}, {}), _page()]
        s, _ = session(access_token="A", refresh_token="R", expires_at=FUTURE)
        self.assertEqual(self.ids(s.workouts_since("tj", self.SINCE)), ["a", "b"])

    def test_paging_has_a_ceiling(self, request):
        request.return_value = _page(400, 300)
        s, _ = session(access_token="A", refresh_token="R", expires_at=FUTURE)
        with mock.patch.object(hevy_private, "MAX_WORKOUT_PAGES", 3):
            self.assertEqual(len(s.workouts_since("tj", self.SINCE)), 6)
        self.assertEqual(request.call_count, 3)


class TimeTest(unittest.TestCase):
    def test_unix_seconds_and_iso_strings(self):
        self.assertEqual(hevy_private.parse_time(0), datetime(1970, 1, 1, tzinfo=UTC))
        self.assertEqual(hevy_private.parse_time("2026-09-14T20:26:40.922Z"),
                         datetime(2026, 9, 14, 20, 26, 40, 922000, tzinfo=UTC))
        self.assertEqual(hevy_private.parse_time("2026-09-14T20:26:40"), datetime(2026, 9, 14, 20, 26, 40, tzinfo=UTC))

    def test_anything_else_is_none(self):
        for raw in (None, True, "not a time", [1]):
            self.assertIsNone(hevy_private.parse_time(raw), raw)
        self.assertIsNone(hevy_private.start_of({}))


if __name__ == "__main__":
    unittest.main()

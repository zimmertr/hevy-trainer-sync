import io
import json
import unittest
import urllib.error
from datetime import UTC, datetime
from unittest import mock

from hevy_trainer_sync import http


def response(raw: bytes, headers: dict | None = None):
    res = mock.MagicMock()
    res.__enter__.return_value = res
    res.read.return_value = raw
    res.headers = headers or {}
    return res


class RequestTest(unittest.TestCase):
    def test_get_with_query_decodes_json_and_returns_headers(self):
        with mock.patch("urllib.request.urlopen", return_value=response(b'{"a": 1}', {"X-Y": "z"})) as urlopen:
            body, headers = http.request("GET", "https://h/p", headers={"api-key": "k"}, query={"page": 2, "q": "a b"})
        self.assertEqual(body, {"a": 1})
        self.assertEqual(headers, {"X-Y": "z"})
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "https://h/p?page=2&q=a+b")
        self.assertEqual(req.get_method(), "GET")
        self.assertIsNone(req.data)
        self.assertEqual(req.get_header("Accept"), "application/json")
        self.assertEqual(req.get_header("Api-key"), "k")
        self.assertFalse(req.has_header("Content-type"))
        self.assertEqual(urlopen.call_args.kwargs, {"timeout": 30})

    def test_body_is_sent_as_json(self):
        with mock.patch("urllib.request.urlopen", return_value=response(b"[1, 2]")) as urlopen:
            body, _ = http.request("POST", "https://h/p", body={"ids": ["a"]}, timeout=300)
        self.assertEqual(body, [1, 2])
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "https://h/p")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data), {"ids": ["a"]})
        self.assertEqual(req.get_header("Content-type"), "application/json")
        self.assertEqual(urlopen.call_args.kwargs, {"timeout": 300})

    def test_a_tls_context_is_passed_through(self):
        ctx = object()
        with mock.patch("urllib.request.urlopen", return_value=response(b"")) as urlopen:
            http.request("GET", "https://kubernetes.default.svc/x", context=ctx)
        self.assertEqual(urlopen.call_args.kwargs, {"timeout": 30, "context": ctx})

    def test_empty_response_is_none(self):
        with mock.patch("urllib.request.urlopen", return_value=response(b"")):
            body, headers = http.request("POST", "https://h/p", body=[])
        self.assertIsNone(body)
        self.assertEqual(headers, {})

    def test_http_error_becomes_HttpError_with_status_and_body(self):
        err = urllib.error.HTTPError("https://h/p?x=1", 401, "Unauthorized", {}, io.BytesIO(b"expired \xff"))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(http.HttpError) as cm:
                http.request("GET", "https://h/p", query={"x": 1})
        self.assertEqual(cm.exception.status, 401)
        self.assertEqual(cm.exception.body, "expired �")
        self.assertEqual(str(cm.exception), "HTTP 401 from https://h/p?x=1: expired �")
        self.assertIsNone(cm.exception.__cause__)


def too_many(retry_after: str | None, url: str = "https://h/p"):
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    return urllib.error.HTTPError(url, 429, "Too Many Requests", headers, io.BytesIO(b"slow down"))


class UserAgentTest(unittest.TestCase):
    def test_every_request_names_this_tool(self):
        with mock.patch("urllib.request.urlopen", return_value=response(b"")) as urlopen:
            http.request("GET", "https://h/p")
        self.assertEqual(urlopen.call_args.args[0].get_header("User-agent"), http.USER_AGENT)
        self.assertIn("hevy-trainer-sync", http.USER_AGENT)

    def test_a_callers_user_agent_wins(self):
        with mock.patch("urllib.request.urlopen", return_value=response(b"")) as urlopen:
            http.request("GET", "https://h/p", headers={"User-Agent": "GCM-Android-5.23"})
        self.assertEqual(urlopen.call_args.args[0].get_header("User-agent"), "GCM-Android-5.23")


class TooManyRequestsTest(unittest.TestCase):
    def test_a_429_is_retried_once_after_the_wait_it_asks_for(self):
        sleep = mock.Mock()
        with mock.patch("urllib.request.urlopen", side_effect=[too_many("7"), response(b'{"ok": true}')]) as urlopen:
            body, _ = http.request("POST", "https://h/p", body={"a": 1}, sleep=sleep)
        self.assertEqual(body, {"ok": True})
        sleep.assert_called_once_with(7.0)
        self.assertEqual(urlopen.call_count, 2)
        self.assertIs(urlopen.call_args_list[0].args[0], urlopen.call_args_list[1].args[0])

    def test_the_header_name_is_read_in_any_case(self):
        err = urllib.error.HTTPError("https://h/p", 429, "Too Many", {"retry-after": "2"}, io.BytesIO(b""))
        sleep = mock.Mock()
        with mock.patch("urllib.request.urlopen", side_effect=[err, response(b"")]):
            http.request("GET", "https://h/p", sleep=sleep)
        sleep.assert_called_once_with(2.0)

    def test_a_second_429_raises(self):
        sleep = mock.Mock()
        with mock.patch("urllib.request.urlopen", side_effect=[too_many("1"), too_many("1")]) as urlopen:
            with self.assertRaises(http.HttpError) as cm:
                http.request("GET", "https://h/p", sleep=sleep)
        self.assertEqual(cm.exception.status, 429)
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1.0)

    def test_a_wait_past_the_cap_raises_without_sleeping(self):
        sleep = mock.Mock()
        with mock.patch("urllib.request.urlopen", side_effect=too_many(str(http.MAX_RETRY_AFTER_S + 1))) as urlopen:
            with self.assertRaises(http.HttpError):
                http.request("GET", "https://h/p", sleep=sleep)
        sleep.assert_not_called()
        self.assertEqual(urlopen.call_count, 1)

    def test_a_429_without_retry_after_raises_without_sleeping(self):
        sleep = mock.Mock()
        with mock.patch("urllib.request.urlopen", side_effect=too_many(None)) as urlopen:
            with self.assertRaises(http.HttpError) as cm:
                http.request("GET", "https://h/p", sleep=sleep)
        self.assertEqual(cm.exception.headers, {})
        sleep.assert_not_called()
        self.assertEqual(urlopen.call_count, 1)

    def test_other_statuses_are_never_retried(self):
        err = urllib.error.HTTPError("https://h/p", 503, "Unavailable", {"Retry-After": "1"}, io.BytesIO(b""))
        sleep = mock.Mock()
        with mock.patch("urllib.request.urlopen", side_effect=err) as urlopen:
            with self.assertRaises(http.HttpError) as cm:
                http.request("GET", "https://h/p", sleep=sleep)
        self.assertEqual(cm.exception.headers, {"Retry-After": "1"})
        sleep.assert_not_called()
        self.assertEqual(urlopen.call_count, 1)


class RetryAfterTest(unittest.TestCase):
    NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=UTC)

    def test_seconds(self):
        self.assertEqual(http.retry_after_s(" 30 "), 30.0)

    def test_an_http_date_counts_from_now(self):
        self.assertEqual(http.retry_after_s("Thu, 05 Nov 2026 12:00:45 GMT", now=lambda: self.NOW), 45.0)

    def test_a_date_in_the_past_is_no_wait(self):
        self.assertEqual(http.retry_after_s("Thu, 05 Nov 2026 11:59:00 GMT", now=lambda: self.NOW), 0.0)

    def test_nothing_usable_is_none(self):
        for value in (None, "", "soon", "-5", "1.5", "Thu, 05 Nov 2026 12:00:45"):
            with self.subTest(value=value):
                self.assertIsNone(http.retry_after_s(value, now=lambda: self.NOW))


class HttpErrorTest(unittest.TestCase):
    def test_message_truncates_the_body_but_keeps_it_whole(self):
        e = http.HttpError(500, "x" * 400, "https://h")
        self.assertEqual(str(e), "HTTP 500 from https://h: " + "x" * 300)
        self.assertEqual(len(e.body), 400)


if __name__ == "__main__":
    unittest.main()

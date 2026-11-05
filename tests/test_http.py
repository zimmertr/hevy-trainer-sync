import io
import json
import unittest
import urllib.error
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


class HttpErrorTest(unittest.TestCase):
    def test_message_truncates_the_body_but_keeps_it_whole(self):
        e = http.HttpError(500, "x" * 400, "https://h")
        self.assertEqual(str(e), "HTTP 500 from https://h: " + "x" * 300)
        self.assertEqual(len(e.body), 400)


if __name__ == "__main__":
    unittest.main()

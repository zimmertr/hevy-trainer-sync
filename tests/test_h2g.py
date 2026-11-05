import unittest
from unittest import mock

from hevy_trainer_sync import h2g

LOGIN = ("POST", "http://h2g/api/login")


@mock.patch.object(h2g, "request")
class LoginTest(unittest.TestCase):
    def test_session_cookie_is_kept_without_its_attributes(self, request):
        request.return_value = ({"ok": True}, {"Set-Cookie": "h2g_session=abc; Path=/; HttpOnly"})
        d = h2g.Dashboard("http://h2g/", "pw")
        request.assert_called_once_with(*LOGIN, body={"password": "pw"})
        self.assertEqual(d._h, {"Cookie": "h2g_session=abc"})

    def test_lowercase_header_name(self, request):
        request.return_value = (None, {"set-cookie": "h2g_session=abc"})
        self.assertEqual(h2g.Dashboard("http://h2g", "pw")._h, {"Cookie": "h2g_session=abc"})

    def test_no_or_foreign_cookie_sends_no_cookie(self, request):
        for headers in ({}, {"Set-Cookie": "other=1; Path=/"}):
            request.return_value = (None, headers)
            self.assertEqual(h2g.Dashboard("http://h2g", "pw")._h, {})


@mock.patch.object(h2g, "request")
class RoutesTest(unittest.TestCase):
    def dashboard(self, request):
        request.return_value = (None, {"Set-Cookie": "h2g_session=abc"})
        d = h2g.Dashboard("http://h2g", "pw")
        request.reset_mock()
        return d

    def test_sync_routines(self, request):
        d = self.dashboard(request)
        request.return_value = ({"ok": True, "synced": 2}, {})
        self.assertEqual(d.sync_routines(["r1", "r2"]), {"ok": True, "synced": 2})
        request.assert_called_once_with("POST", "http://h2g/api/routines/sync", headers={"Cookie": "h2g_session=abc"},
                                        body={"ids": ["r1", "r2"]}, timeout=300)

    def test_schedule(self, request):
        d = self.dashboard(request)
        request.return_value = ({"ok": True, "scheduleId": None}, {})
        self.assertEqual(d.schedule("r1", "2026-11-05"), {"ok": True, "scheduleId": None})
        request.assert_called_once_with("POST", "http://h2g/api/routines/r1/schedule", headers={"Cookie": "h2g_session=abc"},
                                        body={"date": "2026-11-05"}, timeout=120)

    def test_unschedule(self, request):
        d = self.dashboard(request)
        request.return_value = ({"ok": True}, {})
        self.assertEqual(d.unschedule("r1", "s1"), {"ok": True})
        request.assert_called_once_with("POST", "http://h2g/api/routines/r1/unschedule", headers={"Cookie": "h2g_session=abc"},
                                        body={"scheduleId": "s1"}, timeout=120)

    def test_empty_answers_are_empty_dicts(self, request):
        d = self.dashboard(request)
        request.return_value = (None, {})
        self.assertEqual(d.sync_routines([]), {})
        self.assertEqual(d.schedule("r1", "2026-11-05"), {})
        self.assertEqual(d.unschedule("r1", "s1"), {})


if __name__ == "__main__":
    unittest.main()

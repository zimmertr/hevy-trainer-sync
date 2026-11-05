import unittest
from unittest import mock

from hevy_trainer_sync import garmin


class MessageTest(unittest.TestCase):
    def test_matches_what_garmin_connect_posts(self):
        self.assertEqual(garmin.message("123456", "Upper W8", "3456789012"), {
            "deviceId": 3456789012,
            "messageUrl": "workout-service/workout/FIT/123456",
            "messageType": "workouts",
            "groupName": None,
            "messageName": "Upper W8",
            "priority": 1,
            "fileType": "FIT",
            "metaDataId": 123456,
        })

    def test_send_posts_a_list_of_messages(self):
        # Garmin answers a bare object with 500 MismatchedInputException.
        sent = {}

        def fake_request(method, url, headers=None, body=None, **_):
            sent.update(method=method, url=url, body=body)
            return {}, {}

        g = garmin.Garmin("tok")
        original = garmin.request
        garmin.request = fake_request
        try:
            g.send_workout("123456", "Upper W8", 3456789012)
        finally:
            garmin.request = original
        self.assertEqual(sent["method"], "POST")
        self.assertTrue(sent["url"].endswith("/device-service/devicemessage/messages"))
        self.assertIsInstance(sent["body"], list)
        self.assertEqual(len(sent["body"]), 1)
        self.assertEqual(sent["body"][0]["metaDataId"], 123456)

    def test_client_sends_bearer_and_native_headers(self):
        g = garmin.Garmin("tok")
        self.assertEqual(g._h["Authorization"], "Bearer tok")
        self.assertEqual(g._h["User-Agent"], "GCM-Android-5.23")
        self.assertIn("X-Garmin-User-Agent", g._h)


@mock.patch.object(garmin, "request")
class LastUsedDeviceTest(unittest.TestCase):
    def test_returns_the_device_id_as_an_int(self, request):
        request.return_value = ({"userDeviceId": "3456789012", "deviceName": "fenix"}, {})
        self.assertEqual(garmin.Garmin("tok").last_used_device_id(), 3456789012)
        self.assertEqual(request.call_args.args,
                         ("GET", "https://connectapi.garmin.com/device-service/deviceservice/mylastused"))
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer tok")

    def test_no_device_is_an_error(self, request):
        for body in (None, {}, {"userDeviceId": None}, [{"userDeviceId": 1}]):
            request.return_value = (body, {})
            with self.assertRaisesRegex(RuntimeError, "no last-used device"):
                garmin.Garmin("tok").last_used_device_id()


if __name__ == "__main__":
    unittest.main()

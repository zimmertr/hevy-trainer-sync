import unittest

from hevy_trainer_sync import garmin


class MessageTest(unittest.TestCase):
    def test_matches_what_garmin_connect_posts(self):
        self.assertEqual(garmin.message("123456", "Upper W8", "3456789012"), {
            "deviceId": 3456789012,
            "messageUrl": "workout-service/workout/FIT/123456",
            "messageType": "workouts",
            "messageName": "Upper W8",
            "priority": 1,
            "fileType": "FIT",
        })

    def test_client_sends_bearer_and_native_headers(self):
        g = garmin.Garmin("tok")
        self.assertEqual(g._h["Authorization"], "Bearer tok")
        self.assertEqual(g._h["User-Agent"], "GCM-Android-5.23")
        self.assertIn("X-Garmin-User-Agent", g._h)


if __name__ == "__main__":
    unittest.main()

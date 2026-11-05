import unittest
from unittest import mock

from hevy_trainer_sync import hevy_public

BASE = "https://api.hevyapp.com/v1"


@mock.patch.object(hevy_public, "request")
class PagesTest(unittest.TestCase):
    def test_follows_page_count_with_the_api_key(self, request):
        request.side_effect = [
            ({"page_count": 2, "routine_folders": [{"id": 1}]}, {}),
            ({"page_count": 2, "routine_folders": [{"id": 2}]}, {}),
        ]
        self.assertEqual(hevy_public.Client("key").folders(), [{"id": 1}, {"id": 2}])
        for page, call in enumerate(request.call_args_list, start=1):
            self.assertEqual(call.args, ("GET", f"{BASE}/routine_folders"))
            self.assertEqual(call.kwargs, {"headers": {"api-key": "key"}, "query": {"page": page, "pageSize": 10}})

    def test_missing_page_count_and_key_mean_one_empty_page(self, request):
        request.return_value = ({}, {})
        self.assertEqual(hevy_public.Client("key").routines(), [])
        request.assert_called_once()
        self.assertEqual(request.call_args.args, ("GET", f"{BASE}/routines"))

    def test_recent_workouts_stops_at_max_pages(self, request):
        request.side_effect = [
            ({"page_count": 9, "workouts": [{"id": "w1"}]}, {}),
            ({"page_count": 9, "workouts": [{"id": "w2"}]}, {}),
        ]
        self.assertEqual(list(hevy_public.Client("key").recent_workouts(2)), [{"id": "w1"}, {"id": "w2"}])
        self.assertEqual([c.kwargs["query"]["page"] for c in request.call_args_list], [1, 2])
        self.assertEqual(request.call_args.args, ("GET", f"{BASE}/workouts"))

    def test_workout_events_since_every_page(self, request):
        request.side_effect = [
            ({"page_count": 2, "events": [{"type": "updated"}]}, {}),
            ({"page_count": 2, "events": [{"type": "deleted"}]}, {}),
        ]
        events = hevy_public.Client("key").workout_events("2026-11-05T18:00:00Z")
        self.assertEqual(events, [{"type": "updated"}, {"type": "deleted"}])
        self.assertEqual(request.call_args.args, ("GET", f"{BASE}/workouts/events"))
        self.assertEqual([c.kwargs["query"] for c in request.call_args_list], [
            {"since": "2026-11-05T18:00:00Z", "page": 1, "pageSize": 10},
            {"since": "2026-11-05T18:00:00Z", "page": 2, "pageSize": 10},
        ])


@mock.patch.object(hevy_public, "request")
class WriteTest(unittest.TestCase):
    def test_create_folder(self, request):
        request.return_value = ({"routine_folder": {"id": 9, "title": "Hevy Trainer"}}, {})
        self.assertEqual(hevy_public.Client("key").create_folder("Hevy Trainer"), {"id": 9, "title": "Hevy Trainer"})
        request.assert_called_once_with("POST", f"{BASE}/routine_folders", headers={"api-key": "key"},
                                        body={"routine_folder": {"title": "Hevy Trainer"}})

    def test_create_routine_unwraps_a_list_or_an_object(self, request):
        c = hevy_public.Client("key")
        request.return_value = ({"routine": [{"id": "r1"}]}, {})
        self.assertEqual(c.create_routine({"title": "Upper"}), {"id": "r1"})
        request.assert_called_with(
            "POST", f"{BASE}/routines", headers={"api-key": "key"}, body={"routine": {"title": "Upper"}}
        )
        request.return_value = ({"routine": {"id": "r2"}}, {})
        self.assertEqual(c.create_routine({"title": "Upper"}), {"id": "r2"})

    def test_update_routine_unwraps_a_list_or_an_object(self, request):
        c = hevy_public.Client("key")
        request.return_value = ({"routine": [{"id": "r1"}]}, {})
        self.assertEqual(c.update_routine("r1", {"title": "Upper"}), {"id": "r1"})
        request.assert_called_with(
            "PUT", f"{BASE}/routines/r1", headers={"api-key": "key"}, body={"routine": {"title": "Upper"}}
        )
        request.return_value = ({"routine": {"id": "r1"}}, {})
        self.assertEqual(c.update_routine("r1", {"title": "Upper"}), {"id": "r1"})


if __name__ == "__main__":
    unittest.main()

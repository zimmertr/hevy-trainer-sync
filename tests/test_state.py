import unittest

from hevy_trainer_sync import state

COOKIE = "{%22access_token%22:%22AAA%22%2C%22refresh_token%22:%22r/+r%22%2C%22expires_at%22:%222026-11-04T23:02:17.449Z%22}"


class BootstrapTest(unittest.TestCase):
    def test_raw_cookie_value(self):
        self.assertEqual(state.bootstrap(COOKIE),
                         {"access_token": "AAA", "refresh_token": "r/+r", "expires_at": "2026-11-04T23:02:17.449Z"})

    def test_decoded_json(self):
        self.assertEqual(state.bootstrap('{"access_token": "A", "refresh_token": "R"}')["expires_at"], None)

    def test_refresh_token_alone_is_refused(self):
        with self.assertRaises(ValueError):
            state.bootstrap('{"refresh_token": "R"}')
        with self.assertRaises(ValueError):
            state.bootstrap("H0+IZfdF0eEdFuHzx40B7euF")


if __name__ == "__main__":
    unittest.main()


class LoadOrBootstrapTest(unittest.TestCase):
    def test_bootstrap_is_saved_so_the_next_run_reads_the_file(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "hevy-session.json")
            first, bootstrapped = state.load_or_bootstrap(path, COOKIE)
            self.assertTrue(bootstrapped)
            self.assertTrue(os.path.exists(path))
            second, bootstrapped = state.load_or_bootstrap(path, "ignored once the file exists")
            self.assertFalse(bootstrapped)
            self.assertEqual(first, second)

    def test_no_file_and_no_cookie_is_an_error(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                state.load_or_bootstrap(os.path.join(d, "missing.json"), None)

import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

_spec = importlib.util.spec_from_file_location(
    "hevy_app", Path(__file__).resolve().parent.parent / "scripts" / "hevy_app.py")
hevy_app = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hevy_app)

# A cut-down decompiler output: two small modules, then a library row.
BUNDLE = """\
    r7 = function(a0, a1, a2, a3, a4, a5, a6) { // Environment: r3
        r1 = [0.4, 0.6];
        r1 = function(a0) { // Original name: getWeeksInCycle, environment: r2
            _fun32857: for(var _fun32857_ip = 0; ; ) switch(_fun32857_ip) {
case 0:
                return r0;
            }
        };
        r1 = function(a0) { // Original name: getCycleNumber, environment: r2
            return r0;
        };
    };
    r6 = 3029;
    r7 = function(a0, a1, a2, a3, a4, a5, a6) { // Environment: r3
        r1 = function(a0) { // Original name: unrelated, environment: r2
            return r0;
        };
    };
    r6 = 3030;
        r0 = {'id': '026FD047', 'title': 'Side Bend (Dumbbell)', 'exercise_type': 'weight_reps', 'equipment_category': 'dumbbell'};
        r0 = {'id': '0000ABCD', 'title': 'Farmer\\'s Walk', 'exercise_type': 'weight_distance', 'equipment_category': 'dumbbell'};
        r0 = {'id': '0000BEEF', 'title': 'No Type Here'};
"""  # noqa: E501
LINES = BUNDLE.splitlines()


class ModulesTest(unittest.TestCase):
    def test_followed_functions_are_grouped_by_module(self):
        mods = hevy_app.modules(LINES)
        self.assertEqual(list(mods), ["getWeeksInCycle,getCycleNumber"])
        self.assertEqual(len(mods["getWeeksInCycle,getCycleNumber"]), 12)

    def test_a_function_outside_any_module_is_skipped(self):
        self.assertEqual(hevy_app.modules(LINES[2:]), {})

    def test_function_numbers_do_not_change_the_fingerprint(self):
        renumbered = [line.replace("32857", "40000") for line in LINES]
        self.assertEqual(hevy_app.fingerprints(LINES), hevy_app.fingerprints(renumbered))
        changed = [line.replace("0.4", "0.5") for line in LINES]
        self.assertNotEqual(hevy_app.fingerprints(LINES), hevy_app.fingerprints(changed))

    def test_a_long_module_is_fingerprinted_function_by_function(self):
        # A second module defining getWeeksInCycle again, as startOfWeek is defined twice in the app.
        again = LINES[0:8] + ["    };", "    r6 = 1;"]
        with mock.patch.object(hevy_app, "WHOLE_MODULE_LINES", 5):
            fp = hevy_app.fingerprints(LINES + again)
        self.assertEqual(sorted(fp), ["getCycleNumber", "getWeeksInCycle", "getWeeksInCycle#2"])

    def test_function_body(self):
        body = hevy_app.function_body(LINES, "getCycleNumber")
        self.assertEqual((body[0].strip()[:24], body[-1].strip()), ("r1 = function(a0) { // O", "};"))
        self.assertEqual(hevy_app.function_body(LINES, "missing"), [])
        self.assertEqual(hevy_app.function_body(["x = function() { // Original name: open, e", "{"], "open"),
                         ["x = function() { // Original name: open, e", "{"])


class LibraryTest(unittest.TestCase):
    def test_rows_with_a_type_and_equipment(self):
        self.assertEqual(hevy_app.library(LINES), {
            "026FD047": ("Side Bend (Dumbbell)", "weight_reps", "dumbbell"),
            "0000ABCD": ("Farmer's Walk", "weight_distance", "dumbbell"),
        })

    def test_source_round_trips(self):
        lib = hevy_app.library(LINES)
        scope = {}
        exec(hevy_app.library_source(lib, "9.9.9"), scope)
        self.assertEqual((scope["APP_VERSION"], scope["EXERCISES"]), ("9.9.9", lib))


class ReportTest(unittest.TestCase):
    def test_nothing_changed(self):
        self.assertIsNone(hevy_app.report("1", {"modules": {"a": "1"}}, {"a": "1"}, {"x": 1}, {"x": 1}))

    def test_rules_and_library_changes_are_named(self):
        text = hevy_app.report("3.3.0", {"app_version": "3.2.5", "modules": {"a": "1", "b": "2"}},
                               {"a": "9", "c": "3"}, {"x": 1}, {"y": 1})
        self.assertIn("Hevy app 3.3.0 differs from 3.2.5", text)
        for line in ("- `a` changed", "- `b` is gone", "- `c` is new", "- `x` is gone", "- `y` is new"):
            self.assertIn(line, text)

    def test_only_the_library_changed(self):
        text = hevy_app.report("3.3.0", {"modules": {}}, {}, {}, {"y": 1})
        self.assertNotIn("Trainer's rules", text)
        self.assertIn("from ?", text)


def _xapk(path: Path) -> Path:
    apk = io.BytesIO()
    with zipfile.ZipFile(apk, "w") as z:
        z.writestr("assets/index.android.bundle", b"hbc")
    xapk = path / "app.xapk"
    with zipfile.ZipFile(xapk, "w") as z:
        z.writestr("manifest.json", json.dumps({"package_name": "com.hevy", "version_name": "3.2.5"}))
        z.writestr("com.hevy.apk", apk.getvalue())
    return xapk


def _fake_decompiler(args, **_):
    Path(args[2]).write_text(BUNDLE)


class MainTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.xapk = _xapk(self.dir)
        for name, value in (("FINGERPRINTS", self.dir / "fp.json"), ("LIBRARY", self.dir / "library.py")):
            p = mock.patch.object(hevy_app, name, value)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(hevy_app.subprocess, "run", side_effect=_fake_decompiler)
        self.run_ = p.start()
        self.addCleanup(p.stop)

    def main(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = hevy_app.main(list(argv))
        return rc, out.getvalue()

    def test_usage(self):
        with mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(hevy_app.main([]), 2)
            self.assertEqual(hevy_app.main(["nope", "x"]), 2)

    def test_update_then_check_finds_nothing(self):
        self.assertEqual(hevy_app.current_library(), {})
        self.assertEqual(self.main("update", str(self.xapk))[0], 0)
        self.assertEqual(json.loads(hevy_app.FINGERPRINTS.read_text())["app_version"], "3.2.5")
        self.assertIn("026FD047", hevy_app.current_library())
        self.assertEqual(self.run_.call_args.args[0][0], "hbc-decompiler")
        rc, out = self.main("check", str(self.xapk))
        self.assertEqual((rc, out.strip()), (0, "Hevy app 3.2.5: nothing hevy-trainer-sync follows has changed."))

    def test_check_reports_a_change(self):
        self.main("update", str(self.xapk))
        hevy_app.FINGERPRINTS.write_text(json.dumps({"app_version": "3.2.4", "modules": {}}))
        rc, out = self.main("check", str(self.xapk))
        self.assertEqual(rc, hevy_app.CHANGED)
        self.assertIn("- `getWeeksInCycle,getCycleNumber` is new", out)


if __name__ == "__main__":
    unittest.main()

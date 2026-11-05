"""The release bump is read from the squash commit's title, and only from it.

GitVersion.yml holds the three patterns and .github/scripts/check_pr_title.py
is the PR check that reads them. The rows are Bluebird's table, which it proved
against the real engine (GitVersion 6.8.2), plus the sequence decision record
0021 measured here. A row that changes means running the engine again, because
a 1.0.0 cut by accident cannot be withdrawn: releases are immutable.
"""

import importlib.util
import io
import os
import re
import runpy
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_pr_title.py"


def load():
    spec = importlib.util.spec_from_file_location("check_pr_title", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = load()
PATTERNS = check.load_patterns(REPO / "GitVersion.yml")

ROWS = [
    # Any type, scoped or not, with `!` before the colon is a major.
    ("feat!: x", "major"),
    ("feat(poll)!: x", "major"),
    ("fix!: x", "major"),
    ("fix(cli)!: x", "major"),
    ("chore!: x", "major"),
    ("build!: x", "major"),
    # GitVersion ignores case.
    ("Fix!: x", "major"),
    ("feat: x", "minor"),
    ("Feat: x", "minor"),
    ("fix: x", "patch"),
    ("docs: x", "patch"),
    ("ci: cut a SemVer release for every merge to main", "patch"),
    # The body never counts: GitHub squashes as title, blank line, PR body.
    ("feat: x\n\nBREAKING CHANGE: y", "minor"),
    ("feat: x\n\nSome prose.\n\nfix!: y", "minor"),
    ("fix: x\n\n+semver: major", "patch"),
    # A `!` anywhere but straight after the type or scope is not a major.
    ("fix: stop the crash!", "patch"),
    ("fix: handle feat!: in titles", "patch"),
    ("fix(poll): explain feat(api)!: titles", "patch"),
    # What the bots send.
    ("build(deps): Bump actions/checkout from 7.0.1 to 7.1.0", "patch"),
    # Read by no pattern: the engine falls back to a patch and the check
    # refuses the title. This repo's titles before 0.1.0 were all like these.
    ("BREAKING CHANGE: x", None),
    ('Revert "feat!: x"', None),
    ("Merge pull request #999 from zimmertr/topic", None),
    ("Poll Hevy every minute and start hevy2garmin's merge right away", None),
]


class TitleTest(unittest.TestCase):
    def test_the_title_decides_the_bump(self):
        for message, expected in ROWS:
            with self.subTest(message=message):
                self.assertEqual(check.bump(message, PATTERNS), expected)

    def test_no_pattern_reads_past_the_first_line(self):
        for pattern in PATTERNS.values():
            self.assertTrue(pattern.pattern.startswith("^"), pattern.pattern)
            self.assertFalse(pattern.flags & re.MULTILINE)
            self.assertNotIn("(?m)", pattern.pattern)

    def test_every_type_the_pipeline_reads_can_be_marked_breaking(self):
        def types(pattern):
            return set(re.match(r"\^\(?([a-z|]+)", pattern.pattern).group(1).split("|"))

        self.assertEqual(types(PATTERNS["major"]), types(PATTERNS["minor"]) | types(PATTERNS["patch"]))

    def test_the_patterns_are_bluebirds(self):
        # Identical to Bluebird's GitVersion.yml (its decision 0080), so a title
        # means the same bump in both repos.
        self.assertEqual(
            PATTERNS["major"].pattern, r"^(feat|fix|perf|refactor|chore|docs|style|test|ci|build)(\([^)\r\n]+\))?!:"
        )
        self.assertEqual(PATTERNS["minor"].pattern, r"^feat(\([^)\r\n]+\))?:")
        self.assertEqual(
            PATTERNS["patch"].pattern, r"^(fix|perf|refactor|chore|docs|style|test|ci|build)(\([^)\r\n]+\))?:"
        )

    def test_a_config_missing_a_pattern_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            config = Path(d) / "GitVersion.yml"
            config.write_text("minor-version-bump-message: '^feat:'\n")
            with self.assertRaisesRegex(ValueError, "no major, patch-version-bump-message line"):
                check.load_patterns(config)

    def test_a_doubled_quote_is_one_quote(self):
        with tempfile.TemporaryDirectory() as d:
            config = Path(d) / "GitVersion.yml"
            config.write_text(
                "major-version-bump-message: '^a!:'\n"
                "minor-version-bump-message: '^it''s:'\n"
                "patch-version-bump-message: '^b:'\n"
            )
            self.assertEqual(check.load_patterns(config)["minor"].pattern, "^it's:")


class MainTest(unittest.TestCase):
    def run_main(self, title):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"PR_TITLE": title}), redirect_stdout(out):
            code = check.main()
        return code, out.getvalue()

    def test_a_major_is_a_warning(self):
        code, out = self.run_main("feat(poll)!: x")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("::warning title=PR title::"), out)
        self.assertIn("releases a major version", out)

    def test_a_patch_is_a_notice(self):
        code, out = self.run_main("build(deps): Bump x from 1.0.0 to 1.0.1")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("::notice title=PR title::"), out)
        self.assertIn("releases a patch version", out)

    def test_an_unread_title_fails(self):
        code, out = self.run_main("Update README")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("::error title=PR title::'Update README'"), out)

    def test_no_title_fails(self):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {}, clear=True), redirect_stdout(out):
            self.assertEqual(check.main(), 1)

    def test_run_as_a_script_exits_with_the_result(self):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"PR_TITLE": "Update README"}), redirect_stdout(out):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path(str(SCRIPT), run_name="__main__")
        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()

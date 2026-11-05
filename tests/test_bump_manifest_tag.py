"""The release bumps exactly one line of Kubernetes-Manifests.

The layout below is the shape of misc/hevy2garmin/kustomization.yml on
2026-11-05, with made-up tags: another image's newTag sits right above ours,
and a comment sits between our name and newTag.
"""

import importlib.util
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "bump_manifest_tag.py"


def load():
    spec = importlib.util.spec_from_file_location("bump_manifest_tag", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bump_manifest_tag = load()

KUSTOMIZATION = """\
images:
  - name: ghcr.io/example/dashboard
    # Built by hand from a fork.
    newTag: 1111111111111111111111111111111111111111
  - name: zimmertr/hevy-trainer-sync
    # Bumped by this repo's CI after every release.
    newTag: {tag}
resources:
  - cronjob.yml
"""

OLD_SHA = "0123456789abcdef0123456789abcdef01234567"


class BumpTest(unittest.TestCase):
    def test_a_commit_tag_becomes_the_version(self):
        # The first release: [0-9a-f]+ would have stopped at "0" and left
        # ".1.0" behind it.
        self.assertEqual(
            bump_manifest_tag.bump(KUSTOMIZATION.format(tag=OLD_SHA), "0.1.0"),
            KUSTOMIZATION.format(tag="0.1.0"),
        )

    def test_a_version_becomes_the_next_version(self):
        self.assertEqual(
            bump_manifest_tag.bump(KUSTOMIZATION.format(tag="0.1.0"), "0.10.12"),
            KUSTOMIZATION.format(tag="0.10.12"),
        )

    def test_newname_and_comments_may_sit_between(self):
        text = "  - name: zimmertr/hevy-trainer-sync\n    newName: example/fork\n    # note\n    newTag: 0.1.0\n"
        self.assertEqual(
            bump_manifest_tag.bump(text, "0.2.0"),
            "  - name: zimmertr/hevy-trainer-sync\n    newName: example/fork\n    # note\n    newTag: 0.2.0\n",
        )

    def test_no_match_is_refused(self):
        text = "  - name: zimmertr/hevy-trainer-sync\n    digest: sha256:abc\n"
        with self.assertRaisesRegex(ValueError, "matched 0"):
            bump_manifest_tag.bump(text, "0.2.0")

    def test_two_matches_are_refused(self):
        text = KUSTOMIZATION.format(tag="0.1.0") * 2
        with self.assertRaisesRegex(ValueError, "matched 2"):
            bump_manifest_tag.bump(text, "0.2.0")

    def test_only_a_release_version_is_written(self):
        for version in ["", "v0.1.0", "0.1", "0.2.0-topic.1", "0.1.0\n"]:
            with self.subTest(version=version):
                with self.assertRaisesRegex(ValueError, "is not a release version"):
                    bump_manifest_tag.bump(KUSTOMIZATION.format(tag="0.1.0"), version)


class MainTest(unittest.TestCase):
    def test_rewrites_the_file_in_place(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "kustomization.yml"
            path.write_text(KUSTOMIZATION.format(tag=OLD_SHA))
            self.assertEqual(bump_manifest_tag.main(["bump", str(path), "0.1.0"]), 0)
            self.assertEqual(path.read_text(), KUSTOMIZATION.format(tag="0.1.0"))

    def test_run_as_a_script(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "kustomization.yml"
            path.write_text(KUSTOMIZATION.format(tag="0.1.0"))
            with mock.patch("sys.argv", ["bump", str(path), "0.1.1"]):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path(str(SCRIPT), run_name="__main__")
            self.assertEqual(cm.exception.code, 0)
            self.assertEqual(path.read_text(), KUSTOMIZATION.format(tag="0.1.1"))


if __name__ == "__main__":
    unittest.main()

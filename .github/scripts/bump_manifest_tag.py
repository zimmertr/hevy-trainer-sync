"""Point Kubernetes-Manifests at a new hevy-trainer-sync release.

Usage: bump_manifest_tag.py <kustomization.yml> <version>

Changes the one `newTag:` line under `name: zimmertr/hevy-trainer-sync` and
nothing else, because `kustomize edit` and a YAML round-trip rewrite the whole
file and strand its comments (decision record 0012). Comment and `newName:`
lines may sit between the two. Any other layout fails rather than guessing.

Standard library only: the release job runs it on the runner's own Python with
no install step.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

IMAGE = "zimmertr/hevy-trainer-sync"

# The old tag is read to the end of its token rather than as hex. Tags were
# commit SHAs until 0.1.0 and are versions since, and `[0-9a-f]+` stops at the
# first dot of `0.1.0`, which would leave `.1.0` stuck behind the new tag.
_TAG_LINE = re.compile(
    r"(name: " + re.escape(IMAGE) + r"\n(?:[ \t]+(?:#.*|newName:.*)\n)*[ \t]+newTag: )\S+"
)

# What GitVersion gives main in ContinuousDeployment mode. Anything else (an
# empty output, a branch's prerelease) must not reach production.
_VERSION = re.compile(r"\d+\.\d+\.\d+")


def bump(text: str, version: str) -> str:
    if not _VERSION.fullmatch(version):
        raise ValueError(f"{version!r} is not a release version")
    new, n = _TAG_LINE.subn(lambda m: m.group(1) + version, text)
    if n != 1:
        raise ValueError(f"expected one {IMAGE} newTag line, matched {n}")
    return new


def main(argv: list[str]) -> int:
    path, version = Path(argv[1]), argv[2]
    path.write_text(bump(path.read_text(), version))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""The Hevy session tokens, kept on disk because the refresh token rotates on every refresh.

Losing the newest refresh token means logging in again by hand, so the file is
written the moment a refresh succeeds, before the new access token is used.
"""

import json
import os
import tempfile


def load(path: str) -> dict | None:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def save(path: str, tokens: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".tokens-")
    with os.fdopen(fd, "w") as f:
        json.dump(tokens, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)

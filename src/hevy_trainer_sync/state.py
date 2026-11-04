"""The Hevy session tokens, kept on disk because the refresh token rotates on every refresh.

Losing the newest refresh token means logging in again by hand, so the file is
written the moment a refresh succeeds, before the new access token is used.
"""

import json
import os
import tempfile
import urllib.parse

REQUIRED = ("access_token", "refresh_token")


def bootstrap(raw: str) -> dict:
    """Tokens from the hevy.com `auth2.0-token` cookie, pasted as-is or already URL-decoded.

    The refresh endpoint wants the access token in the Authorization header as
    well as the refresh token in the body, expired or not, so a refresh token
    on its own cannot start the chain. Hence the whole cookie.
    """
    text = raw.strip()
    try:
        # The cookie keeps its braces literal and encodes the quotes, so it is
        # not valid JSON until unquoted; a pasted decoded copy already is.
        data = json.loads(text)
    except ValueError:
        try:
            data = json.loads(urllib.parse.unquote(text))
        except ValueError:
            raise ValueError("HEVY_SESSION is not the auth2.0-token cookie: expected JSON with access_token and refresh_token") from None
    if not isinstance(data, dict):
        raise ValueError("HEVY_SESSION is not the auth2.0-token cookie: expected a JSON object")
    missing = [k for k in REQUIRED if not data.get(k)]
    if missing:
        raise ValueError(f"HEVY_SESSION is missing {', '.join(missing)}")
    return {"access_token": data["access_token"], "refresh_token": data["refresh_token"], "expires_at": data.get("expires_at")}


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

# 0006. The Hevy session is bootstrapped once from the whole cookie and then lives only on a volume

- Status: Accepted
- Date: 2026-11-04 (git: the merges of #2 and #3)
- Decider: TJ ("This won't keep expiring, right? If so, we need to find a way to auto-renew it")
- Issues and PRs: #2, #3, #9, KM#1819
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Rules, the session bullet

## Context

The private API takes a bearer token from the hevy.com `auth2.0-token` cookie. The access token lasts about 30 minutes, and the refresh token rotates every time it is used. The first deploy took only the refresh token from the secret.

## Decision

`HEVY_SESSION` holds the whole cookie and is read only when the state file is missing. The first run saves both tokens to `HEVY_STATE_FILE` at once, and every refresh rewrites that file. The file sits on the PVC `hevy-trainer-sync-state` and is the only valid copy of the session.

## Evidence

- 2026-11-04, first cluster run: `POST /auth/refresh_token` answered 400 with only the refresh token. It wants the old access token in `Authorization` as well, even an expired one.
- 2026-11-04, second run: the bootstrap token had not expired, so no refresh happened and nothing was saved. The next run had nothing to refresh with. Fixed in #3 by saving on bootstrap.
- 2026-11-05 00:07 UTC: the scheduled run refreshed from the saved file with no secret involved.

## Alternatives rejected

- Refresh token alone in the secret: refused by Hevy (the 400 above).
- Writing the rotated token back into the Kubernetes secret: needs cluster write access from the job, and the secret would still race the file.

## Consequences

Only one process may refresh the session. The CronJob uses `concurrencyPolicy: Forbid`, and a local run against the same session would rotate the cluster's copy out from under it. Losing the PVC means pasting a fresh cookie. `test_state.py` covers bootstrap and save.

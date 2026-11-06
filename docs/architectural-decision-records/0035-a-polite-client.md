# 0035. Every call names this tool, and a 429 is waited out once

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ, 2026-11-05: "Go ahead and raise a PR for all three", on the gaps found against zimmertr/ai-config's `initialize-project` standard (ai-config#10, metered upstreams)
- Issues and PRs: this PR, zimmertr/ai-config#10
- Cited in code as: none
- Guide: [`docs/TRAFFIC.md`](../TRAFFIC.md), Identity and caching; Timeouts and retries

## Context

The shared standard asks a client of a free or rate-limited service to identify itself, honour `Retry-After`, state its caching, and record each provider's terms. This tool sent urllib's default `User-Agent`, failed on any `429` at once, and `docs/DATA.md` recorded no provider's terms.

## Decision

- `http.request` sends `User-Agent: hevy-trainer-sync (+https://github.com/zimmertr/hevy-trainer-sync)` unless the caller sets its own. Garmin's calls keep the Android app's headers.
- A `429` whose `Retry-After` asks for at most 60 seconds (`MAX_RETRY_AFTER_S`) is waited out and retried once. A longer wait, a missing or unreadable header, or a second `429` raises `HttpError` as before. No other status is retried.
- Nothing caches a response, and `docs/TRAFFIC.md` says why.
- `docs/DATA.md` records each provider's terms, dated.

## Evidence

- 2026-11-05: Hevy's public API docs publish no rate limit, and ask that an hourly or daily job not call at exactly xx:00. The CronJob runs at minute 7.
- `docs/DATA.md` records no `429` from any of the three services, so the retry is a precaution, not a fix for an observed failure.

## Alternatives rejected

- Retrying with backoff on any failure: a POST to the dashboard can half-apply, and the CronJob and poller already retry on their next tick.
- Waiting out any `Retry-After`, however long: an hourly run held open for an hour overlaps the next one, which `concurrencyPolicy: Forbid` would then skip.
- A browser `User-Agent` for Hevy's private API, to look like the web app: the calls already carry the web app's key; claiming to be a browser would be a lie about who is calling.

## Consequences

Hevy, hevy2garmin and the private API now see this tool's name and repository on every request. If Hevy ever filters on it, the private API calls are the ones at risk; the fix is a header, not a rewrite.

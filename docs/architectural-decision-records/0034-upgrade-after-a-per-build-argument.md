# 0034. The apt upgrade layer sits after a build argument that changes on every build

- Status: Accepted. Amends [0022](0022-scan-before-production.md)
- Date: 2026-11-05
- Decider: TJ, 2026-11-05: "Go ahead and raise a PR for all three", on the gaps found against zimmertr/ai-config's `initialize-project` standard (ai-config#8)
- Issues and PRs: this PR, zimmertr/ai-config#8
- Cited in code as: none
- Guide: the `Dockerfile`'s comment above the upgrade, and [`docs/CICD.md`](../CICD.md), the image scan

## Context

0022 runs `apt-get upgrade` at build time, because the base image lags Debian's security fixes. That only works while the layer actually reruns. The builds have no layer cache today, so it does. But a cache is the usual fix for a slow build, and once one is added BuildKit would reuse the upgrade layer and a fixed CVE would never arrive, with no sign. Bluebird hit exactly that (its record 0197).

## Decision

The `Dockerfile` declares `ARG APP_COMMIT` and runs the upgrade after it, below the pip install and the source copy, with only `USER` and `ENTRYPOINT` after it. The release passes `github.sha`, the PR build the PR's head commit, and `make build` the checked-out commit.

## Evidence

- Bluebird's record 0197: BuildKit includes every build argument in scope in a `RUN`'s cache key, whether or not the command reads it.
- 2026-11-05: neither `release.yml` nor `pr.yml` sets `cache-from`, and each run starts a fresh builder.

## Alternatives rejected

- Leaving the layer where it was: correct today, and silently wrong the day a cache is added.
- `--no-cache` on every build: throws away the cache for everything, which is what a cache would have been added to keep.

## Consequences

The upgrade runs after `pip install`, so it no longer comes first in the build log. A local rebuild of the same commit reuses the layer; only CI's builds, which ship, are guaranteed fresh.

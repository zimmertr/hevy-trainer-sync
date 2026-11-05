# 0003. The tool lives in its own repo and ships its own image

- Status: Accepted
- Date: 2026-11-04
- Decider: TJ
- Issues and PRs: #1, KM#1818
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

TJ's rule: a 20-line script belongs in Kubernetes-Manifests, and a program gets its own repo with a dedicated container image. The mirror needs a session store, two Hevy clients, a dashboard client and tests, so it is a program. TJ also floated a purpose-built replacement for hevy2garmin one day, and a repo leaves room for that.

## Decision

The code lives in `zimmertr/hevy-trainer-sync` and runs from the image `zimmertr/hevy-trainer-sync`. Kubernetes-Manifests holds only the manifests, under `misc/hevy2garmin`.

## Evidence

No dated measurement.

## Alternatives rejected

- A script in a ConfigMap in Kubernetes-Manifests: too big to review or test there.

## Consequences

Two repos change for any new setting: the code here and the CronJob in Kubernetes-Manifests ([0011](0011-ci-bumps-manifests.md) keeps the image tag in step).

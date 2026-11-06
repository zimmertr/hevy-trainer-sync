# 0022. Production moves only onto a scanned image, and the image takes Debian's fixes at build time

- Status: Accepted; where the upgrade layer sits is amended by [0034](0034-upgrade-after-a-per-build-argument.md)
- Date: 2026-11-05
- Decider: TJ (chose "Trivy scan of pushed image" from Bluebird's release hardening)
- Issues and PRs: #32
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

Nothing checked the image before Kubernetes-Manifests moved onto it. Bluebird scans the digest it pushed and holds production on the previous release when the scan fails (its decision 0105).

## Decision

The release's `scan` job runs Trivy against `zimmertr/hevy-trainer-sync@<digest>`, the bytes Build & Push pushed, for `linux/amd64`, with `ignore-unfixed` and `trivy.yaml`. A fixable Critical or High fails it, and Create GitHub Release and Update Kubernetes Manifests both need it, so production stays where it was. The image and the git tag stay published, and the fix is the next release.

The Dockerfile runs `apt-get upgrade` on the base before installing anything, and CI builds without a layer cache, so each release takes Debian's packages as they are that day.

## Evidence

- 2026-11-05: Trivy 0.68.1 on the running image, `zimmertr/hevy-trainer-sync:cf7bace5041fae7329e70f931bc511b53b1d1ac1`, found two fixable Highs: CVE-2026-109518 in `apt` and `libapt-pkg7.0` 3.0.3, fixed in 3.0.4. Python packages were clean. Without the upgrade, the first release would have failed its own scan.
- 2026-11-05: the newest `python:3.13-slim` (`sha256:ae14d4ce8771…`) still had apt 3.0.3, and `apt-get -s upgrade` in it offered 3.0.4 from Debian-Security.

## Alternatives rejected

- Scanning the PR's image instead: the squash commit is built again on main, so the PR's image is not the one that ships.
- Waiting for the base image to catch up: it lagged on the day this was written, and the gate would have held every release until it did.

## Consequences

A new fixable High in Debian or a Python package blocks releases until a rebuild picks up the fix, or a pin moves. Nothing re-scans the running image between releases; Bluebird's weekly scan was not brought over.

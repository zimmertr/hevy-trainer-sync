# 0011. CI bumps the image tag in Kubernetes-Manifests with one self-merging PR

- Status: Accepted
- Date: 2026-11-05 (git: the merge of #5)
- Decider: TJ ("can we update CI to auto-push to KM similar to what we do with Bluebird")
- Issues and PRs: #5
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

Every image change needed a hand-made Kubernetes-Manifests PR and an explicit "merge" from TJ.

## Decision

The `update-manifests` job runs after `image` on a push to main. It force-pushes the fixed branch `chore/hevy-trainer-sync-image` fresh from Kubernetes-Manifests main, opens or updates one PR, and arms auto-merge. It authenticates with the `GH_PAT` repository secret.

## Evidence

- 2026-11-05: merges of #6, #15 and #17 produced KM#1824, KM#1825 and KM#1826, each merged within about a minute.

## Alternatives rejected

- A new branch per build: a pile of PRs when merges come quickly.
- Argo CD Image Updater: not what Bluebird uses, and it writes back to git in its own format.

## Consequences

A change to env vars or secrets still needs a hand-made Kubernetes-Manifests PR. The bump only touches the tag.

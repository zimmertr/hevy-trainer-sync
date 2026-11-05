# 0004. The repo is public and licensed GPL-3.0

- Status: Accepted
- Date: 2026-11-04
- Decider: TJ
- Issues and PRs: #1
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

A new repo needs a license and a visibility before its first commit.

## Decision

Public, GPL-3.0 (`LICENSE`).

## Evidence

No dated measurement.

## Alternatives rejected

- Private: nothing in the code is secret; credentials only ever come from the environment.
- A permissive or source-available license: TJ chose copyleft.

## Consequences

Nothing secret may be committed, including test fixtures cut from real responses: strip tokens and ids first.

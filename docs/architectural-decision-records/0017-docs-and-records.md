# 0017. Docs and decision records are kept the way Bluebird keeps them

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ ("create a docs directory in the repo and start building ADRs for every decision we make. Similar to what Bluebird does today")
- Issues and PRs: the PR that added `docs/`
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Documentation

## Context

The decisions behind this tool were spread across a chat, PR bodies and issue comments.

## Decision

Prose lives in `docs/`: architecture, CI/CD, configuration, usage, data sources, traffic and development. Every decision gets a record in `docs/architectural-decision-records/`, linked from the `CLAUDE.md` rule it explains. A change that makes a doc untrue updates it in the same PR. Bluebird's `API.md`, `LIMITS.md` and `STYLES.md` have no counterpart: this tool serves no API, enforces no caps and has no UI.

## Evidence

No dated measurement.

## Alternatives rejected

- Keeping everything in the README: the README is TJ's and stays short.

## Consequences

The README stays as TJ wrote it and links to `docs/`. Its variable table and `docs/CONFIGURATION.md` must be changed together.

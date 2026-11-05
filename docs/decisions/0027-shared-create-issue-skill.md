# 0027. The create-issue skill is shared from zimmertr/ai-config, and this repo's specifics live in CLAUDE.md

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ ("Lets move create-issue skill to it as well. Raise a PR to bluebird and hevy trainer repos deleting the create issue skill.")
- Issues and PRs: zimmertr/ai-config#1, this PR
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Issues

## Context

This repo and Bluebird each kept a copy of `create-issue` in `.claude/skills/`. They shared one flow (0013) and had already drifted apart: Bluebird's copy had its summary example and its reader checklist, and this one had neither.

## Decision

The skill lives once, in `claude/skills/create-issue/` of zimmertr/ai-config, linked into `~/.claude/skills`. It reads four things from this repo's `CLAUDE.md`, under Issues: who reads the summary, the gates for Acceptance Criteria, the constraints for the agent notes, and the area labels. This repo's copy is deleted, and those four come from it.

## Evidence

- 2026-11-05: a diff of the two copies showed one flow and different examples, gates, constraints and areas, with 147 lines in Bluebird's and 108 in this repo's.

## Alternatives rejected

- Keeping a copy per repo: they drift, as the diff showed.
- A plugin marketplace now: planned in zimmertr/ai-config's issues; a user-level skill works today.

## Consequences

Filing an issue here needs the skill installed at user level, which only TJ's machine has. Changing the flow is a PR to zimmertr/ai-config; changing this repo's reader, gates, constraints or areas is a change to this `CLAUDE.md`.

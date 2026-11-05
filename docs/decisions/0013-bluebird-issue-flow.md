# 0013. Issues follow Bluebird's create-issue flow and labels

- Status: Accepted
- Date: 2026-11-05 (git: the merge of #15)
- Decider: TJ ("Look at how Bluebird creates labels. Reproduce that here")
- Issues and PRs: #7 to #14, #15
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Issues

## Context

The first eight issues were filed with plain bodies and no labels.

## Decision

Every issue uses `.claude/skills/create-issue/SKILL.md`: a two-sentence summary, then Problem, Proposed Solutions, Implementation Plan, Acceptance Criteria, Notes for an AI agent and Notes for a human, trimmed with the hemingway and humanizer skills. Every issue gets one priority (`P1`, `P2`, `P3`), one type, its area labels, and the Claude Code session UUID as a label. Templates are in `.github/ISSUE_TEMPLATE/`.

## Evidence

No dated measurement.

## Alternatives rejected

- Plain issues: hard to triage on a board and missing what an implementing agent needs.

## Consequences

Each session creates its own UUID label before filing.

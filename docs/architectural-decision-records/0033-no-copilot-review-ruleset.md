# 0033. There is no Copilot review ruleset

- Status: Accepted. Supersedes the ruleset part of [0024](0024-branch-protection.md)
- Date: 2026-11-05
- Decider: TJ, 2026-11-05: "Then remove it from AI Config and turn it off for both repos."
- Issues and PRs: this PR, zimmertr/ai-config#14
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

0024 added Bluebird's "Copilot review for default branch" ruleset. It never produced a review here or on Bluebird.

## Decision

The ruleset is deleted, on this repo and on Bluebird. Branch protection is otherwise unchanged.

## Evidence

- 2026-11-05: before the delete, the ruleset's three rules were `deletion`, `non_fast_forward` and `copilot_code_review`. Branch protection on `main` already had `allow_force_pushes` and `allow_deletions` off, with admins enforced, so deleting the ruleset left main as protected as before.
- 2026-11-05: `gh api repos/zimmertr/hevy-trainer-sync/rulesets` returns an empty list after the delete.

## Alternatives rejected

- Keeping the ruleset until Copilot review becomes available: TJ chose to remove it.

## Consequences

No automated reviewer comments on PRs. If one is wanted later, it is a new decision and a new record.

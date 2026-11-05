# 0028. Decision records live in `docs/architectural-decision-records/`, the name every new project uses

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ ("Update docs/decisions path."), after setting `docs/architectural-decision-records/` as the folder for every new project in zimmertr/ai-config's `initialize-project` skill
- Issues and PRs: this PR, zimmertr/ai-config#1, zimmertr/bluebird#867
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Documentation

## Context

The records lived in `docs/decisions/`. TJ's `initialize-project` skill sets `docs/architectural-decision-records/` for every new project, and Bluebird moved its records there the same day.

## Decision

The folder is `docs/architectural-decision-records/`. File names, numbers, the index and every record's text stay as they were, and records keep linking each other by bare file name. Every link and mention of the old path, in `CLAUDE.md`, the `docs/` pages and the records, moves to the new one.

## Evidence

- 2026-11-05: 10 files carried the old path. After the move every relative Markdown link in the repo resolves from its own file (152 checked); the one that doesn't is the example inside a code span in the index's how-to.
- No code, test or workflow reads the path.

## Alternatives rejected

- Keeping `docs/decisions/`: this repo would be the one on a different name.

## Consequences

Links from outside the repo to the old path break; GitHub doesn't redirect a moved folder's files.

# 0018. Every change ships with tests, and coverage stays at 100% of lines and branches

- Status: Superseded by [0032](0032-coverage-aims-at-100.md)
- Date: 2026-11-05
- Decider: TJ ("I want to have 100% test coverage for this tool. All new features and changes must include tests")
- Issues and PRs: the PR that added the coverage gate
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Tests

## Context

The first tests covered only the pure modules (`build`, `state`, `schedule`, `garmin.message`). The two bugs found in the first live runs (#19, #20) were in code no test reached.

## Decision

The `test` job runs the suite under `coverage` with branch coverage on and `fail_under = 100`. A PR that drops below 100% fails CI. The only exclusion is the `if __name__ == "__main__":` idiom. Tests never touch the network or a real database.

## Evidence

No dated measurement.

## Alternatives rejected

- A lower threshold: lets the untested remainder grow back.
- Line coverage only: misses the untaken side of an `if`, which is where #19 hid.

## Consequences

Every new branch needs a test that takes it. Tests run in CI, and locally only inside Docker when CI cannot answer the question.

# 0032. Coverage aims at 100% and is reported on every PR, without a floor

- Status: Accepted. Supersedes [0018](0018-full-coverage.md)
- Date: 2026-11-05
- Decider: TJ, 2026-11-05: "Strive for 100%, don't hold it to that requirement." For the shared standard the same day: "Strive for 100% coverage but don't do weird things to get there."
- Issues and PRs: this PR, zimmertr/ai-config#7
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Tests

## Context

0018 failed CI below 100% of lines and branches. The shared `initialize-project` standard (zimmertr/ai-config#7) changed to aiming at 100% without a gate, after a review against Bluebird found its coverage is a report with no floor (Bluebird record 0187): a floor rewards a test that runs a line without asserting anything about it.

## Decision

`.coveragerc` has no `fail_under`. The `test` job still runs the suite under `coverage` with branch coverage on, and prints the report to the log and to the run's summary. The aim is 100%. A gap gets a test of the behaviour behind it, or a written reason beside the code. No test exists only to reach a line. Every change still ships with tests, the only exclusion is still the `if __name__ == "__main__":` idiom, and tests still never touch the network or a real database.

## Evidence

- 2026-11-05: the suite was at 100% of lines and branches when the gate came off, so nothing regressed with it.

## Alternatives rejected

- Keeping the gate (0018): TJ chose not to hold the repo to it.
- A lower floor, such as 95%: still rewards a test written for the number, just less often.

## Consequences

A PR can now merge with less than 100%, so the report on the run's summary is the only signal, and the gates in `CLAUDE.md` ask that every new gap carry a test or a reason. A drop is caught in review, not by CI.

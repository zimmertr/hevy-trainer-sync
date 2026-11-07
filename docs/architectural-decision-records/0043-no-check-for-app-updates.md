# 0043. Nothing checks for Hevy app updates; a mismatch in the app is how one shows

- Status: Accepted. Amends 0042
- Date: 2026-11-07
- Decider: TJ ("Sounds over-engineered", then "Yes, lets drop it")
- Issues and PRs: #58, #59
- Cited in code as: `trainer_rules.py`
- Guide: [`CLAUDE.md`](../../CLAUDE.md), How it fits together, the prescriptions bullet

## Context

[0042](0042-trainer-prescriptions-by-the-apps-rules.md) added a weekly GitHub workflow that downloaded the latest Hevy Android app from APKPure, decompiled it, and opened an issue when the functions `trainer_rules.py` follows or the exercise library changed. It took a script, a hashed lock for the decompiler, a fingerprint file and its tests.

## Decision

- The workflow, the script, its lock, the fingerprints and their tests are gone.
- `library.py` stays, read from app 3.2.5. An exercise added in a later app version isn't in it and keeps its last logged weight.
- If an app update changes a rule, the watch and the app show different weights. TJ sees both every session, and that mismatch is how we find out.

## Alternatives rejected

- **Keep the weekly check:** it depended on APKPure and a decompiler, and Hevy reorganising its code without changing a rule would still open a false P1.

## Consequences

- A small rule change, such as different rounding, can go unnoticed until a weight on the watch differs from the app's.
- Following a new app version means downloading and reading it by hand, as for 3.2.5.

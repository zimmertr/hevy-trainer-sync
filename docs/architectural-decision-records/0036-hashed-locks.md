# 0036. The image installs a hashed lock compiled from its direct pins

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ, 2026-11-05: "Go ahead and raise a PR for all three", on the gaps found against zimmertr/ai-config's `initialize-project` standard (ai-config#8)
- Issues and PRs: this PR, zimmertr/ai-config#8
- Cited in code as: none
- Guide: [`docs/DEVELOPMENT.md`](../DEVELOPMENT.md), the `make` targets

## Context

`requirements.txt` pinned the two direct dependencies by version, and pip resolved everything under them at build time, with no hash checked. A republished or tampered file on PyPI would have installed without complaint. Bluebird locks and hashes every package (its record 0099).

## Decision

- `requirements.in` and `requirements-dev.in` hold the direct pins. `make lock` compiles `requirements.txt` and `requirements-dev.txt` from them with pip-compile 7.5.3 and `--generate-hashes`, on the image's Python. The dev lock is constrained to the image's.
- The image, the `test` job and the `make` targets install with `--require-hashes`.
- `tests/test_dependency_lock.py` fails when a direct pin isn't locked at its version, the dev lock disagrees with the image's, a locked package has no hash, an install drops `--require-hashes`, or the pip Dependabot entry loses its cooldown.
- Dependabot recompiles the locks from the `.in` files.

## Evidence

- 2026-11-05: `make lock` locked `psycopg` and `psycopg-binary` 3.2.9 and `tzdata` 2025.2, the same versions as before, with 69 hashes in `requirements.txt` and 188 in `requirements-dev.txt` (which adds `coverage` 7.17.2).

## Alternatives rejected

- Version pins without hashes: what this replaces.
- A lock tool other than pip-compile: Dependabot recompiles pip-compile's output directly, and Bluebird already uses it.

## Consequences

A pin changes in its `.in` file, and the PR carries the regenerated lock. A hand edit to a lock fails the hash check at install, or the test above.

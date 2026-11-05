# 0021. Every merge to main cuts a SemVer release, and GitVersion reads the bump from the PR title

- Status: Accepted. Supersedes the tag convention of 0005
- Date: 2026-11-05
- Decider: TJ ("Lets make it so that CI cuts releases for each commit and follows semantic versioning and gitversion. Basically replicate what we have in place for Bluebird today."), and, the same day, 0.1.0 as the first version, squash-only merges and immutable releases
- Issues and PRs: #32
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

The image was tagged with the commit SHA and `latest`. Nothing said what changed between two builds, or whether a change could break the manifests. Bluebird already versions every merge with GitVersion and conventional PR titles, and has settled its edge cases (its decision 0080).

## Decision

`release.yml` runs on every push to main. GitVersion 6.8.2, pinned exactly, computes the version from the squash commit's title with Bluebird's three patterns, unchanged:

| PR title | Bump |
|---|---|
| any listed type with `!` before the colon: `feat!:`, `fix(poll)!:` | major |
| `feat:`, `feat(scope):` | minor |
| `fix`, `perf`, `refactor`, `chore`, `docs`, `style`, `test`, `ci`, `build`, each with an optional `(scope)` | patch |

The body never counts. The image is pushed as `zimmertr/hevy-trainer-sync:<version>` and nothing else, the commit is tagged `v<version>`, a GitHub release is made with notes from the PR titles, and Kubernetes-Manifests is bumped to the version. Each piece is made only when missing, so a re-run finishes a failed release. The `PR Title` check refuses a title no pattern reads.

The first release is 0.1.0. The repo merges by squash only, with the PR title as the commit title and the PR body as its message, and its GitHub releases are immutable.

## Evidence

GitVersion 6.8.2 in Docker, on a throwaway copy of main at cf7bace, 2026-11-05. Each row is one commit on top of the last, tagged with its result before the next, the way the workflow tags:

| Squash title | Version |
|---|---|
| `ci: cut a SemVer release for every merge to main` (this PR) | 0.1.0 |
| `fix: x` | 0.1.1 |
| `feat: x` | 0.2.0 |
| `build(deps): Bump actions/checkout from 7.0.1 to 7.1.0` | 0.2.1 |
| `Update README` | 0.2.2 |
| `fix: x` with a `BREAKING CHANGE: y` footer | 0.2.3 |
| `feat(poll)!: x` | 1.0.0 |
| `chore: y` | 1.0.1 |

Two things had to be found the same way. With Bluebird's `strategies: [Mainline]` alone, `next-version` is ignored and the untagged history gives 0.0.17. With `ConfiguredNextVersion` added, a bare `next-version: 0.1.0` fails with "Failed to parse 0.1.0 into a Semantic Version", because it is parsed against `tag-prefix: 'v'`. `'v0.1.0'` gives 0.1.0.

## Alternatives rejected

- Letting GitVersion count the untagged history: 0.0.17, a number that means nothing.
- 1.0.0 first: TJ chose 0.1.0, leaving room to change the interface before 1.0.
- Keeping `latest` beside the version: Kubernetes-Manifests pins the version, and a moving tag invites something to pull it.
- Seeding with a hand-pushed `v0.1.0` tag: the tag would name a commit no release built.

## Consequences

Every PR title is `type(scope): summary`. The titles before #32 were plain sentences, which the check now refuses. A major needs `!` in the title. `tests/test_release_titles.py` holds the patterns to Bluebird's and to the rows above, and a change to the engine version means running this table again. The SHA tags already on Docker Hub stay there, and nothing new is tagged that way.

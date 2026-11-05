# 0012. CI edits the newTag line in place instead of running kustomize edit

- Status: Accepted
- Date: 2026-11-05 (git: the merge of #18)
- Decider: TJ (LGTM on #18 and KM#1827)
- Issues and PRs: #18, KM#1824, KM#1827
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

The first version of the bump ran `kustomize edit set image`, which rewrites the whole `kustomization.yml`.

## Decision

A short Python step changes only the `newTag:` line under `name: zimmertr/hevy-trainer-sync`, tolerating comment and `newName:` lines between them, and fails unless it matched exactly once.

## Evidence

- 2026-11-05: KM#1824 changed 15 lines and removed 12 to bump one tag. It reordered keys, reindented lists, and left both image comments above the list. KM#1827 restored the file. KM#1828 and KM#1829 then changed one line each.

## Alternatives rejected

- `kustomize edit set image`: the diff above.
- A YAML round-trip in Python: loses comments the same way.

## Consequences

A layout the pattern does not recognise fails the job rather than guessing. Kustomize no longer needs installing in CI.

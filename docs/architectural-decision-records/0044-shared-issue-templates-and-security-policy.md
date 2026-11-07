# 0044. The issue templates and security policy come from `zimmertr/.github`

- Status: Accepted. Supersedes 0013 in part (where the templates live)
- Date: 2026-11-07
- Decider: TJ ("Yggdrasil should be shipping defaults to .github repos for each account/org. Then repos should be able to override those with their own repo configs. ... Other repos are open game")
- Issues and PRs: zimmertr/yggdrasil#8 (step 6.17)
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), the security scanning bullet

## Context

This repo kept its own `.github/ISSUE_TEMPLATE/` and `SECURITY.md`, copied from Bluebird and tailored. zimmertr/yggdrasil now writes one shared set into `zimmertr/.github` (its record 0041), and GitHub shows those files in every repo of the account that has none of its own. A repo's own templates hide every shared one.

## Decision

- This repo's templates and `SECURITY.md` are deleted, so the shared ones show here.
- A change to them goes to `community-health-files/` in zimmertr/yggdrasil.

## Evidence

- 2026-11-07: `zimmertr/3D-Models`, which has no templates of its own, offers the shared "Bug report" and "Proposal" and the shared security policy.

## Alternatives rejected

- **Keep the tailored copies:** a repo may override the shared files, but TJ kept overrides only in Bluebird and TJs-Kubernetes-Service.

## Consequences

- Blank issues are off, as in the shared `config.yml`.
- The shared bug template asks for the area labels `CLAUDE.md` lists, instead of naming them.
- The security policy no longer names Hevy, Garmin Connect, Strava and hevy2garmin as out of scope; the shared one puts every third-party service out of scope.

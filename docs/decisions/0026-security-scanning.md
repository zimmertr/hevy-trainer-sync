# 0026. GitHub's security scanning is on, and the released image is re-scanned weekly

- Status: Accepted
- Date: 2026-11-05
- Decider: TJ ("github security scanning. Just like Bluebird.")
- Issues and PRs: #35
- Cited in code as: none
- Guide: [`CLAUDE.md`](../../CLAUDE.md), Working in this repo

## Context

Secret scanning and push protection were on, as GitHub turns them on for a public repo. Nothing scanned the code, nothing gave a reporter a private channel, and the image was scanned only once, at release (0022).

## Decision

- **CodeQL default setup** for `actions` and `python`, the default query suite, on every PR and push and weekly.
- **Secret scanning with push protection**, left on.
- **Private vulnerability reporting** is on, and `SECURITY.md` points reporters to it.
- **`image-scan.yml`** scans the latest release's image every Monday at 14:17 UTC with Trivy and `trivy.yaml`. It uploads SARIF to the Security tab under `trivy-released-image` and fails only on a fixable Critical or High.

## Evidence

Bluebird's settings, read through the API on 2026-11-05: CodeQL default setup (weekly, default suite, its languages), secret scanning and push protection on, non-provider patterns and validity checks off, private vulnerability reporting on, and the same weekly scan.

## Alternatives rejected

- A CodeQL workflow file instead of default setup: Bluebird uses default setup, and there is nothing here to customise.

## Consequences

A CVE published after a release turns the Monday run red until a rebuild fixes it; see `docs/CICD.md`, The weekly image scan. CodeQL findings appear in the Security tab and on PRs, but nothing makes them a required check.

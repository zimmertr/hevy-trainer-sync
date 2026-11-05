# Security Policy

## Supported Versions

hevy-trainer-sync is a rolling release. The only supported version is the latest
release, published as the newest `zimmertr/hevy-trainer-sync` tag on Docker Hub
and listed under [Releases](https://github.com/zimmertr/hevy-trainer-sync/releases).
Older tags stay pullable but get no fixes; a fix ships as the next release.

| Version          | Supported          |
| ---------------- | ------------------ |
| Latest release   | :white_check_mark: |
| Older image tags | :x:                |

## Reporting a Vulnerability

Please report vulnerabilities privately through GitHub:
[Report a vulnerability](https://github.com/zimmertr/hevy-trainer-sync/security/advisories/new).
Do not open a public issue for security problems.

Include what you found, where it lives (file, workflow, or image), and how to
reproduce it. A proof of concept helps but is not required.

What to expect:

- **Acknowledgement** within a few days. This is a one-person project, so
  response times are best effort.
- **Fix**: a confirmed vulnerability is fixed in the next release. Every merge
  to main releases and deploys, so a fix is live as soon as it merges.
- **Credit** in the advisory and release notes, unless you'd rather not.

## Scope

In scope: this repository's code, the Docker image, and the CI/CD workflows.

Out of scope: the services it talks to (Hevy, Garmin Connect, Strava) and
[hevy2garmin](https://github.com/drkostas/hevy2garmin) itself. Report issues in
those to their maintainers.

There is no bounty program. Reports are still appreciated.

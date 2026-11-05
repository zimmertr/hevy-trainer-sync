# Notices

hevy-trainer-sync itself is licensed under the [GNU General Public License v3.0](LICENSE). This file credits the third parties it is built on: the services it talks to, and the software bundled into the shipped image.

## Services

- **Hevy** ([hevy.com](https://www.hevy.com)): the public API ([docs](https://api.hevyapp.com/docs)), used under a Hevy Pro API key, and the private Trainer endpoint the web app uses. Hevy is not affiliated with this project. [docs/DATA.md](docs/DATA.md) describes both.
- **Garmin Connect**: reached only through the session hevy2garmin keeps. Garmin is not affiliated with this project.
- **[hevy2garmin](https://github.com/drkostas/hevy2garmin)** by drkostas, MIT License. This tool drives its dashboard and reads its database; none of its code is copied here.

## Bundled in the image

Read from `zimmertr/hevy-trainer-sync:0.1.4` on 2026-11-05. The release's SBOM attestation is the full list, including the Debian packages under the base image (`docker buildx imagetools inspect zimmertr/hevy-trainer-sync:<version> --format '{{ json .SBOM }}'`).

| Software | Version | License |
|---|---|---|
| Python, from the `python:3.13-slim` base image | 3.13 | Python Software Foundation License |
| [psycopg](https://www.psycopg.org/) and `psycopg-binary`, which bundles libpq | 3.2.9 | GNU LGPL v3 |
| [tzdata](https://github.com/python/tzdata) | 2025.2 | Apache License 2.0 |
| [pip](https://pip.pypa.io/), from the base image | 26.2.2 | MIT License |
| Debian 13, under the base image | | Each package's own license; see the SBOM |

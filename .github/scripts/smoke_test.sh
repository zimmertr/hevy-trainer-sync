#!/usr/bin/env bash
# What only a built image can show: the entry point starts, the dependencies
# load on the image's own Python (a new Python minor can ship before a wheel
# for it does), the zoneinfo data is there for TZ, and the process runs as the
# unprivileged user the manifests expect.
#
# The Docker Build check runs this against the PR's image, with its tag in
# $IMAGE. Locally: make build && IMAGE=hevy-trainer-sync:dev .github/scripts/smoke_test.sh
set -uo pipefail

fail=0
check() { # label, actual, expected
  if [ "$2" = "$3" ]; then echo "  ok    $1"; else echo "  FAIL  $1 (want '$3', got '$2')"; fail=1; fi
}
check "the entry point answers --help" \
  "$(docker run --rm "$IMAGE" --help | head -n1 | cut -d' ' -f1-2)" "usage: hevy-trainer-sync"
check "psycopg loads on the image's Python" \
  "$(docker run --rm --entrypoint python3 "$IMAGE" -c 'import psycopg; print(psycopg.pq.version() > 0)')" "True"
check "the zoneinfo data is installed" \
  "$(docker run --rm --entrypoint python3 "$IMAGE" -c 'import zoneinfo; print(zoneinfo.ZoneInfo("America/Los_Angeles").key)')" "America/Los_Angeles"
check "it runs as UID 1000" \
  "$(docker run --rm --entrypoint id "$IMAGE" -u)" "1000"
exit "$fail"

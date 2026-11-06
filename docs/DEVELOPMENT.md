# Development

CI is the test runner. Push a branch, open a draft PR, and read the `test` job. Run anything locally only when CI cannot answer the question, and then inside Docker: nothing here installs on the host.

## The loop

1. Branch from the latest `main`.
2. Write the change and its tests together. Every change ships with tests, and coverage stays at 100% of lines and branches. Record: [0018](architectural-decision-records/0018-full-coverage.md).
3. Commit early, push, and open a draft PR. The `test` job runs on every push to it. Title the PR `type(scope): summary`, because the title picks the release version and the `PR Title` check fails anything else ([CICD.md](CICD.md#conventions)).
4. Read the result:

   ```sh
   gh pr checks <number>
   gh run view <run-id> --log
   ```

   The coverage table is at the end of the `test` job's log, with the missing lines and branches for any file under 100%.
5. Update the docs the change makes untrue, and add a decision record for any decision, in the same PR ([architectural-decision-records/README.md](architectural-decision-records/README.md)).
6. Mark the PR ready. Resolve every conversation on it, because main will not merge with one open. After TJ approves, it is squash-merged, which releases it, and [CICD.md](CICD.md) takes over.

## Running the checks in Docker

Only when CI is not enough, for example to iterate on one failing test. Every check CI runs is a `make` target, and each one runs in Docker. Record: [0029](architectural-decision-records/0029-repo-files-and-make-targets.md)

| Target | What it runs |
|---|---|
| `make test` | The suite under coverage, failing below 100%, as the `test` job does |
| `make test-one MODULE=tests.test_build` | One module, verbose |
| `make lint` | ruff under `ruff.toml`, as the `Lint` job does |
| `make lint-docker` | hadolint on the `Dockerfile`, as the `Docker Build` job does first |
| `make build` | `docker build -t hevy-trainer-sync:dev .`, with `APP_COMMIT` set to the checked-out commit |
| `make lock` | Rewrites `requirements.txt` and `requirements-dev.txt`, with hashes, from their `.in` files. Run it after changing a pin, and commit both |
| `make scan` | Builds, then scans the build with Trivy under `trivy.yaml`, failing on a fixable Critical or High, as the release does |

The same suite without make:

```sh
docker run --rm -v "$PWD":/repo -w /repo python:3.13-slim sh -c '
  pip install -q -r requirements-dev.txt &&
  PYTHONPATH=src python -m coverage run -m unittest discover -s tests &&
  python -m coverage report'
```

## Writing tests

- `unittest` and `unittest.mock` only. No pytest, no new runtime dependencies.
- No network and no database. Patch `urllib.request.urlopen` to test `http.py`, patch each client module's `request` to test the clients, and fake `psycopg` for `db.py`.
- Assert behaviour: the request that was sent, the payload, the exit code, the log line when the log line is the behaviour. A test that only executes a line does not count.
- The only coverage exclusion is the `if __name__ == "__main__":` idiom. Anything else that seems untestable is a design problem to raise, not a pragma to add.
- Fixtures cut from real responses lose their tokens, ids and personal data first. The repo is public.

## Building the image

CI builds and pushes every image (record [0005](architectural-decision-records/0005-images-from-ci-prs-only.md)). To check that the Dockerfile builds without pushing anything, run `make build`, and `make scan` to put it through the release's scan.

## Running the tool

Exercise it through tests, and run it for real from the cluster ([USAGE.md](USAGE.md#running-it-by-hand)). Every run, `--dry-run` included, refreshes the Hevy session and rotates its refresh token, so never point a local run at the cluster's session file (record [0006](architectural-decision-records/0006-session-on-a-volume.md)). If a local run against the real account is ever needed, do it in the image with a fresh cookie of its own and a throwaway state file:

```sh
docker run --rm -e HEVY_API_KEY -e HEVY_SESSION -e HEVY_STATE_FILE=/tmp/session.json hevy-trainer-sync:dev --dry-run
```

Refreshing that cookie may sign the browser tab it came from out of hevy.com. Whether it affects other Hevy sessions is not known.

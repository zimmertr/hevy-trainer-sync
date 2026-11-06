# Every check CI runs, runnable the same way here. Each target runs in Docker;
# nothing installs on the workstation (docs/DEVELOPMENT.md). Record 0029.

PYTHON_IMAGE := python:3.13-slim
TRIVY_IMAGE  := aquasec/trivy:0.68.1
# The same versions pr.yml runs; move them together.
RUFF_IMAGE   := ghcr.io/astral-sh/ruff:0.16.0
HADOLINT     := hadolint/hadolint:v2.12.0
IMAGE        := hevy-trainer-sync:dev
RUN          := docker run --rm -v "$(CURDIR)":/repo -w /repo

.PHONY: test test-one lint lint-docker build scan lock

# The suite under coverage, with its line and branch report, as the test job
# runs it.
test:
	$(RUN) $(PYTHON_IMAGE) sh -c 'pip install -q --require-hashes -r requirements-dev.txt && \
	  PYTHONPATH=src python -m coverage run -m unittest discover -s tests && \
	  python -m coverage report'

# One module, for iterating on a failure: make test-one MODULE=tests.test_build
test-one:
	$(RUN) $(PYTHON_IMAGE) sh -c 'pip install -q --require-hashes -r requirements-dev.txt && \
	  PYTHONPATH=src python -m unittest $(MODULE) -v'

# The Lint job: ruff under ruff.toml.
lint:
	$(RUN) $(RUFF_IMAGE) check .

# The Docker Build job's first step.
lint-docker:
	docker run --rm -i $(HADOLINT) < Dockerfile

build:
	docker build --build-arg APP_COMMIT=$$(git rev-parse HEAD) -t $(IMAGE) .

# The release scan's rules (trivy.yaml, fixable Critical and High only) against
# a local build. Exits non-zero when it finds one, as the release does.
scan: build
	$(RUN) -v /var/run/docker.sock:/var/run/docker.sock $(TRIVY_IMAGE) image \
	  --config trivy.yaml --ignore-unfixed --severity CRITICAL,HIGH --exit-code 1 $(IMAGE)

# Not a check: rewrites the two hashed locks from requirements.in and
# requirements-dev.in, on the image's own Python. pip-compile keeps every pin
# it already has unless asked; add --upgrade-package NAME to move one. The
# pip-tools and pip versions are Bluebird's, the pair Dependabot also runs.
lock:
	$(RUN) $(PYTHON_IMAGE) sh -c "pip install -q --root-user-action=ignore 'pip<26' pip-tools==7.5.3 && \
	  pip-compile -q --generate-hashes --allow-unsafe --strip-extras --output-file=requirements.txt requirements.in && \
	  pip-compile -q --generate-hashes --allow-unsafe --strip-extras --output-file=requirements-dev.txt requirements-dev.in"

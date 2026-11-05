# Every check CI runs, runnable the same way here. Each target runs in Docker;
# nothing installs on the workstation (docs/DEVELOPMENT.md). Record 0029.

PYTHON_IMAGE := python:3.13-slim
TRIVY_IMAGE  := aquasec/trivy:0.68.1
IMAGE        := hevy-trainer-sync:dev
RUN          := docker run --rm -v "$(CURDIR)":/repo -w /repo

.PHONY: test test-one build scan

# The suite under coverage, failing below 100% of lines and branches, as the
# test job does.
test:
	$(RUN) $(PYTHON_IMAGE) sh -c 'pip install -q -r requirements-dev.txt && \
	  PYTHONPATH=src python -m coverage run -m unittest discover -s tests && \
	  python -m coverage report'

# One module, for iterating on a failure: make test-one MODULE=tests.test_build
test-one:
	$(RUN) $(PYTHON_IMAGE) sh -c 'pip install -q -r requirements-dev.txt && \
	  PYTHONPATH=src python -m unittest $(MODULE) -v'

build:
	docker build -t $(IMAGE) .

# The release scan's rules (trivy.yaml, fixable Critical and High only) against
# a local build. Exits non-zero when it finds one, as the release does.
scan: build
	$(RUN) -v /var/run/docker.sock:/var/run/docker.sock $(TRIVY_IMAGE) image \
	  --config trivy.yaml --ignore-unfixed --severity CRITICAL,HIGH --exit-code 1 $(IMAGE)

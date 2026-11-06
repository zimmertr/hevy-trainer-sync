# Tag and digest, so a rebuild of 3.13-slim upstream reaches this image as a
# Dependabot PR rather than silently at the next build. Decision record 0025.
FROM python:3.13-slim@sha256:09a17cad02668ae61ece136b4fd36ac3849e14f670ebedb637ea3e15580525bc

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
# The hashed lock, installed with every hash checked. Decision record 0036.
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY src/hevy_trainer_sync /app/hevy_trainer_sync

# The base image lags Debian's security fixes, and the release scan refuses a
# fixable High (apt 3.0.3, CVE-2026-109518, 2026-11-05). Decision record 0022.
# The upgrade sits after APP_COMMIT, which changes on every build: BuildKit
# keys a RUN on every build argument in scope, so a layer cache, if one is
# ever added, can't freeze this layer and keep a fixed CVE out. Only USER and
# ENTRYPOINT follow it, so rerunning it repeats no other work. Record 0034.
ARG APP_COMMIT=unknown
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

USER 1000:1000

ENTRYPOINT ["python3", "-m", "hevy_trainer_sync"]

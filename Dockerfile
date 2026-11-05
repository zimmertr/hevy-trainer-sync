FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# The base image lags Debian's security fixes, and the release scan refuses a
# fixable High (apt 3.0.3, CVE-2026-109518, 2026-11-05). CI builds without a
# layer cache, so every release takes Debian's packages as they stand that day.
# Decision record 0022.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/hevy_trainer_sync /app/hevy_trainer_sync

USER 1000:1000

ENTRYPOINT ["python3", "-m", "hevy_trainer_sync"]

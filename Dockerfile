FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY src/hevy_trainer_sync /app/hevy_trainer_sync

# No dependencies beyond the standard library, so no pip step.
USER 1000:1000

ENTRYPOINT ["python3", "-m", "hevy_trainer_sync"]

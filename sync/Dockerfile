# syntax=docker/dockerfile:1
# garmin-grafana sync, pinned to a commit, with two patches:
#  - garminconnect 0.3.7 -> 0.3.20 (Garmin's 2026 login changes)
#  - fetch exercise sets for HIIT activities too, not only strength
FROM ghcr.io/astral-sh/uv:0.6.17-python3.13-bookworm-slim AS build
ARG GG_COMMIT=d6bd12b403d68084a2094fd16586635e3b624c94
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN git init -q . \
 && git remote add origin https://github.com/arpanghosh8453/garmin-grafana.git \
 && git fetch -q --depth 1 origin "$GG_COMMIT" \
 && git checkout -q FETCH_HEAD
RUN sed -i 's/"garminconnect==0.3.7"/"garminconnect==0.3.20"/' pyproject.toml \
 && grep -q '"garminconnect==0.3.20"' pyproject.toml \
 && sed -i "s/if 'strength' in activity_type_key.lower()/if ('strength' in activity_type_key.lower() or 'hiit' in activity_type_key.lower())/" src/garmin_grafana/garmin_fetch.py \
 && grep -q "or 'hiit' in activity_type_key.lower())" src/garmin_grafana/garmin_fetch.py \
 && uv lock \
 && uv sync --locked

FROM python:3.13-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN groupadd --gid 1000 appuser && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser
COPY --chown=appuser:appuser --from=build /app/.venv /app/.venv
COPY --chown=appuser:appuser --from=build /app/src /app/
USER appuser
CMD ["python", "garmin_grafana/garmin_fetch.py"]

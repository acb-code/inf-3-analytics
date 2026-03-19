FROM python:3.11-slim AS base

# ── Install uv ──────────────────────────────────────────────────────
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /uvx /usr/local/bin/

# ── Build stage: install Python deps ────────────────────────────────
FROM base AS build
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/
RUN uv sync --frozen --no-dev --extra cloud --extra api --extra cv

# ── Runtime ─────────────────────────────────────────────────────────
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8001
CMD ["uvicorn", "inf3_analytics.api.app:app", "--host", "0.0.0.0", "--port", "8001"]

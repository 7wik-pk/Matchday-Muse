# syntax=docker/dockerfile:1

# Built from the repo root, since the runtime image includes the frontend.
FROM docker.io/library/python:3.14.8-slim-trixie AS base
COPY --from=ghcr.io/astral-sh/uv:0.13.3 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

# For compose: app/ is mounted read-only over the copy, and uvicorn reloads on
# changes.
FROM base AS dev
COPY backend/app ./app
EXPOSE 8000
CMD ["uvicorn", "--factory", "app.main:build", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "app"]

# The frontend's production bundle, which the runtime image serves at /.
FROM docker.io/library/node:24.22.0-alpine3.24 AS ui
ENV NG_CLI_ANALYTICS=false
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-fund --no-audit
COPY contracts/ws /app/contracts/ws
COPY frontend/ ./
RUN npx ng build

# The deployable image, and the default target: the backend serving the UI and
# /ws on one origin (compose.prod.yaml).
FROM base AS runtime
COPY backend/app ./app
COPY --from=ui /app/frontend/dist/matchday-muse/browser ./ui
ENV STATIC_DIR=/app/ui
RUN useradd --system --uid 10001 app
USER app
EXPOSE 8000
CMD ["uvicorn", "--factory", "app.main:build", "--host", "0.0.0.0", "--port", "8000"]

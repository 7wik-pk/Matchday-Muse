# syntax=docker/dockerfile:1

FROM docker.io/library/python:3.14.8-slim-trixie AS base
COPY --from=ghcr.io/astral-sh/uv:0.13.3 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

# For compose: app/ is mounted read-only over the copy, and uvicorn reloads on
# changes.
FROM base AS dev
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "--factory", "app.main:build", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "app"]

# The deployable image, and the default target. From Phase 1 it also serves
# the frontend's production bundle.
FROM base AS runtime
COPY app ./app
RUN useradd --system --uid 10001 app
USER app
EXPOSE 8000
CMD ["uvicorn", "--factory", "app.main:build", "--host", "0.0.0.0", "--port", "8000"]

# syntax=docker/dockerfile:1

# Built from the repo root, since the app imports contracts/ws/examples/.
FROM docker.io/library/node:24.22.0-alpine3.24 AS deps
ENV NG_CLI_ANALYTICS=false
WORKDIR /app/frontend
RUN chown node:node /app /app/frontend
USER node
COPY --chown=node:node frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/home/node/.npm,uid=1000,gid=1000 npm ci --no-fund --no-audit

# ng serve with hot reload; compose mounts src/ and contracts/ws/ over the copies.
FROM deps AS dev
COPY --chown=node:node contracts/ws /app/contracts/ws
COPY --chown=node:node frontend/ ./
EXPOSE 4200
CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--port", "4200"]

# The production bundle is built by backend/Dockerfile, whose runtime image serves it.

# syntax=docker/dockerfile:1

FROM docker.io/library/golang:1.27.3-alpine3.24 AS base
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
ENV MCP_TRANSPORT=http \
    MCP_HTTP_ADDR=:8081 \
    CACHE_DIR=/data/cache

# For compose: the source is mounted at /src, watch restarts the container on
# changes, and each start recompiles (incrementally, with the build cache on
# a volume).
FROM base AS dev
COPY . .
CMD ["sh", "-c", "go build -o /tmp/mcp-server ./cmd/server && exec /tmp/mcp-server"]

FROM base AS build
COPY . .
RUN --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/mcp-server ./cmd/server \
    && mkdir -p /out/data/cache

# The deployable image, and the default target: a static binary on
# distroless, with no shell, no package manager and a non-root user.
FROM gcr.io/distroless/static-debian13:nonroot AS runtime
COPY --from=build /out/mcp-server /mcp-server
# The cache volume mounts here; owning the directory lets a fresh named
# volume start out writable by the nonroot user.
COPY --from=build --chown=65532:65532 /out/data /data
ENV MCP_TRANSPORT=http \
    MCP_HTTP_ADDR=:8081 \
    CACHE_DIR=/data/cache
EXPOSE 8081
# The healthcheck lives in compose.yaml: Podman builds OCI images, which have
# no HEALTHCHECK.
ENTRYPOINT ["/mcp-server"]

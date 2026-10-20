# syntax=docker/dockerfile:1

# The MCP server over Streamable HTTP, as docker-compose and Cloud Run run it.
FROM docker.io/library/golang:1.27.3-alpine3.24 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/mcp-server ./cmd/server \
    && mkdir -p /out/data/cache

# Static binary on distroless: no shell, no package manager, a non-root user.
FROM gcr.io/distroless/static-debian13:nonroot
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

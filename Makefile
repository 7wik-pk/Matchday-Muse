.PHONY: test test-contracts test-mcp test-frontend gen dev down logs dev-mcp record-espn diagrams

test: test-contracts test-mcp test-frontend

# Podman when it is installed, otherwise Docker; override with COMPOSE=...
COMPOSE ?= $(if $(shell command -v podman 2>/dev/null),podman compose,docker compose)

contracts/node_modules: contracts/package-lock.json
	cd contracts && npm ci --no-fund --no-audit
	touch $@

frontend/node_modules: frontend/package-lock.json
	cd frontend && npm ci --no-fund --no-audit
	touch $@

# Compiles every schema, checks the scripted runs in contracts/ws/examples/,
# and fails if the generated TypeScript types are stale.
test-contracts: contracts/node_modules
	cd contracts && npm test --silent

# Go MCP server: formatting, vet, tests against recorded ESPN data (offline),
# and a check that contracts/mcp/ matches what the server advertises.
test-mcp:
	cd mcp-server && test -z "$$(gofmt -l .)" || { gofmt -l .; echo "gofmt needed"; exit 1; }
	cd mcp-server && go vet ./... && go test ./... && go run ./cmd/schemagen -check

# Angular unit and component tests, driven by the scripted runs.
test-frontend: frontend/node_modules
	cd frontend && npx ng test --watch=false

# Exports the MCP tool schemas to contracts/mcp/, then regenerates types from
# contracts/. Python joins when the backend exists.
gen: contracts/node_modules
	cd mcp-server && go run ./cmd/schemagen
	cd contracts && npm run gen --silent

# The stack in compose: the UI at http://localhost:4200 (scripted runs,
# ?mock=<script>&speed=<n>) and the MCP server at http://localhost:8081/mcp.
# Source changes sync or rebuild while it runs; Ctrl-C stops it.
dev: .env
	$(COMPOSE) up --build --watch

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

# A local .env with a fresh MCP token. Never overwrites an existing one.
.env:
	sed "s/^MCP_AUTH_TOKEN=$$/MCP_AUTH_TOKEN=$$(openssl rand -hex 32)/" .env.example > $@

# MCP Inspector's web UI on the server over stdio, using live ESPN data; no
# Docker needed.
dev-mcp:
	cd mcp-server && go build -o bin/mcp-server ./cmd/server
	npx -y @modelcontextprotocol/inspector@2.9.0 mcp-server/bin/mcp-server

# Re-records ESPN responses into mcp-server/testdata/ (needs the network).
# The tests expect the week of Mon 12 Oct 2026.
record-espn:
	cd mcp-server && go run ./cmd/record -league eng.1 -from $(or $(FROM),2026-10-12) -days 7

# Re-renders docs/diagrams/*.mmd to PNG. Needs a Chrome that Puppeteer can find.
diagrams:
	for f in docs/diagrams/*.mmd; do \
		npx -y @mermaid-js/mermaid-cli@11.4.2 -i $$f -o $${f%.mmd}.png -b white -s 2; \
	done

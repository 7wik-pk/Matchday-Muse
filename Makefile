.PHONY: test test-contracts test-mcp test-backend test-frontend gen brand freeze-mcp dev down logs images dev-mcp record-espn diagrams

test: test-contracts test-mcp test-backend test-frontend

UV ?= uv

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

# FastAPI backend: formatting, lint, strict types, tests (offline: MCP
# responses replayed from tests/fixtures/, plus the Go server over stdio for
# the tools that need no network), and a check that app/contracts/ is fresh.
test-backend:
	cd backend && $(UV) sync --frozen --quiet
	cd backend && $(UV) run ruff format --check --quiet . && $(UV) run ruff check --quiet .
	cd backend && $(UV) run mypy app tests scripts
	cd backend && $(UV) run pytest -q
	cd backend && $(UV) run python scripts/gen_contracts.py --check

# Angular unit and component tests, driven by the scripted runs.
test-frontend: frontend/node_modules
	cd frontend && npx ng test --watch=false

# Exports the MCP tool schemas to contracts/mcp/, then regenerates the
# TypeScript and Python types from contracts/.
gen: contracts/node_modules
	cd mcp-server && go run ./cmd/schemagen
	cd contracts && npm run gen --silent
	cd backend && $(UV) run python scripts/gen_contracts.py

# The stack in compose: the UI at http://localhost:4200 on the real backend
# (?mock=<script>&speed=<n> replays a scripted run instead), the backend at
# localhost:8000 and the MCP server at http://localhost:8081/mcp.
# Source changes sync or rebuild while it runs; Ctrl-C stops it.
dev: .env
	$(COMPOSE) up --build --watch

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

# The deployable images: the MCP server on distroless, and the frontend's
# production bundle (which the backend image will serve from Phase 1).
ENGINE ?= $(firstword $(COMPOSE))
images:
	$(ENGINE) build -t matchday-muse/mcp-server:latest mcp-server
	$(ENGINE) build -t matchday-muse/backend:latest backend
	$(ENGINE) build -t matchday-muse/frontend-build:latest --target build -f frontend/Dockerfile .

# A local .env with a fresh MCP token. Never overwrites an existing one.
.env:
	sed "s/^MCP_AUTH_TOKEN=$$/MCP_AUTH_TOKEN=$$(openssl rand -hex 32)/" .env.example > $@

# MCP Inspector's web UI on the server over stdio, using live ESPN data; no
# Docker needed.
dev-mcp:
	cd mcp-server && go build -o bin/mcp-server ./cmd/server
	npx -y @modelcontextprotocol/inspector@2.9.0 mcp-server/bin/mcp-server

# Redraws the logo from docs/brand/make_logo.py: the SVGs, the header's inline
# SVG, and the favicon and touch icon rasters (needs rsvg-convert and ImageMagick).
brand: frontend/node_modules
	python3 docs/brand/make_logo.py
	cd frontend && npx prettier --write --log-level warn src/app/brand/logo.html
	for s in 16 32 48; do rsvg-convert -w $$s -h $$s docs/brand/logo.svg -o /tmp/mm-favicon-$$s.png; done
	magick /tmp/mm-favicon-16.png /tmp/mm-favicon-32.png /tmp/mm-favicon-48.png frontend/public/favicon.ico
	rsvg-convert -w 180 -h 180 docs/brand/app-icon.svg -o frontend/public/apple-touch-icon.png
	rm -f /tmp/mm-favicon-*.png

# Re-records the backend's MCP fixtures through the real client and Go server
# (needs the network for ESPN).
freeze-mcp:
	cd mcp-server && go build -o bin/mcp-server ./cmd/server
	cd backend && $(UV) run python scripts/freeze_mcp.py ../mcp-server/bin/mcp-server

# Re-records ESPN responses into mcp-server/testdata/ (needs the network).
# The tests expect the week of Mon 12 Oct 2026.
record-espn:
	cd mcp-server && go run ./cmd/record -league eng.1 -from $(or $(FROM),2026-10-12) -days 7

# Re-renders docs/diagrams/*.mmd to PNG. Needs a Chrome that Puppeteer can find.
diagrams:
	for f in docs/diagrams/*.mmd; do \
		npx -y @mermaid-js/mermaid-cli@11.4.2 -i $$f -o $${f%.mmd}.png -b white -s 2; \
	done

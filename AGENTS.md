# AGENTS.md — Matchday Muse

Rules for every coding agent working in this repo.

## Before any task: REVIEW.md
If `REVIEW.md` at the repo root is not empty, stop before starting any new work. Tell the user it has items waiting, and ask them to review everything in it and clear the file first. Carry on only once it is empty. Answering questions about the items in it, or fixing what the review turns up, is fine.

## Read first
- docs/design.md (the design doc). Build only the current phase.
- contracts/ is the source of truth for every cross-service shape.

## Rules
1. Contracts first: edit contracts/ws or contracts/pipeline (or the Go structs, for MCP tools), run `make gen`, then code. Never hand-edit generated files: contracts/mcp/, frontend/src/app/contracts/, backend/app/contracts/.
2. Every external call (sports APIs, search, LLM) goes through an interface with a fixture/mock implementation.
3. Tests must pass offline: `make test` uses the fixture search provider, recorded ESPN and MCP data, and the mock LLM.
4. No secrets in code, logs, test fixtures or the database. BYO API keys are never persisted or logged.
5. Prompts live in backend/app/pipeline/prompts/*.vN.md; bump the version on any change.
6. The pipeline is a fixed state machine; do not add autonomous loops. Only pick_match calls tools, max 4 per run.
7. Every stage emits stage.update messages exactly as defined in contracts/ws/.
8. Never display output that failed a guardrail.
9. Go: standard library first, except HTTP: every outbound API call uses the go-resty client (`github.com/go-resty/resty/v2`). Table-driven tests, errors wrapped with context.
10. Python: type hints everywhere, Pydantic v2, ruff + strict mypy clean.
11. Angular: standalone components and signals; types imported from generated contracts.
12. compose.yaml must work on Podman and Docker: mount source read-only and use watch's `restart` action only (its `sync` and `rebuild` break on Podman); healthchecks go in compose.yaml.
13. LLM: only models in the registry (`backend/app/presets.py`) may run, and each needs a `REASONING_EFFORT` entry (a test enforces it). Import LiteLLM only through `app/llm/live.py`, which stops it loading `.env` files. Never log keys; scrub them from provider errors.
14. Guardrails: a new check, or a change to one, must still pass the 8 sample poems in `contracts/ws/examples/takes.json`; craft (rhyme, metre, where the result lands) is for evals, never a run-time check.
15. Keep CHANGELOG.md's Unreleased section and the design doc's decision log current as work lands.

## Commands
- make dev         # the stack in compose (Podman or Docker), with reload; make down to stop, make logs to follow
- make test        # contracts, Go, backend and frontend tests, offline
- make gen         # regenerate contracts/mcp/ and the TypeScript and Python types
- make dev-mcp     # MCP Inspector on the Go server over stdio
- make prod        # the production stack (compose.prod.yaml) on the server; make prod-down to stop
- ./deploy.sh      # on the server: pull, rebuild and restart the production stack (no make needed)
- make images      # the deployable images
- make freeze-mcp  # re-record the backend's MCP fixtures (needs the network)
- make record-espn # re-record the Go server's ESPN testdata (needs the network)

## Definition of done for any task
Tests added and passing offline, contracts unchanged or regenerated, README updated if behaviour changed.

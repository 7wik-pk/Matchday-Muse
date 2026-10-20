# Matchday Muse backend

FastAPI and the pipeline: the `/ws` socket the UI talks to, the ten stages, and the MCP client that reaches the Go server. The design is in [docs/design.md](../docs/design.md#python-backend-and-pipeline).

**Status:** every stage runs on real match data except the LLM calls. `MockLlm` (`app/llm/mock.py`) stands in for them: it picks by drama signals, and its "poem" is the moment's facts, one stanza each. The guardrail checks report as skipped. The LiteLLM stages and the guardrails are the next roadmap items.

## Run it

```sh
make dev                                        # from the repo root: the whole stack in compose
```

Or on the host, with the MCP server over stdio:

```sh
(cd ../mcp-server && go build -o bin/mcp-server ./cmd/server)
MCP_SERVER_COMMAND=../mcp-server/bin/mcp-server uv run uvicorn --factory app.main:build --reload
```

| Variable | Default | |
| --- | --- | --- |
| `MCP_SERVER_URL` | | Streamable HTTP endpoint, such as `http://mcp-server:8081/mcp`; needs `MCP_AUTH_TOKEN` |
| `MCP_SERVER_COMMAND` | | Or: launch the MCP server binary over stdio |
| `MCP_AUTH_TOKEN` | | The shared bearer token, at least 32 characters |
| `MOCK_LLM` | `true` | `false` arrives with the LiteLLM stages |
| `LOG_LEVEL` | `info` | |

## Layout

| Path | |
| --- | --- |
| `app/main.py` | The app factory: `/ws` and `/healthz` |
| `app/ws/session.py` | One socket: `session.hello`, at most one run at a time, cancel, retell of finished runs |
| `app/pipeline/run.py` | The stages, in order, and the result |
| `app/pipeline/ranges.py`, `signals.py` | `resolve_range`, and the drama signals `score_matches` computes |
| `app/llm/` | The LLM stages as one interface (`base.py`) and the mock |
| `app/sports.py` | Typed MCP tool calls over Streamable HTTP or stdio |
| `app/contracts/` | Generated from `contracts/` by `make gen`; do not edit |

## Tests

`make test-backend` (from the repo root) runs ruff, strict mypy, pytest and a check that `app/contracts/` is fresh, all offline. The protocol tests drive the socket as the UI does, validate every message against `contracts/ws/`, and compare the backend with the scripted runs the frontend mock replays. Sports data comes from `tests/fixtures/mcp/`, which `make freeze-mcp` re-records through the real client and Go server.

# Matchday Muse backend

FastAPI and the pipeline: the `/ws` socket the UI talks to, the ten stages, and the MCP client that reaches the Go server. The design is in [docs/design.md](../docs/design.md#python-backend-and-pipeline).

**Status:** every stage runs, on real match data and a real model through LiteLLM (`app/llm/live.py`), with the key from the UI's Your LLM drawer or the server's `LLM_API_KEY`. `MOCK_LLM=true` swaps in `MockLlm` (`app/llm/mock.py`) for tests and keyless runs. The guardrails (`app/guardrails/`) check every poem, rewrite a failing one once, and fail the run if it fails again; only moderation is still skipped.

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
| `MOCK_LLM` | `false` | `true` runs every LLM stage on the mock |
| `LLM_MODEL` | `gemini/gemini-flash-latest` | The model for runs where the browser sends no key |
| `LLM_API_KEY` | | The server's own key for those runs; leave unset to require one in the UI |
| `LLM_RUN_TOKEN_BUDGET` | `150000` | Tokens one run may spend |
| `ANALYSIS_CACHE_DIR` | unset (compose: a volume) | Development cache of the pick, moment and fact draft; a repeat run of a week makes only the poem and judge calls |
| `LOG_LEVEL` | `info` | |

## Layout

| Path | |
| --- | --- |
| `app/main.py` | The app factory: `/ws` and `/healthz` |
| `app/ws/session.py` | One socket: `session.hello`, at most one run at a time, cancel, retell of finished runs |
| `app/pipeline/run.py` | The stages, in order, and the result |
| `app/pipeline/ranges.py`, `signals.py` | `resolve_range`, and the drama signals `score_matches` computes |
| `app/guardrails/` | The output checks; `vocab.py` holds the nicknames, grounds and stock figures the name check accepts |
| `app/llm/` | The LLM stages as one interface (`base.py`), on LiteLLM (`live.py`) or the mock |
| `app/pipeline/prompts/` | Versioned prompts: one per LLM call, one per style preset |
| `app/sports.py` | Typed MCP tool calls over Streamable HTTP or stdio |
| `app/contracts/` | Generated from `contracts/` by `make gen`; do not edit |

## Tests

`make test-backend` (from the repo root) runs ruff, strict mypy, pytest and a check that `app/contracts/` is fresh, all offline. The protocol tests drive the socket as the UI does, validate every message against `contracts/ws/`, and compare the backend with the scripted runs the frontend mock replays. Sports data comes from `tests/fixtures/mcp/`, which `make freeze-mcp` re-records through the real client and Go server. The guardrail checks are tested against the 8 sample poems (no false alarms) and a failing poem per check, plus the rewrite and fail-twice paths through a whole run. The LiteLLM path is tested with a scripted stand-in for `litellm.acompletion`: the search loop and its cap, parsing and the retry, provider errors, the token budget, and a whole run through the socket.

# Matchday Muse MCP server

A thin, deterministic data layer in Go: it fetches, normalises and caches sports data and web search results, and never calls an LLM. Built on the official SDK, `github.com/modelcontextprotocol/go-sdk`. The design is in [docs/design.md](../docs/design.md#go-mcp-server).

| Tool | What it returns |
| --- | --- |
| `list_competitions` | The sports and leagues served: Premier League football (`eng.1`) from ESPN for now |
| `find_matches` | Completed matches kicking off in `[from, to)`, at most 32 days, with final scores and a one-line recap |
| `get_match_events` | One match's timeline (goals, cards, substitutions, VAR reviews, shots, fouls), team stats and the pages to cite |
| `search_coverage` | Web coverage for a query; offline `fixture` provider only until Phase 1 |

Each tool's schemas are generated from the Go types into [contracts/mcp/](../contracts/mcp/) by `make gen`.

## Run it

```sh
make dev                           # from the repo root: docker compose, HTTP on localhost:8081
make dev-mcp                       # MCP Inspector's web UI over stdio, from the repo root
go run ./cmd/server                # stdio, for any MCP client
```

In compose the server listens at `http://localhost:8081/mcp` and wants `Authorization: Bearer <MCP_AUTH_TOKEN from .env>`. To point Inspector at it, choose the Streamable HTTP transport, that URL, and the header. `GET /healthz` needs no token.

In Inspector, pass `match_id` as a string. Its CLI mode turns a bare `401879262` into a number, which the schema rejects, so quote it: `'match_id="401879262"'`.

To add it to Claude Desktop or another client, build it (`go build -o bin/mcp-server ./cmd/server`) and give the client the binary's absolute path as the command. The search corpus is embedded, so the working directory does not matter.

## Configuration

| Variable | Default | |
| --- | --- | --- |
| `SEARCH_PROVIDER` | `fixture` | `exa` and `tavily` arrive in Phase 1 |
| `SEARCH_FIXTURE_DIR` | embedded `testdata/search/` | Directory of `*.json` arrays of search results |
| `CACHE_DIR` | user cache dir `/matchday-muse/mcp-server` | Raw ESPN responses |
| `ENABLED_SPORTS` | `football` | |
| `MCP_TRANSPORT` | `stdio` (`http` in the image) | `http` serves `/mcp` and `/healthz` |
| `MCP_HTTP_ADDR` | `:8081` | |
| `MCP_AUTH_TOKEN` | | Required for `http`; at least 32 characters |
| `LOG_LEVEL` | `info` | `debug` logs every ESPN request; logs go to stderr |

## Tests and testdata

`go test ./...` runs offline. The ESPN adapter is tested against `testdata/espn/`, the Premier League week of Mon 12 Oct 2026, served by a local HTTP server that returns 404 for anything not recorded.

`make record-espn` (from the repo root) re-records that week through the adapter, trimming each response to the fields the adapter reads. It also writes `testdata/search/`, the week's match-report headlines and one-line descriptions, which is the fixture provider's default corpus. If you add a field to the ESPN wire types in `internal/sports/espn/wire.go`, re-record.

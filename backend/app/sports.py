"""The pipeline's view of the MCP server: typed calls over one client session.

The tool input and output models are generated from contracts/mcp/, which the
Go server exports from the types it advertises.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Protocol

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client
from pydantic import BaseModel

from app.config import Settings
from app.contracts.mcp.find_matches_output import FindMatchesOutput, Match
from app.contracts.mcp.get_match_events_output import GetMatchEventsOutput
from app.contracts.mcp.list_competitions_output import Competition, ListCompetitionsOutput
from app.contracts.mcp.search_coverage_output import SearchCoverageOutput

type Timeline = GetMatchEventsOutput


class ToolError(Exception):
    """A tool call the server answered with an error, or that failed in transit."""

    def __init__(self, tool: str, message: str) -> None:
        super().__init__(f"{tool}: {message}")
        self.tool = tool


class SportsData(Protocol):
    async def list_competitions(self) -> list[Competition]: ...

    async def find_matches(self, sport: str, league: str, start: datetime, end: datetime) -> list[Match]: ...

    async def get_match_events(self, sport: str, league: str, match_id: str) -> Timeline: ...

    async def search_coverage(self, query: str, max_results: int = 5) -> SearchCoverageOutput: ...


def rfc3339(t: datetime) -> str:
    return t.astimezone(UTC).isoformat().replace("+00:00", "Z")


class McpSportsData:
    def __init__(self, client: Client) -> None:
        self.client = client

    async def _call[M: BaseModel](self, tool: str, args: dict[str, Any], out: type[M]) -> M:
        try:
            result = await self.client.call_tool(tool, args)
        except Exception as e:  # transport failures
            raise ToolError(tool, f"call failed: {e}") from e
        if result.is_error:
            text = " ".join(getattr(c, "text", "") for c in result.content)
            raise ToolError(tool, text or "the server returned an error")
        return out.model_validate(result.structured_content)

    async def list_competitions(self) -> list[Competition]:
        return (await self._call("list_competitions", {}, ListCompetitionsOutput)).competitions

    async def find_matches(self, sport: str, league: str, start: datetime, end: datetime) -> list[Match]:
        args = {"sport": sport, "league": league, "from": rfc3339(start), "to": rfc3339(end)}
        return (await self._call("find_matches", args, FindMatchesOutput)).matches

    async def get_match_events(self, sport: str, league: str, match_id: str) -> Timeline:
        args = {"sport": sport, "league": league, "match_id": match_id}
        return await self._call("get_match_events", args, GetMatchEventsOutput)

    async def search_coverage(self, query: str, max_results: int = 5) -> SearchCoverageOutput:
        args = {"query": query, "max_results": max_results}
        return await self._call("search_coverage", args, SearchCoverageOutput)


@asynccontextmanager
async def connect(settings: Settings) -> AsyncIterator[SportsData]:
    """One MCP session, over Streamable HTTP or stdio as configured."""
    if settings.mcp_server_url:
        token = settings.mcp_auth_token.get_secret_value() if settings.mcp_auth_token else ""
        http = create_mcp_http_client(headers={"Authorization": f"Bearer {token}"})
        async with http, Client(streamable_http_client(settings.mcp_server_url, http_client=http)) as client:
            yield McpSportsData(client)
    else:
        assert settings.mcp_server_command
        params = StdioServerParameters(command=settings.mcp_server_command)
        async with Client(params) as client:
            yield McpSportsData(client)

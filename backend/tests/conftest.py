"""Shared fixtures: sports data replayed from tests/fixtures/mcp/, the app on
top of it, and a validator for server messages against contracts/ws/."""

import os

# As in app/llm/live.py: LiteLLM must not load .env or fetch prices on import.
os.environ.setdefault("LITELLM_MODE", "PRODUCTION")
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import asyncio
import json
import threading
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from starlette.testclient import WebSocketTestSession

from app.contracts.mcp.find_matches_output import Match
from app.contracts.mcp.get_match_events_output import GetMatchEventsOutput
from app.contracts.mcp.list_competitions_output import Competition
from app.contracts.mcp.search_coverage_output import SearchCoverageOutput
from app.main import create_app
from app.sports import SportsData, Timeline

FIXTURES = Path(__file__).parent / "fixtures" / "mcp"
CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"
EXAMPLES = CONTRACTS / "ws" / "examples"

type Message = dict[str, Any]


class FixtureSports:
    """The MCP tools, answered from recordings with the server's semantics:
    find_matches keeps completed matches kicking off in [start, end)."""

    def __init__(self) -> None:
        self.matches = [Match.model_validate(m) for m in json.loads((FIXTURES / "matches.json").read_text())]
        self.searches = json.loads((FIXTURES / "search.json").read_text())
        self.calls: list[str] = []

    async def list_competitions(self) -> list[Competition]:
        data = json.loads((FIXTURES / "competitions.json").read_text())
        return [Competition.model_validate(c) for c in data]

    async def find_matches(self, sport: str, league: str, start: datetime, end: datetime) -> list[Match]:
        self.calls.append("find_matches")
        return [m for m in self.matches if start <= datetime.fromisoformat(m.kickoff) < end]

    async def get_match_events(self, sport: str, league: str, match_id: str) -> Timeline:
        self.calls.append("get_match_events")
        return GetMatchEventsOutput.model_validate_json((FIXTURES / "events" / f"{match_id}.json").read_text())

    async def search_coverage(self, query: str, max_results: int = 5) -> SearchCoverageOutput:
        self.calls.append("search_coverage")
        empty = {"provider": "fixture", "results": []}
        return SearchCoverageOutput.model_validate(self.searches.get(query, empty))


def factory(sports: SportsData) -> Callable[[], Any]:
    @asynccontextmanager
    async def connect() -> AsyncIterator[SportsData]:
        yield sports

    return connect


@pytest.fixture
def sports() -> FixtureSports:
    return FixtureSports()


@pytest.fixture
def client(sports: FixtureSports) -> Iterator[TestClient]:
    with TestClient(create_app(factory(sports))) as c:
        yield c


def schema_validator() -> Draft202012Validator:
    resources = []
    for sub in ("ws", "pipeline"):
        for f in (CONTRACTS / sub).glob("*.json"):
            resources.append((f.as_uri(), Resource.from_contents(json.loads(f.read_text()))))
    registry: Registry = Registry().with_resources(resources)
    root = CONTRACTS / "ws" / "server-message.json"
    return Draft202012Validator({"$ref": root.as_uri()}, registry=registry, format_checker=FormatChecker())


SERVER_MESSAGE = schema_validator()


def check(message: Message) -> Message:
    """Fails the test unless the message is a valid ServerMessage per contracts/ws/."""
    errors = sorted(SERVER_MESSAGE.iter_errors(message), key=lambda e: e.path)
    assert not errors, f"{message['type']} breaks the contract: {errors[0].message} at {list(errors[0].path)}"
    return message


def hello(ws: WebSocketTestSession, timezone: str = "Europe/London") -> Message:
    ws.send_json(
        {"v": 1, "type": "session.hello", "runId": None, "payload": {"sessionToken": None, "timezone": timezone}}
    )
    return check(ws.receive_json())


def start_payload(**changes: Any) -> Message:
    payload: Message = {
        "sport": "football",
        "league": "eng.1",
        "range": {"granularity": "week", "anchor": "2026-10-12"},
        "style": "ballad",
        "output": "text",
        "llm": {"mode": "house"},
    }
    payload.update(changes)
    return payload


def until_end(ws: WebSocketTestSession) -> list[Message]:
    """Every message of one run, through run.result or run.error."""
    out = []
    while True:
        m = check(ws.receive_json())
        out.append(m)
        if m["type"] in ("run.result", "run.error"):
            return out


def example(name: str) -> Message:
    data: Message = json.loads((EXAMPLES / f"{name}.json").read_text())
    return data


def example_messages(name: str) -> list[Message]:
    return [step["send"] for step in example(name)["steps"] if "send" in step]


class Gate:
    """Holds a sports call until the test thread releases it, so a test can act
    mid-run. TestClient runs the app on another thread, hence threading.Event."""

    def __init__(self) -> None:
        self.event = threading.Event()

    def release(self) -> None:
        self.event.set()

    async def wait(self) -> None:
        while not self.event.is_set():
            await asyncio.sleep(0.01)

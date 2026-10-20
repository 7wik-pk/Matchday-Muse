"""The FastAPI app: the /ws socket the UI talks to, and /healthz.

uv run uvicorn --factory app.main:build --reload   # needs MCP_SERVER_URL or MCP_SERVER_COMMAND
"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from fastapi import FastAPI, WebSocket

from app.config import Settings, get_settings
from app.llm.base import Llm
from app.llm.mock import MockLlm
from app.sports import SportsData, connect
from app.ws.session import Competitions, Session


def create_app(
    sports: Callable[[], AbstractAsyncContextManager[SportsData]],
    llm: Callable[[], Llm] = MockLlm,
) -> FastAPI:
    """The app, given how to reach sports data and which LLM to use. Tests pass fixtures."""
    app = FastAPI(title="Matchday Muse", docs_url=None, redoc_url=None, openapi_url=None)
    competitions = Competitions(sports)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        await Session(websocket, sports, competitions, llm).serve()

    return app


def from_settings(settings: Settings) -> FastAPI:
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return create_app(lambda: connect(settings))


def build() -> FastAPI:
    """The app from the environment, for uvicorn --factory."""
    return from_settings(get_settings())

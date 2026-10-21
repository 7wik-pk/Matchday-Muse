"""The FastAPI app: the /ws socket the UI talks to, and /healthz.

uv run uvicorn --factory app.main:build --reload   # needs MCP_SERVER_URL or MCP_SERVER_COMMAND
"""

import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from fastapi import FastAPI, WebSocket

from app.config import Settings, get_settings
from app.contracts.ws.client_message import ByokLlm, LlmChoice
from app.llm.base import Llm, LlmFailure
from app.llm.mock import MockLlm
from app.presets import MODELS_BY_ID, REASONING_EFFORT
from app.sports import SportsData, connect
from app.ws.session import Competitions, Session


def create_app(
    sports: Callable[[], AbstractAsyncContextManager[SportsData]],
    llm: Callable[[LlmChoice], Llm] = lambda _choice: MockLlm(),
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


def llm_factory(settings: Settings) -> Callable[[LlmChoice], Llm]:
    """Each run's LLM: the user's own key and model, or the server's
    development key for llm.mode "house"; MockLlm when MOCK_LLM is set."""

    def make(choice: LlmChoice) -> Llm:
        if settings.mock_llm:
            return MockLlm()
        from app.llm.analysis_cache import AnalysisCache
        from app.llm.live import LiteLlm  # LiteLLM is slow to import; mock runs never need it

        budget = settings.llm_run_token_budget
        cache = AnalysisCache(settings.analysis_cache_dir) if settings.analysis_cache_dir else None
        if isinstance(choice, ByokLlm):
            known = MODELS_BY_ID.get(choice.model)
            if known is None or known.provider != choice.provider:
                raise LlmFailure("bad_request", f"{choice.model} is not one of the offered models.", retryable=False)
            return LiteLlm(
                choice.model,
                choice.api_key,
                budget=budget,
                reasoning_effort=REASONING_EFFORT.get(choice.model),
                analysis_cache=cache,
            )
        if settings.llm_api_key is None:
            raise LlmFailure(
                "provider_error",
                "No LLM key: add yours in Your LLM to run the pipeline.",
                retryable=False,
            )
        return LiteLlm(
            settings.llm_model,
            settings.llm_api_key.get_secret_value(),
            budget=budget,
            reasoning_effort=REASONING_EFFORT.get(settings.llm_model),
            analysis_cache=cache,
        )

    return make


def from_settings(settings: Settings) -> FastAPI:
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return create_app(lambda: connect(settings), llm_factory(settings))


def build() -> FastAPI:
    """The app from the environment, for uvicorn --factory."""
    return from_settings(get_settings())

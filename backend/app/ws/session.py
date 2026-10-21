"""One browser tab's socket: the session handshake, at most one run at a time,
and the finished runs it can retell.

A run's messages carry its runId and a seq that starts at 1; session-level
messages (session.ready, and errors for messages that never started a run)
carry runId null and seq 0. The BYO key in run.start is held only by the
run's task and is never logged or echoed.
"""

import asyncio
import contextlib
import logging
import secrets
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.contracts.mcp.list_competitions_output import Competition
from app.contracts.ws.client_message import (
    ClientMessage,
    LlmChoice,
    PromptAnswer,
    RunCancel,
    RunRetell,
    RunRetellPayload,
    RunStart,
    RunStartPayload,
    SessionHello,
)
from app.contracts.ws.common import StageId
from app.contracts.ws.server_message import Competition as CompetitionInfo
from app.contracts.ws.server_message import (
    RunAccepted,
    RunAcceptedPayload,
    RunError,
    RunErrorPayload,
    RunResult,
    RunResultPayload,
    SessionReady,
    SessionReadyPayload,
    StageUpdate,
    StageUpdatePayload,
)
from app.llm.base import Llm, LlmFailure
from app.pipeline.run import (
    RETELL_STAGES,
    STAGE_LABELS,
    RunFailure,
    Stages,
    Story,
    run_full,
    run_retell,
    stage_infos,
)
from app.presets import MODELS, SPORT_LABELS, STYLES
from app.sports import SportsData

log = logging.getLogger(__name__)

CLIENT_MESSAGE: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)

type SportsFactory = Callable[[], AbstractAsyncContextManager[SportsData]]
type RunBody = Callable[[ActiveRun, Stages], Awaitable[tuple[RunResultPayload, Story]]]


def now() -> datetime:
    return datetime.now(UTC)


def wire(message: BaseModel) -> dict[str, Any]:
    return message.model_dump(mode="json", by_alias=True)


def short_errors(e: ValidationError) -> list[str]:
    return [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()[:5]]


class Competitions:
    """list_competitions, fetched once per process."""

    def __init__(self, sports: SportsFactory) -> None:
        self.sports = sports
        self.cached: list[Competition] | None = None
        self.lock = asyncio.Lock()

    async def get(self) -> list[Competition]:
        async with self.lock:
            if self.cached is None:
                async with self.sports() as s:
                    self.cached = await s.list_competitions()
            return self.cached


class ActiveRun:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.seq = 0
        self.cancelled = asyncio.Event()
        self.task: asyncio.Task[None] | None = None

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq


class Session:
    def __init__(
        self,
        ws: WebSocket,
        sports: SportsFactory,
        competitions: Competitions,
        llm: Callable[[LlmChoice], Llm],
    ) -> None:
        self.ws = ws
        self.sports = sports
        self.competitions = competitions
        self.new_llm = llm
        self.timezone: str | None = None
        self.active: ActiveRun | None = None
        self.stories: dict[str, Story] = {}
        self.send_lock = asyncio.Lock()

    async def serve(self) -> None:
        try:
            while True:
                await self.handle(await self.ws.receive_text())
        except WebSocketDisconnect:
            pass
        finally:
            # A dropped socket cancels its run (Phases 0 and 1).
            if self.active and self.active.task:
                self.active.task.cancel()

    async def send(self, message: BaseModel) -> None:
        async with self.send_lock:
            await self.ws.send_json(wire(message))

    async def session_error(
        self, code: str, message: str, reasons: list[str] | None = None, *, retryable: bool = False
    ) -> None:
        await self.send(
            RunError(
                v=1,
                type="run.error",
                run_id=None,
                seq=0,
                ts=now(),
                payload=RunErrorPayload(
                    code=code,
                    message=message,
                    retryable=retryable,
                    stage=None,
                    reasons=reasons or [],
                    guardrails=None,
                    suggestion=None,
                ),
            )
        )

    async def handle(self, raw: str) -> None:
        try:
            message = CLIENT_MESSAGE.validate_json(raw)
        except ValidationError as e:
            await self.session_error("bad_message", "That message was not understood.", short_errors(e))
            return
        match message:
            case SessionHello():
                await self.hello(message)
            case _ if self.timezone is None:
                await self.session_error("bad_request", "Send session.hello first.")
            case RunStart():
                await self.start(message.payload)
            case RunRetell():
                await self.retell(message.payload)
            case RunCancel():
                if self.active and self.active.run_id == message.run_id:
                    self.active.cancelled.set()
            case PromptAnswer():
                # Prompts come with the real LLM stages (quota handling).
                await self.session_error("bad_request", "There is no open prompt.")

    async def hello(self, message: SessionHello) -> None:
        self.timezone = message.payload.timezone
        try:
            comps = await self.competitions.get()
        except Exception:
            log.exception("list_competitions failed")
            # The client reconnects with backoff and says hello again.
            await self.ws.close(code=1011, reason="sports data unavailable")
            return
        await self.send(
            SessionReady(
                v=1,
                type="session.ready",
                run_id=None,
                seq=0,
                ts=now(),
                payload=SessionReadyPayload(
                    free_runs_left=None,
                    competitions=[
                        CompetitionInfo(
                            sport=c.sport,
                            sport_label=SPORT_LABELS.get(c.sport, c.sport.capitalize()),
                            league=c.league,
                            league_label=c.name,
                            coverage=c.coverage,
                        )
                        for c in comps
                    ],
                    styles=STYLES,
                    models=MODELS,
                ),
            )
        )

    def busy(self) -> bool:
        return self.active is not None

    async def start(self, payload: RunStartPayload) -> None:
        if self.busy():
            await self.session_error("bad_request", "A run is already in progress.")
            return
        log.info(
            "run.start sport=%s league=%s range=%s/%s style=%s llm=%s",
            payload.sport,
            payload.league,
            payload.range.granularity,
            payload.range.anchor,
            payload.style,
            payload.llm.mode,
        )
        if llm := await self.make_llm(payload.llm):
            self.launch(lambda run, stages: self.full(payload, run, stages, llm), list(STAGE_LABELS), llm)

    async def retell(self, payload: RunRetellPayload) -> None:
        if self.busy():
            await self.session_error("bad_request", "A run is already in progress.")
            return
        story = self.stories.get(payload.from_run_id)
        if story is None:
            await self.send(
                RunError(
                    v=1,
                    type="run.error",
                    run_id=None,
                    seq=0,
                    ts=now(),
                    payload=RunErrorPayload(
                        code="retell_unavailable",
                        message="That run is no longer available to retell. Generate a new one.",
                        retryable=False,
                        stage=None,
                        reasons=[],
                        guardrails=None,
                        suggestion=None,
                    ),
                )
            )
            return
        log.info("run.retell from=%s style=%s llm=%s", payload.from_run_id, payload.style, payload.llm.mode)

        if llm := await self.make_llm(payload.llm):

            async def body(run: ActiveRun, stages: Stages) -> tuple[RunResultPayload, Story]:
                return await run_retell(payload, story, llm, stages), story

            self.launch(body, RETELL_STAGES, llm)

    async def make_llm(self, choice: LlmChoice) -> Llm | None:
        """The run's LLM, or None after telling the client why there is none."""
        try:
            return self.new_llm(choice)
        except LlmFailure as e:
            await self.session_error(e.code, e.message, e.reasons, retryable=e.retryable)
            return None

    async def full(
        self, payload: RunStartPayload, run: ActiveRun, stages: Stages, llm: Llm
    ) -> tuple[RunResultPayload, Story]:
        assert self.timezone is not None
        comps = await self.competitions.get()
        async with self.sports() as sports:
            return await run_full(payload, self.timezone, sports, comps, llm, stages)

    def launch(self, body: RunBody, stages: list[StageId], llm: Llm) -> None:
        run = ActiveRun(f"r_{secrets.token_hex(6)}")
        self.active = run
        run.task = asyncio.create_task(self.drive(run, body, stages, llm))

    async def drive(self, run: ActiveRun, body: RunBody, stage_ids: list[StageId], llm: Llm) -> None:
        async def emit(update: StageUpdatePayload) -> None:
            await self.send(
                StageUpdate(v=1, type="stage.update", run_id=run.run_id, seq=run.next_seq(), ts=now(), payload=update)
            )

        stages = Stages(emit, run.cancelled)

        async def notify(message: str) -> None:
            if stages.current is not None:
                await stages.update("running", message)

        llm.notify = notify
        try:
            await self.send(
                RunAccepted(
                    v=1,
                    type="run.accepted",
                    run_id=run.run_id,
                    seq=run.next_seq(),
                    ts=now(),
                    payload=RunAcceptedPayload(stages=stage_infos(stage_ids)),
                )
            )
            result, story = await body(run, stages)
            self.stories[run.run_id] = story
            u = llm.usage
            log.info(
                "run %s done model=%s tokens=%d/%d cost=%s prompts=%s",
                run.run_id,
                u.model,
                u.input_tokens,
                u.output_tokens,
                u.cost_usd,
                ",".join(f"{k}.{v}" for k, v in sorted(llm.prompt_versions.items())) or "none",
            )
            await self.send(
                RunResult(v=1, type="run.result", run_id=run.run_id, seq=run.next_seq(), ts=now(), payload=result)
            )
        except RunFailure as f:
            await self.run_error(run, f)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("run %s failed", run.run_id)
            await self.run_error(
                run,
                RunFailure(
                    "stage_failed",
                    "Something went wrong. Please try again.",
                    retryable=True,
                    stage=stages.current,
                    reasons=[type(e).__name__],
                ),
            )
        finally:
            self.active = None

    async def run_error(self, run: ActiveRun, f: RunFailure) -> None:
        # Reasons are safe to log: LLM errors have the key scrubbed out.
        log.warning("run %s failed code=%s stage=%s reasons=%s", run.run_id, f.code, f.stage, f.reasons)
        # The socket may already be gone.
        with contextlib.suppress(WebSocketDisconnect, RuntimeError):
            await self.send(
                RunError(
                    v=1,
                    type="run.error",
                    run_id=run.run_id,
                    seq=run.next_seq(),
                    ts=now(),
                    payload=RunErrorPayload(
                        code=f.code,
                        message=f.message,
                        retryable=f.retryable,
                        stage=f.stage,
                        reasons=f.reasons,
                        guardrails=f.guardrails,
                        suggestion=f.suggestion,
                    ),
                )
            )

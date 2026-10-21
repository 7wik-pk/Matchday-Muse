"""The LLM stages, as one interface: a mock today, LiteLLM next.

Each method is one structured-output call whose schema comes from
contracts/pipeline/. Only pick_match may call tools.
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from app.contracts.mcp.find_matches_output import Match
from app.contracts.mcp.search_coverage_output import Result
from app.contracts.pipeline.fact_draft import FactDraft
from app.contracts.pipeline.fact_sheet import FactSheet
from app.contracts.pipeline.grounding_verdict import GroundingVerdict
from app.contracts.pipeline.match_pick import MatchPick
from app.contracts.pipeline.moment_pick import MomentPick
from app.contracts.pipeline.poem import Poem
from app.contracts.ws.server_message import StylePreset
from app.pipeline.signals import Signals
from app.sports import SportsData, Timeline

# run.error codes, shared by the pipeline and the LLM layer.
type ErrorCode = Literal[
    "bad_request", "no_matches", "cancelled", "stage_failed", "timeout", "budget_exceeded",
    "guardrail_failed", "quota_exceeded", "provider_error", "interrupted",
]  # fmt: skip


class LlmFailure(Exception):
    """An LLM call that cannot go on: the pipeline turns it into run.error."""

    def __init__(self, code: ErrorCode, message: str, *, retryable: bool, reasons: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.code: ErrorCode = code
        self.message = message
        self.retryable = retryable
        self.reasons = list(reasons)


@dataclass
class Candidate:
    """A completed match with its timeline and drama signals."""

    match: Match
    timeline: Timeline
    signals: Signals


@dataclass
class Usage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = 0.0


class Llm(Protocol):
    usage: Usage
    prompt_versions: dict[str, str]  # logged with every run
    # Set by the pipeline: a line for the stage panel, such as a retry's wait.
    notify: Callable[[str], Awaitable[None]] | None

    async def pick_match(
        self,
        candidates: Sequence[Candidate],
        tools: SportsData,
        on_search: Callable[[str], Awaitable[None]],
    ) -> MatchPick:
        """May call tools.search_coverage, announcing each query through on_search."""
        ...

    async def pick_moment(self, candidate: Candidate) -> MomentPick: ...

    async def build_facts(self, candidate: Candidate, moment: MomentPick, coverage: Sequence[Result]) -> FactDraft: ...

    async def write_poem(self, sheet: FactSheet, style: StylePreset) -> Poem: ...

    async def repair_poem(self, sheet: FactSheet, style: StylePreset, poem: Poem, problems: Sequence[str]) -> Poem:
        """Rewrites a poem that failed the guardrails, fixing each problem."""
        ...

    async def judge_grounding(self, poem: Poem, sheet: FactSheet) -> GroundingVerdict: ...

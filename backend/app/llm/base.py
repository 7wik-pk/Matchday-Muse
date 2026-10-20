"""The LLM stages, as one interface: a mock today, LiteLLM next.

Each method is one structured-output call whose schema comes from
contracts/pipeline/. Only pick_match may call tools.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

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

    async def pick_match(self, candidates: Sequence[Candidate], tools: SportsData) -> MatchPick: ...

    async def pick_moment(self, candidate: Candidate) -> MomentPick: ...

    async def build_facts(self, candidate: Candidate, moment: MomentPick, coverage: Sequence[Result]) -> FactDraft: ...

    async def write_poem(self, sheet: FactSheet, style: StylePreset) -> Poem: ...

    async def judge_grounding(self, poem: Poem, sheet: FactSheet) -> GroundingVerdict: ...

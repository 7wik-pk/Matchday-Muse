"""The pipeline: a fixed sequence of stages, each announcing itself with
stage.update messages. A full run goes through all ten; a retell reuses a
finished run's story and runs only generate, guardrails and done.
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Literal, NoReturn
from urllib.parse import urlparse

from app.contracts.mcp.find_matches_output import Match
from app.contracts.mcp.get_match_events_output import Event
from app.contracts.mcp.list_competitions_output import Competition
from app.contracts.mcp.search_coverage_output import Result
from app.contracts.pipeline.fact_sheet import FactSheet
from app.contracts.pipeline.guardrail_report import GuardrailCheck, GuardrailReport
from app.contracts.pipeline.match_pick import MatchPick
from app.contracts.pipeline.person import Person
from app.contracts.pipeline.poem import Poem
from app.contracts.pipeline.source_link import SourceLink
from app.contracts.ws.client_message import RunRetellPayload, RunStartPayload
from app.contracts.ws.common import StageId
from app.contracts.ws.server_message import (
    Fact as ResultFact,
)
from app.contracts.ws.server_message import (
    Line,
    MatchSummary,
    PassageText,
    RangeSuggestion,
    RunResultPayload,
    StageInfo,
    StageUpdatePayload,
    Stanza,
    StylePreset,
)
from app.contracts.ws.server_message import (
    Usage as ResultUsage,
)
from app.llm.base import Candidate, Llm
from app.pipeline import ranges, signals
from app.presets import STYLES_BY_ID
from app.sports import SportsData, Timeline, ToolError

STAGE_LABELS: dict[StageId, str] = {
    "resolve_range": "Resolve the date range",
    "fetch_matches": "Find completed matches",
    "score_matches": "Load events and score drama",
    "pick_match": "Pick the match",
    "search_coverage": "Search match coverage",
    "pick_moment": "Pick the moment",
    "build_fact_sheet": "Build the fact sheet",
    "generate": "Write the poem",
    "guardrails": "Check the output",
    "done": "Done",
}
RETELL_STAGES: list[StageId] = ["generate", "guardrails", "done"]

# The checks the guardrails stage reports, with their chip labels.
CHECKS: list[tuple[str, str]] = [
    ("score", "Score"),
    ("names", "Names"),
    ("quotes", "Quotes"),
    ("overlap", "Originality"),
    ("form", "Length and form"),
    ("grounding", "Grounding"),
    ("moderation", "Safety"),
]

LOAD_CONCURRENCY = 4
SHORTLIST = 3
MAX_SOURCES = 5

type ErrorCode = Literal[
    "bad_request", "no_matches", "cancelled", "stage_failed", "timeout", "budget_exceeded",
    "guardrail_failed", "quota_exceeded", "provider_error", "interrupted",
]  # fmt: skip


def stage_infos(stages: Sequence[StageId]) -> list[StageInfo]:
    return [StageInfo(id=s, label=STAGE_LABELS[s]) for s in stages]


class RunFailure(Exception):
    """Ends a run with run.error."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool,
        stage: StageId | None,
        reasons: Sequence[str] = (),
        suggestion: RangeSuggestion | None = None,
    ) -> None:
        super().__init__(message)
        self.code: ErrorCode = code
        self.message = message
        self.retryable = retryable
        self.stage = stage
        self.reasons = list(reasons)
        self.suggestion = suggestion


@dataclass
class Story:
    """What a finished run keeps so it can be retold."""

    sport: str
    competition: str  # league label, such as Premier League
    match: Match
    pick: MatchPick
    sheet: FactSheet


class Stages:
    """Announces each stage as it starts and ends. Cancelling takes effect at
    the next stage boundary, after the running stage finishes."""

    def __init__(self, emit: Callable[[StageUpdatePayload], Awaitable[None]], cancelled: asyncio.Event) -> None:
        self.emit = emit
        self.cancelled = cancelled
        self.current: StageId | None = None
        self.last: StageId | None = None

    def check_cancelled(self) -> None:
        if self.cancelled.is_set():
            raise RunFailure(
                "cancelled", "Run cancelled. Nothing was generated.", retryable=True, stage=self.current or self.last
            )

    async def begin(self, stage: StageId, message: str, progress: float | None = None) -> None:
        self.check_cancelled()
        self.current = stage
        await self.update("running", message, progress)

    async def update(
        self,
        status: Literal["running", "done", "skipped", "failed"],
        message: str,
        progress: float | None = None,
        detail: str | None = None,
    ) -> None:
        assert self.current is not None
        await self.emit(
            StageUpdatePayload(stage=self.current, status=status, message=message, progress=progress, detail=detail)
        )

    async def done(self, message: str, detail: str | None = None, progress: float | None = None) -> None:
        await self.update("done", message, progress, detail)
        self.last, self.current = self.current, None

    async def mark_done(self, stage: StageId, message: str) -> None:
        """A stage with nothing to run, such as done: one update, no running state."""
        self.check_cancelled()
        self.current = stage
        await self.done(message)

    async def fail(self, message: str, failure: RunFailure) -> NoReturn:
        await self.update("failed", message)
        raise failure


def data_failure(stage: StageId, e: ToolError, what: str) -> RunFailure:
    return RunFailure(
        "stage_failed",
        f"Couldn't {what} right now. Please try again in a minute.",
        retryable=True,
        stage=stage,
        reasons=[str(e)],
    )


async def run_full(
    req: RunStartPayload,
    timezone: str,
    sports: SportsData,
    competitions: Sequence[Competition],
    llm: Llm,
    stages: Stages,
) -> tuple[RunResultPayload, Story]:
    if req.output != "text":
        raise RunFailure("bad_request", "Image output arrives in a later phase.", retryable=False, stage=None)
    comp = next((c for c in competitions if c.sport == req.sport and c.league == req.league), None)
    if comp is None:
        raise RunFailure("bad_request", f"{req.sport} {req.league} is not covered.", retryable=False, stage=None)

    # 1. resolve_range
    await stages.begin("resolve_range", f"Resolving the {req.range.granularity}")
    try:
        window = ranges.resolve(req.range, timezone)
    except ranges.BadTimezone as e:
        await stages.fail(
            "Unknown timezone",
            RunFailure("bad_request", str(e), retryable=False, stage="resolve_range"),
        )
    await stages.done(window.label)

    # 2. fetch_matches
    await stages.begin("fetch_matches", f"Asking {comp.source} for {comp.name} results")
    try:
        matches = await sports.find_matches(req.sport, req.league, window.kickoff_from, window.kickoff_to)
    except ToolError as e:
        await stages.fail("The match list did not load", data_failure("fetch_matches", e, "load match results"))
    matches = [m for m in matches if m.status == "completed"]
    if not matches:
        await stages.done("No completed matches")
        raise RunFailure(
            "no_matches",
            f"No {comp.name} matches finished {window.when}.",
            retryable=False,
            stage="fetch_matches",
            suggestion=ranges.suggestion(req.range),
        )
    await stages.done(f"{len(matches)} completed match{'' if len(matches) == 1 else 'es'}")

    # 3. score_matches
    await stages.begin("score_matches", "Loading match events", progress=0.0)
    candidates = await load_candidates(req, matches, sports, stages)
    top = sorted(candidates, key=lambda c: -c.signals.total)[:SHORTLIST]
    await stages.done(
        f"{len(candidates)} of {len(candidates)} matches loaded",
        progress=1.0,
        detail="Strongest drama signals: " + " · ".join(f"{c.match.final_result} ({c.signals.summary()})" for c in top),
    )

    # 4. pick_match
    await stages.begin("pick_match", f"Short-listing {min(SHORTLIST, len(candidates))} of {len(candidates)} matches")
    pick = await llm.pick_match(candidates, sports)
    chosen = next((c for c in candidates if c.match.id == pick.match_id), None)
    if chosen is None:
        await stages.fail(
            "The pick was not one of the matches",
            RunFailure(
                "stage_failed",
                "The match pick went wrong. Please try again.",
                retryable=True,
                stage="pick_match",
                reasons=[f"picked unknown match {pick.match_id!r}"],
            ),
        )
    await stages.done(f"Picked {chosen.match.title} · {pick.angle}", detail=pick.reason)

    # 5. search_coverage
    await stages.begin("search_coverage", "Searching match coverage")
    try:
        coverage = await search(chosen, comp, sports)
    except ToolError as e:
        await stages.fail("Coverage search failed", data_failure("search_coverage", e, "search match coverage"))
    sources = source_links(chosen.timeline, coverage)
    await stages.done(f"{len(sources)} source{'' if len(sources) == 1 else 's'} kept")

    # 6. pick_moment
    await stages.begin("pick_moment", "Reading the timeline")
    moment = await llm.pick_moment(chosen)
    events = {e.source_ref: e for e in chosen.timeline.events}
    unknown = [r for r in [*moment.event_refs, *moment.beats] if r not in events]
    if unknown or not moment.event_refs:
        await stages.fail(
            "The moment did not match the timeline",
            RunFailure(
                "stage_failed",
                "Picking the moment went wrong. Please try again.",
                retryable=True,
                stage="pick_moment",
                reasons=[f"unknown event refs: {', '.join(unknown)}" if unknown else "no moment events"],
            ),
        )
    await stages.done(moment.title, detail=", ".join(beat_label(events[r]) for r in moment.beats))

    # 7. build_fact_sheet
    await stages.begin("build_fact_sheet", "Merging events and coverage")
    draft = await llm.build_facts(chosen, moment, coverage)
    sheet = FactSheet(
        match_id=chosen.match.id,
        competition=comp.name,
        teams_or_participants=[p.name for p in chosen.match.participants],
        final_result=chosen.match.final_result,
        roster=roster(chosen.timeline),
        moment=moment,
        facts=draft.facts,
        sources=sources,
    )
    if problems := fact_sheet_problems(sheet, chosen.timeline):
        await stages.fail(
            "The fact sheet did not check out",
            RunFailure(
                "stage_failed",
                "Building the fact sheet went wrong. Please try again.",
                retryable=True,
                stage="build_fact_sheet",
                reasons=problems,
            ),
        )
    await stages.done(f"{len(sheet.facts)} facts from {len(sources)} source{'' if len(sources) == 1 else 's'}")

    story = Story(sport=req.sport, competition=comp.name, match=chosen.match, pick=pick, sheet=sheet)
    return await write(story, STYLES_BY_ID[req.style], llm, stages), story


async def run_retell(req: RunRetellPayload, story: Story, llm: Llm, stages: Stages) -> RunResultPayload:
    if req.output != "text":
        raise RunFailure("bad_request", "Image output arrives in a later phase.", retryable=False, stage=None)
    return await write(story, STYLES_BY_ID[req.style], llm, stages)


async def write(story: Story, style: StylePreset, llm: Llm, stages: Stages) -> RunResultPayload:
    """generate, guardrails and done: shared by full runs and retells."""
    await stages.begin("generate", "Writing the headline and poem")
    poem = await llm.write_poem(story.sheet, style)
    if not poem.headline.strip() or not any(line.strip() for s in poem.stanzas for line in s.lines):
        await stages.fail(
            "The poem came back empty",
            RunFailure(
                "stage_failed", "Writing the poem went wrong. Please try again.", retryable=True, stage="generate"
            ),
        )
    await stages.done("Poem written")

    await stages.begin("guardrails", f"Running {len(CHECKS)} checks")
    verdict = await llm.judge_grounding(poem, story.sheet)
    known = {f.id for f in story.sheet.facts}
    fact_ids = {v.index: [i for i in v.fact_ids if i in known] for v in verdict.lines}
    # The checks themselves are the next guardrails roadmap item.
    report = GuardrailReport(
        passed=True,
        attempts=1,
        checks=[GuardrailCheck(id=cid, label=label, status="skipped", detail="Not built yet") for cid, label in CHECKS],
    )
    await stages.done(f"Guardrails not built yet: {len(CHECKS)} checks skipped")

    await stages.mark_done("done", "Done")
    return result_payload(story, style, poem, fact_ids, report, llm)


async def load_candidates(
    req: RunStartPayload, matches: Sequence[Match], sports: SportsData, stages: Stages
) -> list[Candidate]:
    limit = asyncio.Semaphore(LOAD_CONCURRENCY)
    loaded = 0

    async def load(m: Match) -> Candidate:
        nonlocal loaded
        async with limit:
            timeline = await sports.get_match_events(req.sport, req.league, m.id)
        loaded += 1
        if loaded < len(matches):
            await stages.update("running", f"{loaded} of {len(matches)} matches loaded", loaded / len(matches))
        return Candidate(match=m, timeline=timeline, signals=signals.compute(timeline))

    try:
        return list(await asyncio.gather(*(load(m) for m in matches)))
    except ToolError as e:
        await stages.fail("Match events did not load", data_failure("score_matches", e, "load match events"))


async def search(chosen: Candidate, comp: Competition, sports: SportsData) -> list[Result]:
    """Two queries built from the teams and competition. A result that does
    not name every team is about some other match, so it is dropped."""
    teams = [p.name for p in chosen.match.participants]
    home, away = teams[:2]
    seen: dict[str, Result] = {}
    for query in (f"{home} {away} {comp.name}", f"{home} v {away}"):
        for r in (await sports.search_coverage(query, max_results=MAX_SOURCES)).results:
            text = f"{r.title} {r.content}".casefold()
            if all(team.casefold() in text for team in teams):
                seen.setdefault(r.url, r)
    return list(seen.values())[:MAX_SOURCES]


def source_links(t: Timeline, coverage: Sequence[Result]) -> list[SourceLink]:
    """The match's own pages first, then coverage, one entry per URL."""
    links: dict[str, SourceLink] = {}
    for s in t.sources:
        links.setdefault(
            s.url, SourceLink(title=s.title, url=s.url, publisher=s.publisher, published_at=s.published_at)
        )
    for r in coverage:
        host = urlparse(r.url).hostname or ""
        links.setdefault(
            r.url,
            SourceLink(
                title=r.title, url=r.url, publisher=host.removeprefix("www.") or None, published_at=r.published_at
            ),
        )
    return list(links.values())


def roster(t: Timeline) -> list[Person]:
    names = dict.fromkeys(a for e in t.events for a in e.actors)
    return [Person(canonical=n, variants=[n.split()[-1]] if " " in n else []) for n in names]


def fact_sheet_problems(sheet: FactSheet, t: Timeline) -> list[str]:
    refs = {e.source_ref for e in t.events} | {str(s.url) for s in sheet.sources}
    ids = [f.id for f in sheet.facts]
    problems = [f"duplicate fact id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    problems += [f"{f.id} cites unknown source {f.source_ref!r}" for f in sheet.facts if f.source_ref not in refs]
    if not any(f.kind == "score" for f in sheet.facts):
        problems.append("no fact states the final score")
    return problems


VERBS = {
    "goal": "Goal",
    "penalty_goal": "Penalty",
    "own_goal": "Own goal",
    "red_card": "Red card",
    "penalty_miss": "Missed penalty",
    "var": "VAR",
}


def beat_label(e: Event) -> str:
    """Such as: Goal: Alexander Isak (70')."""
    what = VERBS.get(e.type) or e.type.replace("_", " ").capitalize()
    return f"{what}: {e.actors[0]} ({e.clock})" if e.actors else f"{what} ({e.clock})"


def result_payload(
    story: Story,
    style: StylePreset,
    poem: Poem,
    fact_ids: dict[int, list[str]],
    report: GuardrailReport,
    llm: Llm,
) -> RunResultPayload:
    sheet, m = story.sheet, story.match
    match_page = str(sheet.sources[0].url)
    n = iter(range(1, 10_000))
    text = PassageText(
        headline=Line(text=poem.headline, fact_ids=fact_ids.get(0, [])),
        stanzas=[
            Stanza(lines=[Line(text=line, fact_ids=fact_ids.get(next(n), [])) for line in s.lines])
            for s in poem.stanzas
        ],
    )
    return RunResultPayload(
        output="text",
        text=text,
        image_url=None,
        style=style.id,
        match=MatchSummary(
            match_id=m.id,
            sport=story.sport,
            competition=story.competition,
            title=m.title,
            participants=[p.name for p in m.participants],
            final_result=m.final_result,
            start_time=m.kickoff,
            venue=m.venue or None,
        ),
        angle=story.pick.angle,
        moment=sheet.moment.title,
        facts=[
            ResultFact(
                id=f.id,
                text=f.text,
                kind=f.kind,
                source_url=f.source_ref if f.source_ref.startswith("http") else match_page,
            )
            for f in sheet.facts
        ],
        sources=sheet.sources,
        guardrails=report,
        usage=ResultUsage(
            model=llm.usage.model,
            input_tokens=llm.usage.input_tokens,
            output_tokens=llm.usage.output_tokens,
            cost_usd=llm.usage.cost_usd,
        ),
    )

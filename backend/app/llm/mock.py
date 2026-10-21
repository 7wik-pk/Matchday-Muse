"""A deterministic stand-in for the LLM stages, so the pipeline runs end to end
without a key. Its picks follow the drama signals; its "poem" is the beats'
facts in plain sentences, padded to the form's shape, and says so in its
first lines. It passes every guardrail by construction.
"""

from collections.abc import Awaitable, Callable, Sequence

from app.contracts.mcp.get_match_events_output import Event
from app.contracts.mcp.search_coverage_output import Result
from app.contracts.pipeline.fact import Fact
from app.contracts.pipeline.fact_draft import FactDraft
from app.contracts.pipeline.fact_sheet import FactSheet
from app.contracts.pipeline.grounding_verdict import GroundingVerdict, LineVerdict
from app.contracts.pipeline.match_pick import MatchPick
from app.contracts.pipeline.moment_pick import MomentPick
from app.contracts.pipeline.poem import Poem, PoemStanza
from app.contracts.ws.server_message import StylePreset
from app.llm.base import Candidate, Usage
from app.pipeline.signals import GOALS
from app.sports import SportsData

KEY_EVENTS = GOALS | {"red_card", "penalty_miss", "var"}
MAX_BEATS = 5
HOOK = ["No model wrote these lines: a mock writer", "sets out the moment's facts in order."]
FILLER = [
    "and still the stands sang on,",
    "while the evening light came down,",
    "and every song rolled round the ground,",
    "till the players walked off slow.",
]
# Fixed forms' stanza shapes; other forms get quatrains.
SHAPES = {"sonnet": [4, 4, 4, 2], "villanelle": [3, 3, 3, 3, 3, 4], "limericks": [5, 5, 5], "clerihews": [4, 4, 4]}


def event_fact(e: Event) -> str:
    """One plain sentence per event, naming only the match's people and teams."""
    who = e.actors[0] if e.actors else "a player"
    team = e.team or "their side"
    score = (e.score_after or "").replace("-", "–")
    match e.type:
        case "goal":
            return f"{e.clock}: {who} scored for {team}, making it {score}."
        case "penalty_goal":
            return f"{e.clock}: {who} scored a penalty for {team}, making it {score}."
        case "own_goal":
            return f"{e.clock}: an own goal by {who} made it {score}."
        case "red_card":
            return f"{e.clock}: {who} of {team} was sent off."
        case "penalty_miss":
            return f"{e.clock}: {who} missed a penalty."
        case "var":
            return f"{e.clock}: a VAR review changed a decision."
    return f"{e.clock}: {e.description}"


def key_events(c: Candidate) -> list[Event]:
    return [e for e in c.timeline.events if e.type in KEY_EVENTS]


def decisive(c: Candidate) -> Event | None:
    """The goal that put the winner ahead for good, or a draw's last goal."""
    goals = [e for e in c.timeline.events if e.type in GOALS and e.score_after]
    if not goals:
        return None
    home, away = (int(p.score or 0) for p in c.match.participants[:2])
    if home == away:
        return goals[-1]
    sign = 1 if home > away else -1
    pick = goals[-1]
    for e in reversed(goals):
        h, a = (int(x) for x in (e.score_after or "0-0").split("-"))
        if (h - a) * sign <= 0:  # the winner was not ahead after this goal
            break
        pick = e
    return pick


class MockLlm:
    def __init__(self) -> None:
        self.usage = Usage(model="mock")
        self.prompt_versions: dict[str, str] = {}
        self.notify: Callable[[str], Awaitable[None]] | None = None
        self._line_facts: dict[str, list[str]] = {}

    async def pick_match(
        self,
        candidates: Sequence[Candidate],
        tools: SportsData,
        on_search: Callable[[str], Awaitable[None]],
    ) -> MatchPick:
        ranked = sorted(candidates, key=lambda c: (-c.signals.total, c.match.kickoff, c.match.id))
        best = ranked[0]
        s = best.signals
        comedy = (s.own_goals or s.penalty_misses) and not (s.lead_changes or s.late_goals)
        return MatchPick(
            match_id=best.match.id,
            reason=f"{best.match.final_result}: {s.summary()}.",
            angle="comedy" if comedy else "drama",
            shortlist=[c.match.id for c in ranked[:3]],
        )

    async def pick_moment(self, candidate: Candidate) -> MomentPick:
        keys = key_events(candidate)
        moment = decisive(candidate) or (keys[0] if keys else candidate.timeline.events[-1])
        if moment in keys:
            i = keys.index(moment)
            beats = keys[max(0, i - (MAX_BEATS - 2)) : i + 2][:MAX_BEATS]
        else:
            beats = [*keys[: MAX_BEATS - 1], moment]
        if len(beats) < 2:
            beats = [candidate.timeline.events[0], moment]
        scorer = moment.actors[0] if moment.actors else "the decider"
        s = candidate.signals
        if moment.type in GOALS:
            what = "The comeback, completed by" if s.came_from_behind else "The decisive goal:"
            title = f"{what} {scorer} at {moment.clock}"
        else:
            title = f"A goalless afternoon, and {moment.description.split('.')[0].lower()}"
        return MomentPick(
            title=title,
            event_refs=[moment.source_ref],
            beats=[e.source_ref for e in beats],
            why_it_matters=f"{s.summary().capitalize()}; it settled {candidate.match.final_result}.",
        )

    async def build_facts(self, candidate: Candidate, moment: MomentPick, coverage: Sequence[Result]) -> FactDraft:
        m, t = candidate.match, candidate.timeline
        page = t.sources[0].url
        facts: list[Fact] = []

        def add(text: str, kind: str, ref: str) -> None:
            facts.append(Fact(id=f"f{len(facts) + 1}", text=text, kind=kind, source_ref=ref, speaker=None))

        venue = f", at {m.venue}" if m.venue else ""
        add(f"Final score: {m.final_result}{venue}.", "score", page)
        wanted = set(moment.beats) | {e.source_ref for e in key_events(candidate)}
        for e in t.events:
            if e.source_ref in wanted:
                add(event_fact(e), "event", e.source_ref)
        if len(t.team_stats) == 2:
            a, b = t.team_stats
            add(
                f"{a.team} had {a.possession_pct:g}% of possession and {a.shots} shots; "
                f"{b.team} had {b.possession_pct:g}% and {b.shots}.",
                "context",
                page,
            )
        for r in coverage:
            if r.content:
                add(f"{r.title}: {r.content.split('. ')[0].rstrip('.')}.", "context", r.url)
        return FactDraft(facts=facts)

    async def write_poem(self, sheet: FactSheet, style: StylePreset) -> Poem:
        by_ref = {f.source_ref: f for f in sheet.facts}
        score = next(f for f in sheet.facts if f.kind == "score")
        content: list[tuple[str, list[str]]] = [(line, []) for line in HOOK]
        content += [(by_ref[ref].text, [by_ref[ref].id]) for ref in sheet.moment.beats if ref in by_ref]
        shape = SHAPES.get(style.id) or [4] * max(2, -(-(len(content) + 1) // 4))
        total = sum(shape)
        lines = content[: total - 1]
        lines += [(FILLER[i % len(FILLER)], []) for i in range(total - 1 - len(lines))]
        lines.append((score.text, [score.id]))
        self._line_facts = dict(lines)
        stanzas, start = [], 0
        for size in shape:
            stanzas.append(PoemStanza(lines=[text for text, _ in lines[start : start + size]]))
            start += size
        return Poem(headline=f"A mock {style.label.lower()}", stanzas=stanzas)

    async def repair_poem(self, sheet: FactSheet, style: StylePreset, poem: Poem, problems: Sequence[str]) -> Poem:
        return await self.write_poem(sheet, style)

    async def judge_grounding(self, poem: Poem, sheet: FactSheet) -> GroundingVerdict:
        lines = [poem.headline] + [line for stanza in poem.stanzas for line in stanza.lines]
        return GroundingVerdict(
            lines=[
                LineVerdict(index=i, fact_ids=self._line_facts.get(text, []), unsupported=[])
                for i, text in enumerate(lines)
            ]
        )

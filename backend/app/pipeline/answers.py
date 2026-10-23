"""What makes an analysis stage's answer usable: the match pick, the moment and
the fact draft. The pipeline checks each answer before going on, and the LLM
layer's development cache keeps only answers that pass, so one bad reply
cannot fail every later run of the same week.
"""

from collections.abc import Iterable, Sequence

from app.contracts.pipeline.fact import Fact
from app.contracts.pipeline.match_pick import MatchPick
from app.contracts.pipeline.moment_pick import MomentPick
from app.sports import Timeline


def pick_problems(pick: MatchPick, match_ids: Iterable[str]) -> list[str]:
    return [] if pick.match_id in set(match_ids) else [f"picked unknown match {pick.match_id!r}"]


def moment_problems(m: MomentPick, t: Timeline) -> list[str]:
    known = {e.source_ref for e in t.events}
    if unknown := [r for r in [*m.event_refs, *m.beats] if r not in known]:
        return [f"unknown event refs: {', '.join(unknown)}"]
    return [] if m.event_refs else ["no moment events"]


def fact_problems(facts: Sequence[Fact], t: Timeline, urls: Iterable[str]) -> list[str]:
    """urls: the sources a fact may cite besides the timeline's events."""
    refs = {e.source_ref for e in t.events} | set(urls)
    ids = [f.id for f in facts]
    problems = [f"duplicate fact id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
    problems += [f"{f.id} cites unknown source {f.source_ref!r}" for f in facts if f.source_ref not in refs]
    if not any(f.kind == "score" for f in facts):
        problems.append("no fact states the final score")
    return problems

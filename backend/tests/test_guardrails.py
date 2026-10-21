"""The output checks. The hand-written sample poems in contracts/ws/examples/
takes.json (one per form, all about Brentford 1–2 Liverpool) must pass every
deterministic check: they are the false-alarm test. Each check then gets
poems it must fail."""

import json
from typing import Any

import pytest

from app.contracts.mcp.get_match_events_output import GetMatchEventsOutput
from app.contracts.pipeline.fact import Fact
from app.contracts.pipeline.fact_sheet import FactSheet
from app.contracts.pipeline.grounding_verdict import GroundingVerdict, LineVerdict
from app.contracts.pipeline.moment_pick import MomentPick
from app.contracts.pipeline.poem import Poem, PoemStanza
from app.guardrails.checks import (
    Material,
    check_form,
    check_grounding,
    check_names,
    check_overlap,
    check_quotes,
    check_score,
    deterministic,
    scores_in,
)
from app.pipeline.run import roster
from tests.conftest import EXAMPLES, FIXTURES

TIMELINE = GetMatchEventsOutput.model_validate_json((FIXTURES / "events" / "401879262.json").read_text())
TAKES = {t["style"]: t for t in json.loads((EXAMPLES / "takes.json").read_text())["takes"]}
MOMENT = MomentPick(title="The comeback", event_refs=["x"], beats=["x", "y"], why_it_matters="It was.")


def material(style: str = "ballad", coverage: list[str] | None = None) -> Material:
    take = TAKES["ballad"]
    sheet = FactSheet(
        match_id="401879262",
        competition="Premier League",
        teams_or_participants=["Brentford", "Liverpool"],
        final_result="Brentford 1–2 Liverpool",
        roster=roster(TIMELINE),
        moment=MOMENT,
        facts=[
            Fact(id=f["id"], text=f["text"], kind=f["kind"], source_ref=f["sourceUrl"], speaker=None)
            for f in take["facts"]
        ],
        sources=[],
    )
    scores = [e.score_after for e in TIMELINE.events if e.score_after]
    return Material(sheet=sheet, style=style, venue="Gtech Community Stadium", scores=scores, coverage=coverage or [])


def poem(*stanzas: list[str], headline: str = "The Bees Who Lost Their Sting") -> Poem:
    return Poem(headline=headline, stanzas=[PoemStanza(lines=s) for s in stanzas])


def take_poem(take: dict[str, Any]) -> Poem:
    return Poem(
        headline=take["text"]["headline"]["text"],
        stanzas=[PoemStanza(lines=[line["text"] for line in s["lines"]]) for s in take["text"]["stanzas"]],
    )


EIGHT = ["A red card came before the break,", "and Brentford's ten held firm,"] * 4


@pytest.mark.parametrize("style", sorted(TAKES))
def test_the_sample_poems_pass(style: str) -> None:
    failed = [c for c in deterministic(take_poem(TAKES[style]), material(style)) if c.status != "pass"]
    assert not failed, failed


# Score


@pytest.mark.parametrize(
    ("text", "found"),
    [
        ("one–one, the scoreboard reckoned", [(1, 1)]),
        ("it ended 1-2 to the Reds", [(1, 2)]),
        ("they won by two goals to one", [(2, 1)]),
        ("one–nil at the break", [(1, 0)]),
        ("a slick one-two down the right", []),
        ("they lined up 4-4-2", []),
        ("in the 45+8th minute the nine-man Bees", []),
        ("from ten men to nine they fell", []),
        ("the 2026 season", []),
    ],
)
def test_scores_in(text: str, found: list[tuple[int, int]]) -> None:
    assert scores_in(text) == found


def test_a_score_that_never_happened_fails() -> None:
    c = check_score(poem([*EIGHT[:-1], "and it finished three–one, you know."]), material())
    assert c.status == "fail" and "3–1" in c.problems[0] and "Brentford 1–2 Liverpool" in c.problems[0]


def test_intermediate_scores_pass() -> None:
    assert check_score(poem([*EIGHT[:-1], "one–nil, then one–one, then two–one."]), material()).status == "pass"


# Names


def test_an_invented_player_fails() -> None:
    c = check_names(poem(["and then young Smithson struck the post,", *EIGHT[1:]]), material())
    assert c.status == "fail" and c.problems[0].startswith("Line 1: Smithson")


def test_names_that_are_allowed() -> None:
    lines = [
        "when Isak's left foot found the net,",  # roster, possessive
        "the Bee and the Reds and Lewis-Potter",  # nickname singular, hyphenated name
        "at the Gtech, on a Saturday;",  # venue, generic
        "Smithson, said nobody; and then",  # line start is skipped
        "the referee, Brooks, said no.",  # named in the facts, not the event roster
        "and VAR looked again: Yarmoliuk",  # VAR; after a colon is a sentence start
        "walked, and Liverpool came back,",
        "two–one to Merseyside at last.",  # Liverpool's region
    ]
    c = check_names(poem(lines), material())
    assert c.status == "pass", c


def test_stock_figures_belong_to_their_form() -> None:
    lines = ["Sing, O Muse, of Fate and Isak,", *EIGHT[1:]]
    assert check_names(poem(lines), material("mock_heroic")).status == "pass"
    assert check_names(poem(lines), material("ballad")).status == "fail"


# Quotes


def test_quotes_must_come_from_a_quote_fact() -> None:
    good = poem([*EIGHT[:-1], 'and the home end sang "what a waste of money".'])
    assert check_quotes(good, material()).status == "pass"
    bad = poem([*EIGHT[:-1], 'and Isak said "I knew I would score".'])
    c = check_quotes(bad, material())
    assert c.status == "fail" and "I knew I would score" in c.problems[0]


# Originality


def test_copied_coverage_fails() -> None:
    source = (
        "Alexander Isak marked his return from injury with the winner as Liverpool came from behind "
        "to beat nine-man Brentford"
    )
    copied = poem([*EIGHT[:-1], "Isak marked his return from injury with the winner as Liverpool came from behind"])
    c = check_overlap(copied, material(coverage=[source]))
    assert c.status == "fail" and "copied" in c.problems[0]
    assert check_overlap(poem(EIGHT), material(coverage=[source])).status == "pass"


# Length and form


def test_form_rules() -> None:
    assert check_form(poem(EIGHT[:4], EIGHT[4:]), material()).status == "pass"
    assert check_form(poem(EIGHT[:6]), material()).status == "fail"  # too short
    assert check_form(poem(EIGHT[:4], EIGHT[4:]), material("sonnet")).status == "fail"  # not 14 lines
    limericks = poem(EIGHT[:5], EIGHT[:4])
    c = check_form(limericks, material("limericks"))
    assert c.status == "fail" and "5 lines" in c.problems[0]
    long_head = poem(EIGHT, headline="one two three four five six seven eight nine ten eleven")
    assert check_form(long_head, material()).status == "fail"


# Grounding


def test_grounding_needs_every_line_supported() -> None:
    p = poem(EIGHT)
    ok = GroundingVerdict(lines=[LineVerdict(index=i, fact_ids=["f4"], unsupported=[]) for i in range(9)])
    assert check_grounding(p, ok).status == "pass"
    bad = ok.model_copy(deep=True)
    bad.lines[2].unsupported = ["Brentford were down to nine"]
    c = check_grounding(p, bad)
    assert c.status == "fail" and c.problems == [
        'Line 2: "Brentford were down to nine" is not supported by the fact sheet.'
    ]
    missing = GroundingVerdict(lines=ok.lines[:5])
    assert check_grounding(p, missing).status == "fail"

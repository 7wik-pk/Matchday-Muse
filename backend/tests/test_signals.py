import json

import pytest

from app.contracts.mcp.get_match_events_output import GetMatchEventsOutput
from app.pipeline.signals import compute, minute
from tests.conftest import FIXTURES


def signals_for(match_id: str):
    return compute(GetMatchEventsOutput.model_validate_json((FIXTURES / "events" / f"{match_id}.json").read_text()))


def test_brentford_liverpool() -> None:
    s = signals_for("401879262")  # Brentford 1–2 Liverpool: behind at half-time, two Brentford reds
    assert (s.goals, s.red_cards, s.lead_changes, s.margin) == (3, 2, 1, 1)
    assert s.came_from_behind and not s.comeback_from_two
    assert s.summary().startswith("came from behind, 2 red cards")


def test_one_sided_match_scores_low() -> None:
    brighton = signals_for("401879261")  # Brighton 5–0 Crystal Palace
    brentford = signals_for("401879262")
    assert brighton.margin == 5
    assert brighton.total < brentford.total


def test_every_fixture_week_match_reconciles() -> None:
    matches = json.loads((FIXTURES / "matches.json").read_text())
    for m in matches:
        s = signals_for(m["id"])
        home, away = (int(p["score"]) for p in m["participants"][:2])
        assert s.goals == home + away, m["title"]
        assert s.margin == abs(home - away), m["title"]


@pytest.mark.parametrize(
    ("clock", "parsed"), [("70'", (70, 0)), ("90+2'", (90, 2)), ("45+8'", (45, 8)), ("HT", (0, 0))]
)
def test_minute(clock: str, parsed: tuple[int, int]) -> None:
    assert minute(clock) == parsed

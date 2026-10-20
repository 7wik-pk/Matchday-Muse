"""score_matches: deterministic drama signals from a match timeline.

The weights are a first guess; tuning them waits for a pick-quality measure
(TODO.md).
"""

import re
from dataclasses import dataclass, field

from app.sports import Timeline

GOALS = {"goal", "penalty_goal", "own_goal"}
LATE_MINUTE = 85
WEIGHTS = {
    "late_goals": 3.0,
    "lead_changes": 3.0,
    "comeback_from_two": 4.0,
    "came_from_behind": 2.0,
    "red_cards": 2.0,
    "penalties": 1.0,
    "penalty_misses": 2.0,
    "own_goals": 2.0,
    "var_reviews": 1.0,
    "goals": 0.5,
}
BLOWOUT_MARGIN = 3
BLOWOUT_PENALTY = 2.0

_CLOCK = re.compile(r"^(\d+)(?:\+(\d+))?'")
_SCORE = re.compile(r"^(\d+)-(\d+)$")


def minute(clock: str) -> tuple[int, int]:
    """Parses a football clock: 90+2' is (90, 2). Anything else counts as minute 0."""
    m = _CLOCK.match(clock)
    return (int(m[1]), int(m[2] or 0)) if m else (0, 0)


@dataclass
class Signals:
    goals: int = 0
    late_goals: int = 0
    lead_changes: int = 0
    comeback_from_two: bool = False
    came_from_behind: bool = False
    red_cards: int = 0
    penalties: int = 0
    penalty_misses: int = 0
    own_goals: int = 0
    var_reviews: int = 0
    margin: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        score = sum(WEIGHTS[k] * float(getattr(self, k)) for k in WEIGHTS)
        return score - (BLOWOUT_PENALTY if self.margin >= BLOWOUT_MARGIN else 0.0)

    def summary(self) -> str:
        """The strongest signals in a few words, such as: came from behind, 2 red cards."""
        parts = list(self.notes)
        for count, one, many in (
            (self.red_cards, "red card", "red cards"),
            (self.late_goals, "late goal", "late goals"),
            (self.own_goals, "own goal", "own goals"),
            (self.penalty_misses, "missed penalty", "missed penalties"),
            (self.var_reviews, "VAR review", "VAR reviews"),
        ):
            if count:
                parts.append(one if count == 1 else f"{count} {many}")
        if self.goals >= 5:
            parts.append(f"{self.goals} goals")
        return ", ".join(parts) or "no standout moments"


def compute(t: Timeline) -> Signals:
    s = Signals()
    home = away = 0
    leader = 0  # 1 home, -1 away, 0 level
    worst = {1: 0, -1: 0}  # the furthest each side fell behind
    for e in t.events:
        if e.type in GOALS:
            s.goals += 1
            if minute(e.clock)[0] >= LATE_MINUTE:
                s.late_goals += 1
            if e.type == "own_goal":
                s.own_goals += 1
            if e.type == "penalty_goal":
                s.penalties += 1
            if e.score_after and (m := _SCORE.match(e.score_after)):
                home, away = int(m[1]), int(m[2])
            now = (home > away) - (home < away)
            if now and leader and now != leader:
                s.lead_changes += 1
            if now:
                leader = now
            worst[1] = max(worst[1], away - home)
            worst[-1] = max(worst[-1], home - away)
        elif e.type == "red_card":
            s.red_cards += 1
        elif e.type == "penalty_miss":
            s.penalties += 1
            s.penalty_misses += 1
        elif e.type == "var":
            s.var_reviews += 1
    s.margin = abs(home - away)
    final = (home > away) - (home < away)
    if final:
        s.came_from_behind = worst[final] >= 1
        s.comeback_from_two = worst[final] >= 2
    else:
        s.comeback_from_two = max(worst.values()) >= 2
    if s.comeback_from_two:
        s.notes.append("came back from two down")
    elif s.came_from_behind:
        s.notes.append("came from behind")
    return s

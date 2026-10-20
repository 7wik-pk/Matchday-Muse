# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Event(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    actors: Annotated[
        list[str],
        Field(
            description="People involved, main actor first: the scorer then the assister; the player coming on then the one going off"
        ),
    ]
    clock: Annotated[
        str,
        Field(
            description="Match clock as the sport writes it: 67', 45+8', Lap 42, Over 18.4"
        ),
    ]
    description: Annotated[str, Field(description="The source's own wording")]
    score_after: Annotated[
        str | None,
        Field(description="Home-away score after a goal or at a break, such as 1-2"),
    ] = None
    source_ref: Annotated[
        str,
        Field(
            description="Provenance for grounding checks: source, match id and play id"
        ),
    ]
    team: Annotated[
        str | None,
        Field(description="The team the event belongs to, when the source says"),
    ] = None
    type: Annotated[
        str,
        Field(
            description="Normalised type. Football: kickoff, half_time, second_half, full_time, goal, penalty_goal, own_goal, penalty_miss, yellow_card, red_card, sub, var, shot_on_target, shot_off_target, shot_blocked, woodwork, foul, handball, corner, offside, injury, other"
        ),
    ]


class Participant(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    abbreviation: Annotated[str, Field(description="Three-letter code, such as BRE")]
    name: Annotated[str, Field(description="Full display name, such as Brentford")]
    role: Annotated[
        str, Field(description="home or away; empty where a sport has neither")
    ]
    score: Annotated[
        str, Field(description="Final or current score, as the source writes it")
    ]
    short_name: Annotated[str, Field(description="Short display name, such as Spurs")]
    winner: Annotated[
        bool,
        Field(
            description="True for the winner of a completed match; false for both sides in a draw"
        ),
    ]


class Match(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    end_estimate: Annotated[
        str,
        Field(
            description="Estimated finish, RFC 3339 UTC: the source gives start times only"
        ),
    ]
    final_result: Annotated[
        str,
        Field(
            description="Canonical result line, such as Brentford 1–2 Liverpool; empty until the match is completed"
        ),
    ]
    id: Annotated[str, Field(description="Source match id, passed to get_match_events")]
    kickoff: Annotated[str, Field(description="Scheduled start, RFC 3339 UTC")]
    league: str
    participants: list[Participant]
    sport: str
    status: Annotated[
        str,
        Field(
            description="scheduled, in_progress, completed or other (postponed, abandoned)"
        ),
    ]
    summary: Annotated[
        str, Field(description="One-line recap from the source; may be empty")
    ]
    title: Annotated[
        str, Field(description="Home v away, such as Brentford v Liverpool")
    ]
    venue: str


class Source(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    published_at: Annotated[
        str | None, Field(description="RFC 3339 UTC, when known")
    ] = None
    publisher: str
    title: str
    url: str


class TeamStat(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    corners: int
    fouls: int
    possession_pct: float
    red_cards: int
    saves: int
    shots: int
    shots_on_target: int
    team: str
    yellow_cards: int


class GetMatchEventsOutput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    coverage: str
    events: Annotated[
        list[Event],
        Field(description="In match order; empty when coverage is scores_only"),
    ]
    match: Match
    sources: Annotated[
        list[Source],
        Field(
            description="Pages to cite: the match page, and the match report when there is one"
        ),
    ]
    team_stats: Annotated[
        list[TeamStat], Field(description="Home first; empty when the source has none")
    ]

# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


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


class FindMatchesOutput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    matches: list[Match]

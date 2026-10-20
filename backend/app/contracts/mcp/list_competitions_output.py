# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Competition(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    coverage: Annotated[
        str,
        Field(
            description="Detail available per match: full_events, round_stats or scores_only"
        ),
    ]
    league: Annotated[
        str, Field(description="League code to pass to find_matches, such as eng.1")
    ]
    name: Annotated[str, Field(description="Display name, such as Premier League")]
    source: Annotated[str, Field(description="Where the data comes from")]
    sport: Annotated[
        str, Field(description="Sport id to pass to find_matches, such as football")
    ]


class ListCompetitionsOutput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    competitions: list[Competition]

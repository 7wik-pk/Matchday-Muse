# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class FindMatchesInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    from_: Annotated[
        AwareDatetime,
        Field(
            alias="from",
            description="Start of the range, inclusive: an RFC 3339 time, such as 2026-10-11T23:00:00Z",
        ),
    ]
    league: Annotated[
        str, Field(description="League code from list_competitions, such as eng.1")
    ]
    sport: Annotated[
        str, Field(description="Sport id from list_competitions, such as football")
    ]
    to: Annotated[
        AwareDatetime,
        Field(description="End of the range, exclusive: an RFC 3339 time"),
    ]

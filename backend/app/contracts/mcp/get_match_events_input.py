# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class GetMatchEventsInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    league: Annotated[
        str, Field(description="League code, as find_matches returned it")
    ]
    match_id: Annotated[str, Field(description="Match id, as find_matches returned it")]
    sport: Annotated[str, Field(description="Sport id, as find_matches returned it")]

# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class MatchPick(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    match_id: Annotated[str, Field(description="One of the candidate match ids.")]
    reason: Annotated[
        str, Field(description="One or two sentences, shown under the pick stage.")
    ]
    angle: Literal["drama", "comedy"]
    shortlist: Annotated[
        list[str],
        Field(
            description="Up to 3 candidate match ids considered, best first, including match_id."
        ),
    ]

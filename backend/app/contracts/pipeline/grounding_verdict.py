# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class LineVerdict(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    index: Annotated[
        int, Field(description="0 is the headline; poem lines count from 1.")
    ]
    fact_ids: Annotated[
        list[str], Field(description="Facts this line rests on; empty for pure colour.")
    ]
    unsupported: Annotated[
        list[str],
        Field(description="Factual claims in the line that no fact supports."),
    ]


class GroundingVerdict(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    lines: list[LineVerdict]

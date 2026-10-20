# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class PoemStanza(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    lines: list[str]


class Poem(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    headline: Annotated[
        str, Field(description="Up to 10 words; does not give away the final result.")
    ]
    stanzas: list[PoemStanza]

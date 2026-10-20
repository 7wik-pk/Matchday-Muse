# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class MomentPick(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    title: Annotated[
        str,
        Field(
            description="One line naming the moment, such as: The comeback, from the red card to the winner."
        ),
    ]
    event_refs: Annotated[
        list[str],
        Field(description="source_refs of the events that make up the moment itself."),
    ]
    beats: Annotated[
        list[str],
        Field(
            description="2 to 5 event source_refs in match order, including the moment."
        ),
    ]
    why_it_matters: Annotated[str, Field(description="One or two sentences.")]

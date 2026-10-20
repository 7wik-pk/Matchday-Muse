# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class Fact(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    id: Annotated[
        str, Field(description="f1, f2 and so on, unique within the fact sheet.")
    ]
    text: Annotated[
        str,
        Field(
            description="One plain sentence, such as: 70': Alexander Isak scored. Brentford 1, Liverpool 2."
        ),
    ]
    kind: Literal["score", "event", "context", "quote"]
    source_ref: Annotated[
        str,
        Field(
            description="The event's source_ref from get_match_events, or the URL of a search result."
        ),
    ]
    speaker: Annotated[
        str | None,
        Field(
            description="Quotes only: who said it, as the source attributes it; null otherwise."
        ),
    ]

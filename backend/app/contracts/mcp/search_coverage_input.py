# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class SearchCoverageInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    max_results: Annotated[
        int | None, Field(description="How many results to return", ge=1, le=10)
    ] = 5
    published_after: Annotated[
        AwareDatetime | None,
        Field(description="Only pages published after this RFC 3339 time"),
    ] = None
    query: Annotated[
        str,
        Field(
            description="What to search for, such as Barcola miss Brentford fans",
            max_length=200,
            min_length=3,
        ),
    ]

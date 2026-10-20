# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import AnyUrl, AwareDatetime, BaseModel, ConfigDict, Field


class SourceLink(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    title: str
    url: AnyUrl
    publisher: str | None
    published_at: Annotated[AwareDatetime | None, Field(alias="publishedAt")]

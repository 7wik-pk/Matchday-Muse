# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from . import fact, moment_pick, person, source_link


class FactSheet(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    match_id: str
    competition: str
    teams_or_participants: list[str]
    final_result: Annotated[
        str,
        Field(
            description="Canonical, from MCP data only, such as Brentford 1–2 Liverpool."
        ),
    ]
    roster: Annotated[
        list[person.Person], Field(description="Every person allowed in the output.")
    ]
    moment: moment_pick.MomentPick
    facts: list[fact.Fact]
    sources: list[source_link.SourceLink]

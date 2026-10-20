# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from pydantic import BaseModel, ConfigDict

from . import fact


class FactDraft(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    facts: list[fact.Fact]

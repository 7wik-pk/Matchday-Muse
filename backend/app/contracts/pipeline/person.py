# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Person(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    canonical: Annotated[str, Field(description="Full name, such as Bukayo Saka.")]
    variants: Annotated[
        list[str], Field(description="Other accepted forms: surname, known-as names.")
    ]

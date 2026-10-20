# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class GuardrailCheck(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    id: Literal[
        "score", "names", "quotes", "overlap", "form", "grounding", "moderation"
    ]
    label: str
    status: Literal["pass", "fail", "skipped"]
    detail: Annotated[
        str | None,
        Field(
            description="One line for the chip's tooltip, such as the failure reason."
        ),
    ]


class GuardrailReport(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    passed: Annotated[
        bool,
        Field(
            description="True only when every check on the final attempt passed or was skipped."
        ),
    ]
    attempts: Annotated[
        int,
        Field(
            description="1 = passed first time; 2 = one repair attempt was made.",
            ge=1,
            le=2,
        ),
    ]
    checks: list[GuardrailCheck]

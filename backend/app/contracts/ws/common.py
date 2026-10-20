# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

type CommonWebSocketTypes = Annotated[
    Any,
    Field(
        description="Types shared by client and server messages.",
        title="Common WebSocket types",
    ),
]


type StageId = Annotated[
    Literal[
        "resolve_range",
        "fetch_matches",
        "score_matches",
        "pick_match",
        "search_coverage",
        "pick_moment",
        "build_fact_sheet",
        "generate",
        "guardrails",
        "done",
    ],
    Field(description="Pipeline stage ids, in run order.", title="StageId"),
]


type StyleId = Annotated[
    Literal[
        "ballad",
        "sonnet",
        "villanelle",
        "mock_heroic",
        "limericks",
        "clerihews",
        "terrace_chant",
        "nursery_rhyme",
    ],
    Field(
        description="Curated style presets; every one is a rhyming form.",
        title="StyleId",
    ),
]


type StyleFamily = Annotated[
    Literal["formal", "light"],
    Field(
        description="Groups the presets in the style select: formal verse or light verse.",
        title="StyleFamily",
    ),
]


type Granularity = Annotated[
    Literal["day", "week", "month"], Field(title="Granularity")
]


class RangeRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    granularity: Granularity
    anchor: Annotated[
        date,
        Field(
            description="Any date inside the wanted day, week or month, in the user's timezone."
        ),
    ]


type OutputKind = Annotated[Literal["text", "image"], Field(title="OutputKind")]


type Angle = Annotated[Literal["drama", "comedy"], Field(title="Angle")]

# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from . import common


class SessionHelloPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    session_token: Annotated[
        str | None,
        Field(
            alias="sessionToken",
            description="Null before the first session.ready; unused until Phase 3.",
        ),
    ]
    timezone: Annotated[
        str, Field(description="The browser's IANA timezone, such as Europe/London.")
    ]
    resume_run_id: Annotated[
        str | None,
        Field(
            alias="resumeRunId",
            description="Phase 3: resume this run after a reconnect.",
        ),
    ] = None
    last_seq: Annotated[
        int | None,
        Field(
            alias="lastSeq",
            description="Phase 3: replay server messages after this seq.",
            ge=0,
        ),
    ] = None


class HouseLlm(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    mode: Literal["house"]


class ByokLlm(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    mode: Literal["byok"]
    provider: Annotated[str, Field(examples=["gemini"])]
    model: Annotated[str, Field(examples=["gemini/gemini-flash"])]
    api_key: Annotated[str, Field(alias="apiKey", min_length=1)]


class RunCancel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    v: Literal[1]
    type: Literal["run.cancel"]
    run_id: Annotated[str, Field(alias="runId")]
    payload: Annotated[dict[str, Any], Field(max_length=0, title="RunCancelPayload")]


class PromptAnswerPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    prompt_id: Annotated[str, Field(alias="promptId")]
    choice: Annotated[
        str, Field(description="The id of one of the prompt.request options.")
    ]


class PromptAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    v: Literal[1]
    type: Literal["prompt.answer"]
    run_id: Annotated[str, Field(alias="runId")]
    payload: Annotated[PromptAnswerPayload, Field(title="PromptAnswerPayload")]


class SessionHello(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    v: Literal[1]
    type: Literal["session.hello"]
    run_id: Annotated[None, Field(alias="runId")]
    payload: SessionHelloPayload


type LlmChoice = Annotated[HouseLlm | ByokLlm, Field(title="LlmChoice")]


class RunStartPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    sport: Annotated[str, Field(examples=["football"])]
    league: Annotated[str, Field(examples=["eng.1"])]
    range: common.RangeRequest
    style: common.StyleId
    output: common.OutputKind
    llm: LlmChoice


class RunRetellPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    from_run_id: Annotated[
        str,
        Field(
            alias="fromRunId",
            description="A run of this session that ended in run.result.",
        ),
    ]
    style: common.StyleId
    output: common.OutputKind
    llm: LlmChoice


class RunStart(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    v: Literal[1]
    type: Literal["run.start"]
    run_id: Annotated[None, Field(alias="runId")]
    payload: RunStartPayload


class RunRetell(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    v: Literal[1]
    type: Literal["run.retell"]
    run_id: Annotated[None, Field(alias="runId")]
    payload: RunRetellPayload


type ClientMessage = Annotated[
    SessionHello | RunStart | RunRetell | RunCancel | PromptAnswer,
    Field(description="Every message the browser sends on /ws.", title="ClientMessage"),
]

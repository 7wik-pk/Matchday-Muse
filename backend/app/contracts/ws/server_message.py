# GENERATED from contracts/ by scripts/gen_contracts.py; do not edit. Run make gen.


from typing import Annotated, Literal

from pydantic import AnyUrl, AwareDatetime, BaseModel, ConfigDict, Field

from ..pipeline import guardrail_report, source_link
from . import common

type Ts = AwareDatetime


class Competition(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    sport: str
    sport_label: Annotated[str, Field(alias="sportLabel")]
    league: str
    league_label: Annotated[str, Field(alias="leagueLabel")]
    coverage: Literal["full_events", "round_stats", "scores_only"]


class StylePreset(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    id: common.StyleId
    label: str
    description: str
    family: common.StyleFamily


class ModelInfo(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    id: Annotated[str, Field(description="LiteLLM model string.")]
    provider: str
    label: str
    tools: bool
    json_: Annotated[bool, Field(alias="json")]
    image_companion: Annotated[
        str | None,
        Field(
            alias="imageCompanion",
            description="Image model for this provider; null disables the Image toggle.",
        ),
    ]
    free_tier_note: Annotated[str | None, Field(alias="freeTierNote")]


class StageInfo(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    id: common.StageId
    label: str


class StageUpdatePayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    stage: common.StageId
    status: Literal["running", "done", "skipped", "failed"]
    message: Annotated[
        str,
        Field(description='Latest one-line status, such as "7 of 10 matches loaded".'),
    ]
    progress: Annotated[float | None, Field(ge=0.0, le=1.0)]
    detail: Annotated[
        str | None,
        Field(description="Expandable extra text, such as the reason for a pick."),
    ]


class StageUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    v: Literal[1]
    type: Literal["stage.update"]
    run_id: Annotated[str, Field(alias="runId")]
    seq: Annotated[int, Field(ge=1)]
    ts: Ts
    payload: Annotated[StageUpdatePayload, Field(title="StageUpdatePayload")]


class PromptOption(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    id: str
    label: str


class PromptRequestPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    prompt_id: Annotated[str, Field(alias="promptId")]
    kind: Literal["free_runs_exhausted", "quota_exceeded", "switch_model"]
    message: str
    options: Annotated[list[PromptOption], Field(min_length=1)]
    retry_after_seconds: Annotated[int | None, Field(alias="retryAfterSeconds", ge=0)]


class PromptRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    v: Literal[1]
    type: Literal["prompt.request"]
    run_id: Annotated[str, Field(alias="runId")]
    seq: Annotated[int, Field(ge=1)]
    ts: Ts
    payload: Annotated[PromptRequestPayload, Field(title="PromptRequestPayload")]


class Line(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    text: Annotated[str, Field(min_length=1)]
    fact_ids: Annotated[
        list[str],
        Field(
            alias="factIds",
            description="The facts this line rests on, from the grounding judge; empty for pure colour.",
        ),
    ]


class Fact(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    id: Annotated[str, Field(examples=["f3"])]
    text: str
    kind: Literal["score", "event", "context", "quote"]
    source_url: Annotated[
        AnyUrl,
        Field(alias="sourceUrl", description="The url of one of the result's sources."),
    ]


class MatchSummary(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    match_id: Annotated[str, Field(alias="matchId")]
    sport: str
    competition: str
    title: Annotated[str, Field(examples=["Brentford v Liverpool"])]
    participants: list[str]
    final_result: Annotated[
        str, Field(alias="finalResult", examples=["Brentford 1–2 Liverpool"])
    ]
    start_time: Annotated[Ts, Field(alias="startTime")]
    venue: str | None


class Usage(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    model: str
    input_tokens: Annotated[int, Field(alias="inputTokens", ge=0)]
    output_tokens: Annotated[int, Field(alias="outputTokens", ge=0)]
    cost_usd: Annotated[
        float | None,
        Field(
            alias="costUsd",
            description="Estimated; null when the model's price is unknown.",
            ge=0.0,
        ),
    ]


class RangeSuggestion(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    label: str
    range: common.RangeRequest


class SessionReadyPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    free_runs_left: Annotated[
        int | None,
        Field(
            alias="freeRunsLeft",
            description="Null until free runs exist (Phase 3); the UI then hides the counter.",
            ge=0,
        ),
    ]
    competitions: Annotated[list[Competition], Field(min_length=1)]
    styles: Annotated[list[StylePreset], Field(min_length=1)]
    models: list[ModelInfo]


class RunAcceptedPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    stages: Annotated[
        list[StageInfo],
        Field(
            description="A full run lists all 10 stages; a retell lists generate, guardrails and done.",
            min_length=1,
        ),
    ]


class RunAccepted(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    v: Literal[1]
    type: Literal["run.accepted"]
    run_id: Annotated[str, Field(alias="runId")]
    seq: Annotated[int, Field(ge=1)]
    ts: Ts
    payload: Annotated[RunAcceptedPayload, Field(title="RunAcceptedPayload")]


class Stanza(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    lines: Annotated[list[Line], Field(min_length=1)]


class RunErrorPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    code: Literal[
        "bad_message",
        "bad_request",
        "no_matches",
        "cancelled",
        "stage_failed",
        "timeout",
        "budget_exceeded",
        "guardrail_failed",
        "quota_exceeded",
        "provider_error",
        "interrupted",
        "retell_unavailable",
    ]
    message: Annotated[str, Field(description="Shown to the user as is.")]
    retryable: bool
    stage: common.StageId | None
    reasons: Annotated[
        list[str],
        Field(
            description="Specific causes, such as the guardrail failures on the last attempt."
        ),
    ]
    guardrails: guardrail_report.GuardrailReport | None
    suggestion: RangeSuggestion | None


class RunError(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    v: Literal[1]
    type: Literal["run.error"]
    run_id: Annotated[
        str | None,
        Field(
            alias="runId",
            description="Null when the failing message never started a run, such as bad_message.",
        ),
    ]
    seq: Annotated[int, Field(ge=0)]
    ts: Ts
    payload: Annotated[RunErrorPayload, Field(title="RunErrorPayload")]


class SessionReady(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    v: Literal[1]
    type: Literal["session.ready"]
    run_id: Annotated[None, Field(alias="runId")]
    seq: Literal[0]
    ts: Ts
    payload: SessionReadyPayload


class PassageText(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    headline: Line
    stanzas: Annotated[list[Stanza], Field(min_length=1)]


class RunResultPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    output: common.OutputKind
    text: Annotated[PassageText | None, Field(description="Set when output is text.")]
    image_url: Annotated[
        AnyUrl | None, Field(alias="imageUrl", description="Set when output is image.")
    ]
    style: common.StyleId
    match: MatchSummary
    angle: common.Angle
    moment: Annotated[str, Field(description="One line naming the retold moment.")]
    facts: Annotated[
        list[Fact],
        Field(description="The fact sheet's facts, which lines refer to by id."),
    ]
    sources: list[source_link.SourceLink]
    guardrails: guardrail_report.GuardrailReport
    usage: Usage


class RunResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    v: Literal[1]
    type: Literal["run.result"]
    run_id: Annotated[str, Field(alias="runId")]
    seq: Annotated[int, Field(ge=1)]
    ts: Ts
    payload: RunResultPayload


type ServerMessage = Annotated[
    SessionReady | RunAccepted | StageUpdate | PromptRequest | RunResult | RunError,
    Field(
        description="Every message the backend sends on /ws. seq increases by 1 per run, starting at 1; session messages carry runId null and seq 0.",
        title="ServerMessage",
    ),
]

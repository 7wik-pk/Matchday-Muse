"""What session.ready offers: competitions labels, style presets and the model registry."""

from app.contracts.ws.server_message import ModelInfo, StylePreset

SPORT_LABELS = {"football": "Football"}

STYLES = [
    StylePreset(id="ballad", label="Ballad", description="Story-telling quatrains, rhymed ABCB.", family="formal"),
    StylePreset(
        id="sonnet",
        label="Shakespearean sonnet",
        description="Fourteen lines, rhymed ABAB CDCD EFEF GG, with a closing couplet.",
        family="formal",
    ),
    StylePreset(
        id="villanelle",
        label="Villanelle",
        description="Nineteen lines on two rhymes, with two refrains that keep returning.",
        family="formal",
    ),
    StylePreset(
        id="mock_heroic",
        label="Mock-heroic couplets",
        description="Grand rhyming couplets for a small affair, in the manner of an 18th-century epic spoof.",
        family="formal",
    ),
    StylePreset(
        id="limericks", label="Limericks", description="Three five-line limericks, rhymed AABBA.", family="light"
    ),
    StylePreset(
        id="clerihews",
        label="Clerihews",
        description="Four-line comic verses, rhymed AABB, each opening with a player's name.",
        family="light",
    ),
    StylePreset(
        id="terrace_chant",
        label="Terrace chant",
        description="Rhyming couplets to sing from the stands, ending in a chorus.",
        family="light",
    ),
    StylePreset(
        id="nursery_rhyme",
        label="Nursery rhyme",
        description="Sing-song couplets, rhymed AABB, after the old playground rhymes.",
        family="light",
    ),
]
STYLES_BY_ID = {s.id: s for s in STYLES}

# Only these models may run: a model string from the browser is never passed
# to LiteLLM unchecked, since some provider prefixes reach local endpoints.
MODELS = [
    ModelInfo(
        id="gemini/gemini-flash-latest",
        provider="gemini",
        label="Gemini Flash",
        tools=True,
        json_=True,
        image_companion="gemini/gemini-3.1-flash-image",
        free_tier_note="Free tier limits apply",
    ),
    ModelInfo(
        id="gemini/gemini-3.5-flash",
        provider="gemini",
        label="Gemini 3.5 Flash",
        tools=True,
        json_=True,
        image_companion="gemini/gemini-3.1-flash-image",
        free_tier_note="Free tier limits apply",
    ),
    ModelInfo(
        id="anthropic/claude-haiku-5-5",
        provider="anthropic",
        label="Claude Haiku 5.5",
        tools=True,
        json_=True,
        image_companion=None,
        free_tier_note=None,
    ),
    ModelInfo(
        id="openai/gpt-5-mini",
        provider="openai",
        label="GPT-5 mini",
        tools=True,
        json_=True,
        image_companion=None,
        free_tier_note=None,
    ),
    ModelInfo(
        id="groq/openai/gpt-oss-120b",
        provider="groq",
        label="GPT-OSS 120B",
        tools=True,
        json_=True,
        image_companion=None,
        free_tier_note="Free tier limits apply",
    ),
    ModelInfo(
        id="groq/openai/gpt-oss-20b",
        provider="groq",
        label="GPT-OSS 20B",
        tools=True,
        json_=True,
        image_companion=None,
        free_tier_note="Free tier limits apply",
    ),
]
MODELS_BY_ID = {m.id: m for m in MODELS}

# The least thinking each model allows, sent as LiteLLM's reasoning_effort to
# keep hidden reasoning tokens (and free-tier quota) down. Gemini 3 and GPT-5
# take "minimal"; GPT-OSS's lowest is "low". Claude thinks only when asked, and
# asking would switch thinking on, so it gets nothing.
REASONING_EFFORT: dict[str, str | None] = {
    "gemini/gemini-flash-latest": "minimal",
    "gemini/gemini-3.5-flash": "minimal",
    "anthropic/claude-haiku-5-5": None,
    "openai/gpt-5-mini": "minimal",
    "groq/openai/gpt-oss-120b": "low",
    "groq/openai/gpt-oss-20b": "low",
}

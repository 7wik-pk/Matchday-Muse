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

MODELS = [
    ModelInfo(
        id="gemini/gemini-flash",
        provider="gemini",
        label="Gemini Flash",
        tools=True,
        json_=True,
        image_companion="gemini/gemini-flash-image",
        free_tier_note="Free tier limits apply",
    ),
    ModelInfo(
        id="anthropic/claude-haiku",
        provider="anthropic",
        label="Claude Haiku",
        tools=True,
        json_=True,
        image_companion=None,
        free_tier_note=None,
    ),
]

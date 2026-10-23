"""Settings, read from the environment once at startup. Every variable is in .env.example."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Self

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode

MIN_TOKEN_LENGTH = 32


class Settings(BaseSettings):
    # The MCP server: a URL (Streamable HTTP, as in compose) or a command to
    # launch over stdio (tests, evals, running outside Docker).
    mcp_server_url: str | None = None
    mcp_server_command: str | None = None
    mcp_auth_token: SecretStr | None = None
    # compose generates the token into a volume; MCP_AUTH_TOKEN wins if set.
    mcp_auth_token_file: Path | None = None

    # MOCK_LLM=true runs every LLM stage on MockLlm: tests, demos, no key.
    mock_llm: bool = False
    # The development key and model behind llm.mode "house" (Phases 0 to 2).
    llm_model: str = "gemini/gemini-flash-latest"
    llm_api_key: SecretStr | None = None
    # Tokens one run may spend across all its LLM calls.
    llm_run_token_budget: int = 150_000
    # Development only: reuse the pick, moment and fact draft across runs of
    # the same week and model (app/llm/analysis_cache.py). Unset: off.
    analysis_cache_dir: Path | None = None
    log_level: str = "info"

    # Production: the built UI, served at / next to /ws (the runtime image sets
    # it). Unset: the UI comes from ng serve.
    static_dir: Path | None = None
    # The page origins allowed to open /ws, comma-separated, such as
    # https://matchday-muse.example.com. Empty allows any, for development;
    # compose.prod.yaml requires it.
    allowed_origins: Annotated[list[str], NoDecode] = []

    @field_validator(
        "mcp_auth_token",
        "mcp_auth_token_file",
        "llm_api_key",
        "mcp_server_url",
        "mcp_server_command",
        "analysis_cache_dir",
        "static_dir",
        mode="before",
    )
    @classmethod
    def empty_is_unset(cls, value: object) -> object:
        # compose passes unset variables as empty strings
        return None if value == "" else value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def comma_separated(cls, value: object) -> object:
        if isinstance(value, str):
            return [o.strip().rstrip("/") for o in value.split(",") if o.strip()]
        return value

    @model_validator(mode="after")
    def check(self) -> Self:
        if (self.mcp_server_url is None) == (self.mcp_server_command is None):
            raise ValueError("set exactly one of MCP_SERVER_URL or MCP_SERVER_COMMAND")
        if self.mcp_auth_token is None and self.mcp_auth_token_file is not None:
            try:
                self.mcp_auth_token = SecretStr(self.mcp_auth_token_file.read_text().strip())
            except OSError as e:
                raise ValueError(f"MCP_AUTH_TOKEN_FILE: {e.strerror}") from e
        if self.mcp_server_url is not None:
            token = self.mcp_auth_token.get_secret_value() if self.mcp_auth_token else ""
            if len(token) < MIN_TOKEN_LENGTH:
                raise ValueError(f"MCP_SERVER_URL needs MCP_AUTH_TOKEN of at least {MIN_TOKEN_LENGTH} characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

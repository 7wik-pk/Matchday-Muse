"""Settings, read from the environment once at startup. Every variable is in .env.example."""

from functools import lru_cache
from typing import Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings

MIN_TOKEN_LENGTH = 32


class Settings(BaseSettings):
    # The MCP server: a URL (Streamable HTTP, as in compose) or a command to
    # launch over stdio (tests, evals, running outside Docker).
    mcp_server_url: str | None = None
    mcp_server_command: str | None = None
    mcp_auth_token: SecretStr | None = None

    # The real LLM stages arrive in the next roadmap item.
    mock_llm: bool = True
    log_level: str = "info"

    @model_validator(mode="after")
    def check(self) -> Self:
        if (self.mcp_server_url is None) == (self.mcp_server_command is None):
            raise ValueError("set exactly one of MCP_SERVER_URL or MCP_SERVER_COMMAND")
        if self.mcp_server_url is not None:
            token = self.mcp_auth_token.get_secret_value() if self.mcp_auth_token else ""
            if len(token) < MIN_TOKEN_LENGTH:
                raise ValueError(f"MCP_SERVER_URL needs MCP_AUTH_TOKEN of at least {MIN_TOKEN_LENGTH} characters")
        if not self.mock_llm:
            raise ValueError("the real LLM stages are not built yet; set MOCK_LLM=true")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

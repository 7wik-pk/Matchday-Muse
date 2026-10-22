from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings

URL = "http://mcp-server:8081/mcp"


def test_empty_values_are_unset() -> None:
    s = Settings(mcp_server_command="x", llm_api_key="", mcp_auth_token="", mcp_auth_token_file="")
    assert s.llm_api_key is None and s.mcp_auth_token is None and s.mcp_auth_token_file is None


@pytest.mark.parametrize(
    ("token", "want"),
    [("", "f" * 64), ("a" * 32, "a" * 32)],
    ids=["from the file", "the variable wins"],
)
def test_token_file(tmp_path: Path, token: str, want: str) -> None:
    path = tmp_path / "token"
    path.write_text("f" * 64 + "\n")
    s = Settings(mcp_server_url=URL, mcp_auth_token=token, mcp_auth_token_file=path)
    assert s.mcp_auth_token is not None and s.mcp_auth_token.get_secret_value() == want


def test_missing_token_file(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="MCP_AUTH_TOKEN_FILE"):
        Settings(mcp_server_url=URL, mcp_auth_token_file=tmp_path / "missing")

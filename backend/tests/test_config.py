from app.config import Settings


def test_empty_values_are_unset() -> None:
    s = Settings(mcp_server_command="x", llm_api_key="", mcp_auth_token="")
    assert s.llm_api_key is None and s.mcp_auth_token is None

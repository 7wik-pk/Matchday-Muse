"""The real MCP client against the real Go server over stdio. Only the tools
that need no network are called: list_competitions, offline search, and an
error. Skipped when Go is not installed."""

import shutil
import subprocess
from pathlib import Path

import anyio
import pytest

from app.config import Settings
from app.sports import ToolError, connect

MCP_SERVER = Path(__file__).resolve().parents[2] / "mcp-server"

pytestmark = pytest.mark.skipif(shutil.which("go") is None, reason="needs Go to build the MCP server")


@pytest.fixture(scope="module")
def server_binary(tmp_path_factory: pytest.TempPathFactory) -> str:
    out = tmp_path_factory.mktemp("bin") / "mcp-server"
    subprocess.run(["go", "build", "-o", str(out), "./cmd/server"], cwd=MCP_SERVER, check=True)
    return str(out)


def test_tools_over_stdio(server_binary: str) -> None:
    async def main() -> None:
        async with connect(Settings(mcp_server_command=server_binary)) as sports:
            comps = await sports.list_competitions()
            assert [(c.sport, c.league) for c in comps] == [("football", "eng.1")]
            hits = await sports.search_coverage("Isak winner nine-man Brentford", max_results=2)
            assert hits.provider == "fixture" and "Isak" in hits.results[0].title
            with pytest.raises(ToolError, match=r"supported: eng\.1"):
                await sports.get_match_events("football", "esp.1", "1")

    anyio.run(main)


def test_errors_raised_inside_a_session_come_out_unwrapped(server_binary: str) -> None:
    """The MCP client's task groups wrap exceptions; connect() unwraps them."""

    class Stop(Exception):
        pass

    async def main() -> None:
        async with connect(Settings(mcp_server_command=server_binary)) as sports:
            await sports.list_competitions()
            raise Stop

    with pytest.raises(Stop):
        anyio.run(main)

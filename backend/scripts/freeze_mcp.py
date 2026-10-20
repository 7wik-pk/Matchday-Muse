"""Records MCP tool outputs into tests/fixtures/mcp/, through the real client,
so backend tests run with no network and no Go server.

    uv run python scripts/freeze_mcp.py ../mcp-server/bin/mcp-server

Covers Sat 10 to Mon 19 Oct 2026 (the Go server's own testdata week, plus a
day either side), every match's events, and the coverage searches the
pipeline makes for each match.
"""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.contracts.mcp.find_matches_output import Match
from app.sports import connect

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "mcp"
START = datetime(2026, 10, 10, tzinfo=UTC)
END = datetime(2026, 10, 20, tzinfo=UTC)


def dump(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def queries(m: Match, competition: str) -> list[str]:
    home, away = (p.name for p in m.participants[:2])
    return [f"{home} {away} {competition}", f"{home} v {away}"]


async def main(command: str) -> None:
    async with connect(Settings(mcp_server_command=command)) as sports:
        comps = await sports.list_competitions()
        dump(OUT / "competitions.json", [c.model_dump(mode="json") for c in comps])
        matches = await sports.find_matches("football", "eng.1", START, END)
        dump(OUT / "matches.json", [m.model_dump(mode="json") for m in matches])
        searches = {}
        for m in matches:
            timeline = await sports.get_match_events("football", "eng.1", m.id)
            dump(OUT / "events" / f"{m.id}.json", timeline.model_dump(mode="json", exclude_none=True))
            for q in queries(m, comps[0].name):
                searches[q] = (await sports.search_coverage(q, max_results=5)).model_dump(
                    mode="json", exclude_none=True
                )
        dump(OUT / "search.json", searches)
    print(f"{len(matches)} matches, {len(searches)} searches -> {OUT}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))

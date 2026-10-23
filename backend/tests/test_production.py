"""The production shape: the built UI served next to /ws, and sockets only
from the allowed origins."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config import Settings
from app.main import create_app
from tests.conftest import FixtureSports, factory, hello

SITE = "https://matchday-muse.example.com"


def test_the_ui_is_served_next_to_the_socket(sports: FixtureSports, tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<app-root></app-root>")
    (tmp_path / "main.js").write_text("console.log('ui')")
    with TestClient(create_app(factory(sports), static_dir=tmp_path)) as client:
        assert client.get("/").text == "<app-root></app-root>"
        assert client.get("/main.js").text == "console.log('ui')"
        assert client.get("/healthz").json() == {"status": "ok"}
        with client.websocket_connect("/ws") as ws:
            assert hello(ws)["type"] == "session.ready"


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [(SITE, True), ("https://evil.example.com", False), (None, False)],
    ids=["the site", "another site", "no origin"],
)
def test_only_allowed_origins_open_a_socket(sports: FixtureSports, origin: str | None, allowed: bool) -> None:
    headers = {"origin": origin} if origin else {}
    with TestClient(create_app(factory(sports), allowed_origins=[SITE])) as client:
        if allowed:
            with client.websocket_connect("/ws", headers=headers) as ws:
                assert hello(ws)["type"] == "session.ready"
        else:
            with pytest.raises(WebSocketDisconnect) as refused, client.websocket_connect("/ws", headers=headers):
                pass
            assert refused.value.code == 1008


def test_any_origin_when_none_are_set(sports: FixtureSports) -> None:
    with (
        TestClient(create_app(factory(sports))) as client,
        client.websocket_connect("/ws", headers={"origin": "http://localhost:4200"}) as ws,
    ):
        assert hello(ws)["type"] == "session.ready"


def test_allowed_origins_are_comma_separated() -> None:
    s = Settings(mcp_server_command="x", allowed_origins=f" {SITE}/ , http://localhost:8080,")
    assert s.allowed_origins == [SITE, "http://localhost:8080"]
    assert Settings(mcp_server_command="x", allowed_origins="").allowed_origins == []

"""Protocol tests: the socket, driven like the UI drives it, with every server
message checked against contracts/ws/ and compared with the scripted runs the
frontend mock replays."""

import logging
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.sports import ToolError
from tests.conftest import (
    FixtureSports,
    Gate,
    Message,
    check,
    example,
    example_messages,
    factory,
    hello,
    start_payload,
    until_end,
)


def start(ws, **changes) -> None:
    ws.send_json({"v": 1, "type": "run.start", "runId": None, "payload": start_payload(**changes)})


def updates(messages: list[Message]) -> list[tuple[str, str]]:
    return [(m["payload"]["stage"], m["payload"]["status"]) for m in messages if m["type"] == "stage.update"]


def test_session_ready_matches_the_scripted_session(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ready = hello(ws)
    scripted = example_messages("session")[0]
    assert ready["type"] == "session.ready"
    assert (ready["runId"], ready["seq"]) == (None, 0)
    assert ready["payload"] == scripted["payload"]


def test_full_run(client: TestClient, sports: FixtureSports) -> None:
    with client.websocket_connect("/ws") as ws:
        hello(ws)
        start(ws)
        messages = until_end(ws)

    accepted = messages[0]
    scripted = example_messages("success")
    assert accepted["type"] == "run.accepted"
    assert accepted["payload"] == scripted[0]["payload"], "same stages and labels as the scripted run"
    assert [m["seq"] for m in messages] == list(range(1, len(messages) + 1))
    assert {m["runId"] for m in messages} == {accepted["runId"]}

    # Each stage runs, then finishes, in run order; done is announced once.
    stages = [s["id"] for s in accepted["payload"]["stages"]]
    seen = updates(messages)
    assert [s for s, status in seen if status == "done"] == stages
    assert ("done", "running") not in seen
    for stage in stages[:-1]:
        assert seen.index((stage, "running")) < seen.index((stage, "done"))

    result = messages[-1]
    assert result["type"] == "run.result"
    p = result["payload"]
    assert p["match"]["finalResult"] == "Brentford 1–2 Liverpool"
    assert p["style"] == "ballad"
    assert sports.calls.count("get_match_events") == 10

    # The rules validate.mjs applies to the scripted results.
    fact_ids = {f["id"] for f in p["facts"]}
    source_urls = {s["url"] for s in p["sources"]}
    assert all(f["sourceUrl"] in source_urls for f in p["facts"])
    lines = [p["text"]["headline"], *(line for s in p["text"]["stanzas"] for line in s["lines"])]
    assert all(set(line["factIds"]) <= fact_ids for line in lines)
    assert any(line["factIds"] for line in lines)
    assert p["guardrails"]["passed"] and {c["status"] for c in p["guardrails"]["checks"]} == {"skipped"}


def test_retell_reuses_the_story(client: TestClient, sports: FixtureSports) -> None:
    with client.websocket_connect("/ws") as ws:
        hello(ws)
        start(ws)
        first = until_end(ws)[-1]
        calls = len(sports.calls)
        ws.send_json(
            {
                "v": 1,
                "type": "run.retell",
                "runId": None,
                "payload": {
                    "fromRunId": first["runId"],
                    "style": "limericks",
                    "output": "text",
                    "llm": {"mode": "house"},
                },
            }
        )
        messages = until_end(ws)

    accepted, result = messages[0], messages[-1]
    assert accepted["payload"] == example_messages("retell")[0]["payload"]
    assert accepted["runId"] != first["runId"]
    assert result["type"] == "run.result"
    assert result["payload"]["style"] == "limericks"
    assert result["payload"]["match"] == first["payload"]["match"]
    assert result["payload"]["facts"] == first["payload"]["facts"]
    assert len(sports.calls) == calls, "a retell makes no sports calls"


def test_retell_of_an_unknown_run(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        hello(ws)
        ws.send_json(
            {
                "v": 1,
                "type": "run.retell",
                "runId": None,
                "payload": {"fromRunId": "r_gone", "style": "sonnet", "output": "text", "llm": {"mode": "house"}},
            }
        )
        error = check(ws.receive_json())
    assert (error["type"], error["runId"], error["seq"]) == ("run.error", None, 0)
    assert error["payload"]["code"] == "retell_unavailable"


def test_no_matches_suggests_the_whole_week(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        hello(ws)
        start(ws, range={"granularity": "day", "anchor": "2026-10-14"})
        messages = until_end(ws)
    scripted = example_messages("no-matches")
    error = messages[-1]["payload"]
    assert error["code"] == "no_matches"
    assert error["message"] == scripted[-1]["payload"]["message"]
    assert error["suggestion"] == scripted[-1]["payload"]["suggestion"]
    assert updates(messages)[-1] == ("fetch_matches", "done")


def test_cancel_stops_at_the_next_stage(sports: FixtureSports) -> None:
    gate = Gate()
    find = sports.find_matches

    async def held(*args, **kwargs):
        await gate.wait()
        return await find(*args, **kwargs)

    sports.find_matches = held  # type: ignore[method-assign]
    with TestClient(create_app(factory(sports))) as client, client.websocket_connect("/ws") as ws:
        hello(ws)
        start(ws)
        accepted = check(ws.receive_json())
        while check(ws.receive_json())["payload"].get("stage") != "fetch_matches":
            pass
        ws.send_json({"v": 1, "type": "run.cancel", "runId": accepted["runId"], "payload": {}})
        time.sleep(0.2)  # let the session read the cancel before the stage finishes
        gate.release()
        messages = until_end(ws)
    error = messages[-1]
    assert updates(messages) == [("fetch_matches", "done")]
    assert error["payload"]["code"] == "cancelled"
    assert error["payload"]["stage"] == "fetch_matches"
    assert error["payload"]["retryable"]


def test_a_failing_tool_fails_its_stage(sports: FixtureSports) -> None:
    async def broken(*args, **kwargs):
        raise ToolError("find_matches", "ESPN returned HTTP 503")

    sports.find_matches = broken  # type: ignore[method-assign]
    with TestClient(create_app(factory(sports))) as client, client.websocket_connect("/ws") as ws:
        hello(ws)
        start(ws)
        messages = until_end(ws)
    assert updates(messages)[-1] == ("fetch_matches", "failed")
    error = messages[-1]["payload"]
    assert (error["code"], error["stage"], error["retryable"]) == ("stage_failed", "fetch_matches", True)
    assert "HTTP 503" in error["reasons"][0]


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("not json", "bad_message"),
        ('{"v": 1, "type": "run.launch", "runId": null, "payload": {}}', "bad_message"),
        ('{"v": 1, "type": "run.start", "runId": null, "payload": {"sport": "football"}}', "bad_message"),
    ],
)
def test_bad_messages(client: TestClient, raw: str, code: str) -> None:
    with client.websocket_connect("/ws") as ws:
        hello(ws)
        ws.send_text(raw)
        error = check(ws.receive_json())
    assert (error["runId"], error["seq"], error["payload"]["code"]) == (None, 0, code)


def test_run_before_hello(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        start(ws)
        error = check(ws.receive_json())
    assert error["payload"]["code"] == "bad_request"


def test_one_run_at_a_time(sports: FixtureSports) -> None:
    gate = Gate()
    find = sports.find_matches

    async def held(*args, **kwargs):
        await gate.wait()
        return await find(*args, **kwargs)

    sports.find_matches = held  # type: ignore[method-assign]
    with TestClient(create_app(factory(sports))) as client, client.websocket_connect("/ws") as ws:
        hello(ws)
        start(ws)
        while check(ws.receive_json())["payload"].get("stage") != "fetch_matches":
            pass
        start(ws)
        error = check(ws.receive_json())
        gate.release()
        until_end(ws)
    assert (error["runId"], error["payload"]["code"]) == (None, "bad_request")


def test_byok_key_is_never_echoed_or_logged(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    key = "sk-test-0123456789-never-echo"
    caplog.set_level(logging.DEBUG)
    with client.websocket_connect("/ws") as ws:
        hello(ws)
        start(ws, llm={"mode": "byok", "provider": "gemini", "model": "gemini/gemini-flash", "apiKey": key})
        messages = until_end(ws)
    assert messages[-1]["type"] == "run.result"
    assert all(key not in str(m) for m in messages)
    assert key not in caplog.text


def test_scripted_runs_use_the_real_stage_labels() -> None:
    """The mock's scripts and the backend must not drift apart."""
    from app.pipeline.run import STAGE_LABELS

    for name in ("success", "stage-failed", "no-matches", "cancelled", "quota-exceeded", "guardrail-failed"):
        stages = example_messages(name)[0]["payload"]["stages"]
        assert {s["id"]: s["label"] for s in stages} == STAGE_LABELS, name
    assert example("success")["start"]["range"]["anchor"] == "2026-10-12"
    assert datetime.fromisoformat("2026-10-12").weekday() == 0


def test_coverage_about_other_matches_is_dropped(client: TestClient) -> None:
    """The fixture search returns other Liverpool and Brentford reports too."""
    with client.websocket_connect("/ws") as ws:
        hello(ws)
        start(ws)
        result = until_end(ws)[-1]
    urls = [s["url"] for s in result["payload"]["sources"]]
    assert all(u.endswith("/401879262") for u in urls), urls

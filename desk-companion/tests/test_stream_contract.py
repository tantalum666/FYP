"""The phone and the web share one SSE body. Chunk boundaries are not part of it."""

from pathlib import Path

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.stream_contract import EVENT_TYPES, check_event, parse_sse


FIXTURE = Path(__file__).resolve().parents[1] / "contracts" / "assistant-stream.sse"


def test_fixture_lists_every_event_and_survives_split_chunks():
    body = FIXTURE.read_text(encoding="utf-8")
    events = parse_sse(body)
    assert [event["type"] for event in events] == [
        "tool",
        "preview",
        "preview",
        "tool",
        "preview",
        "delta",
        "done",
        "error",
    ]
    assert {event["type"] for event in events} == EVENT_TYPES
    for event in events:
        check_event(event)
    assert events[0]["phase"] == "started" and "arguments" not in events[0]
    assert events[3]["saved"] is False and events[3]["outcome"] == "ok"
    assert events[6]["reply"]["message"] == "It is Tuesday. Morning."
    assert events[7] == {"type": "error", "code": "TEXT_AI_UNAVAILABLE", "status": 503}
    pieces = [body[index : index + 5] for index in range(0, len(body), 5)]
    assert parse_sse("".join(pieces)) == events


def test_phone_and_web_share_the_live_stream_endpoint(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    client = TestClient(app)
    client.post(
        "/api/session",
        json={"username": "owner", "password": "fixture-only"},
        headers={"X-Desk-Request": "1"},
    )
    response = client.post(
        "/api/assistant/messages/stream",
        json={"message": "Remember: the code is lantern", "language": "en"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "native-contract"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    assert events
    for event in events:
        check_event(event)
    assert {event["type"] for event in events} <= EVENT_TYPES
    assert events[-1]["type"] == "done"
    assert events[-1]["reply"]["saved"] is False
    assert any(event["type"] == "tool" and event["tool"] == "memory_save_draft" for event in events)
    assert app.state.runtime.memory.for_model() == []

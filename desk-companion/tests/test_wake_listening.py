import asyncio
import pytest
from desk.app import create_app
from desk.store import DomainError


class Socket:
    def __init__(self, items):
        self.items = iter(items)
        self.sent = []
        self.closed = False

    async def receive(self):
        return next(self.items)

    async def send_json(self, data):
        self.sent.append(data)

    async def close(self, code=1000):
        self.closed = True


class Detector:
    def __init__(self):
        self.calls = 0

    def accept(self, samples):
        self.calls += 1
        return "ALICE" if self.calls == 2 else None


def configured(tmp_path):
    r = create_app(tmp_path, scheduler=False).state.runtime
    r.wake.available = lambda: True
    owner = {"kind": "owner", "session": r.store.create_owner_session()}
    return r, owner


def test_wake_detects_locally_without_consuming_a_voice_ticket(tmp_path):
    r, owner = configured(tmp_path)
    detector = Detector()
    r.wake.detector_factory = lambda: detector
    issued = r.wake.ticket(owner)
    lease, principal = r.wake.consume(issued["ticket"])
    socket = Socket([{"type": "websocket.receive", "bytes": bytes(1280)}] * 2)
    asyncio.run(r.wake.listen(socket, lease, principal))
    assert socket.sent == [{"type": "ready", "word": "Alice"}, {"type": "wake", "word": "Alice"}]
    assert socket.closed and r.wake.active is None and not r.voice.active and not r.voice.tickets


def test_owner_revocation_duplicate_ticket_and_parallel_voice_are_fenced(tmp_path):
    r, owner = configured(tmp_path)
    with pytest.raises(DomainError):
        r.wake.ticket({"kind": "agent"})
    ticket = r.wake.ticket(owner)["ticket"]
    r.wake.consume(ticket)
    with pytest.raises(DomainError):
        r.wake.consume(ticket)
    with pytest.raises(DomainError):
        r.wake.ticket(owner)
    r.wake.active = None
    r.voice.active = True
    with pytest.raises(DomainError):
        r.wake.ticket(owner)


def test_invalid_frames_release_local_detector_slot(tmp_path):
    r, owner = configured(tmp_path)
    r.wake.detector_factory = Detector
    lease, principal = r.wake.consume(r.wake.ticket(owner)["ticket"])
    socket = Socket([{"type": "websocket.receive", "bytes": b"odd"}])
    asyncio.run(r.wake.listen(socket, lease, principal))
    assert socket.closed and r.wake.active is None
    assert socket.sent[-1] == {"type": "error", "code": "WAKE_UNAVAILABLE"}


def test_wake_route_requires_origin_and_consumes_owner_ticket_once(tmp_path):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    app = create_app(tmp_path, scheduler=False)
    r = app.state.runtime
    r.wake.available = lambda: True
    r.wake.detector_factory = Detector
    client = TestClient(app)
    client.cookies.set("desk_companion_session", r.store.create_owner_session())
    response = client.post("/api/wake/tickets", json={}, headers={"X-Desk-Request": "1"})
    assert response.status_code == 200
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/api/wake/ws", headers={"origin": "https://untrusted.invalid"}
        ):
            pass
    with client.websocket_connect(
        "/api/wake/ws", headers={"origin": "http://127.0.0.1:5191"}
    ) as socket:
        socket.send_json({"ticket": response.json()["ticket"]})
        assert socket.receive_json()["type"] == "ready"
        socket.send_bytes(bytes(1280))
        socket.send_bytes(bytes(1280))
        assert socket.receive_json() == {"type": "wake", "word": "Alice"}
    assert not r.voice.active and r.wake.active is None
    with pytest.raises(DomainError):
        r.wake.consume(response.json()["ticket"])


def test_signout_invalidates_a_previously_issued_wake_ticket(tmp_path):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    app = create_app(tmp_path, scheduler=False)
    r = app.state.runtime
    r.wake.available = lambda: True
    client = TestClient(app)
    client.cookies.set("desk_companion_session", r.store.create_owner_session())
    ticket = client.post("/api/wake/tickets", json={}, headers={"X-Desk-Request": "1"}).json()[
        "ticket"
    ]
    assert client.delete("/api/session", headers={"X-Desk-Request": "1"}).status_code == 200
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/api/wake/ws", headers={"origin": "http://127.0.0.1:5191"}
        ) as socket:
            socket.send_json({"ticket": ticket})
            socket.receive_json()
    assert r.wake.active is None and not r.voice.active


def test_wake_and_cloud_voice_share_one_capture_slot(tmp_path):
    from desk.app import create_app
    from desk.voice import VoiceConfig
    from desk.store import DomainError
    import pytest

    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    runtime.voice.config = VoiceConfig(
        "openai_realtime", "wss://api.openai.com/v1/realtime", "gpt-realtime-2.1", "fixture-key"
    )
    owner = {"kind": "owner", "id": "owner", "session": runtime.store.create_owner_session()}
    assert runtime.wake.lock is runtime.voice.lock
    ticket = runtime.voice.ticket(owner)["ticket"]
    runtime.wake.active = "other-window-local-listener"
    with pytest.raises(DomainError, match="VOICE_BUSY"):
        runtime.voice.ticket(owner)
    with pytest.raises(DomainError, match="VOICE_TICKET_EXPIRED"):
        runtime.voice.consume(ticket)
    runtime.wake.active = None
    assert runtime.voice.consume(runtime.voice.ticket(owner)["ticket"])["id"] == "owner"

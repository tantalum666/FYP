"""Web Push stays off unless DESK_WEB_PUSH=1. Tests never open a network connection."""

import json
import os
from datetime import UTC, datetime

import httpx
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.notify import Notice, Notifier
from desk.store import Store
from desk.web_push import (
    HttpPushSender,
    PushService,
    VapidKeys,
    b64url,
    b64url_decode,
    decrypt,
    push_enabled,
)

ENDPOINT = "https://push.example.test/sub/1"


def _subscriber():
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    auth = os.urandom(16)
    return key, b64url(public), b64url(auth)


def _notice(day="2026-10-02"):
    return Notice(
        f"morning_brief-{day}",
        "morning_brief",
        "Morning briefing",
        "早晨简报",
        "1 open task.",
        "1 件事务。",
        "Quiet hours are not in effect.",
        "当前不在安静时段。",
    )


class _Recording:
    def __init__(self):
        self.calls = []

    def send(self, endpoint, body, headers):
        self.calls.append((endpoint, body, headers))


def test_the_private_key_is_owner_only_and_the_flag_defaults_off(tmp_path, monkeypatch):
    monkeypatch.delenv("DESK_WEB_PUSH", raising=False)
    assert push_enabled() is False
    app = create_app(tmp_path / "off", password="fixture-only", scheduler=False)
    assert app.state.runtime.notify.push is None
    assert not (tmp_path / "off" / "vapid-private.pem").exists()
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture-only"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    headers = {"X-Desk-Request": "1"}
    assert client.get("/api/push", headers=headers).json()["enabled"] is False
    refused = client.post(
        "/api/push/subscriptions",
        json={"endpoint": ENDPOINT, "p256dh": "x" * 88, "auth": "y" * 22},
        headers={**headers, "X-Operation-Id": "nope"},
    )
    assert refused.status_code == 404
    assert refused.json()["error"]["code"] == "PUSH_DISABLED"

    path = tmp_path / "vapid-private.pem"
    first = VapidKeys.load_or_create(path)
    assert path.stat().st_mode & 0o777 == 0o600
    second = VapidKeys.load_or_create(path)
    assert first.public_uncompressed() == second.public_uncompressed()


def test_a_fake_sender_obeys_quiet_hours_dedupe_and_revocation(tmp_path):
    store = Store(tmp_path, password="fixture-only", clock=lambda: datetime(2026, 10, 2, tzinfo=UTC))
    private, p256dh, auth = _subscriber()
    recording = _Recording()
    service = PushService(store, recording, tmp_path / "vapid-private.pem")
    saved = service.save(ENDPOINT, p256dh, auth, "subscribe")
    notifier = Notifier(store, push=service)
    assert notifier.publish(_notice(), quiet=True)[1]["status"] == "quiet"
    assert recording.calls == []
    assert notifier.publish(_notice(), quiet=False)[1]["status"] == "delivered"
    assert len(recording.calls) == 1
    plain = decrypt(recording.calls[0][1], private, b64url_decode(auth))
    assert json.loads(plain)["title"] == "Morning briefing"
    assert notifier.publish(_notice(), quiet=False)[1]["status"] == "duplicate"
    assert len(recording.calls) == 1
    service.revoke(saved["id"], "revoke")
    assert notifier.publish(_notice("2026-10-03"), quiet=False)[1]["status"] == "delivered"
    assert len(recording.calls) == 1


def test_the_http_sender_builds_a_request_on_a_fake_transport(tmp_path):
    store = Store(tmp_path, password="fixture-only", clock=lambda: datetime(2026, 10, 2, tzinfo=UTC))
    private, p256dh, auth_b64 = _subscriber()
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["encoding"] = request.headers["content-encoding"]
        seen["body"] = request.content
        return httpx.Response(201)

    service = PushService(store, HttpPushSender(httpx.MockTransport(handler)), tmp_path / "key.pem")
    service.save(ENDPOINT, p256dh, auth_b64, "sub")
    assert service.dispatch({"title": "Morning briefing", "body": "1 open task."}) == 1
    assert seen["url"] == ENDPOINT
    assert seen["auth"].startswith("vapid t=")
    assert seen["encoding"] == "aes128gcm"
    plain = decrypt(seen["body"], private, b64url_decode(auth_b64))
    assert json.loads(plain)["title"] == "Morning briefing"

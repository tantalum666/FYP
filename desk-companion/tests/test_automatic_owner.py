"""Passwordless local entry keeps network, session and action authority boundaries."""

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app


HEADERS = {"X-Desk-Request": "1", "Origin": "http://127.0.0.1:8891"}


def local_client(tmp_path, *, peer="127.0.0.1"):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    return TestClient(app, base_url="http://127.0.0.1:8891", client=(peer, 40000))


def test_direct_workspace_opens_without_password_and_reuses_expiring_cookie(tmp_path, monkeypatch):
    monkeypatch.delenv("DESK_AUTO_OWNER", raising=False)
    client = local_client(tmp_path)
    assert client.get("/api/session").status_code == 401
    assert client.post("/api/session/connect").status_code == 403
    response = client.post("/api/session/connect", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["principal"] == {"kind": "owner", "id": "owner", "name": "Owner"}
    assert response.json()["automatic_owner"] is True
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Max-Age=28800" in cookie
    token = client.cookies.get("desk_companion_session_p8891")
    assert client.get("/api/workspace").status_code == 200
    assert client.get("/api/permissions").json()["mode"] == "ask"
    assert client.post("/api/session/connect", headers=HEADERS).status_code == 200
    assert client.cookies.get("desk_companion_session_p8891") == token


def test_expiry_recovers_owner_identity_without_authorizing_an_operation(tmp_path):
    client = local_client(tmp_path)
    client.post("/api/session/connect", headers=HEADERS)
    old = client.cookies.get("desk_companion_session_p8891")
    store = client.app.state.runtime.store
    with store.connection(write=True) as connection:
        connection.execute("UPDATE sessions SET expires='2000-01-01T00:00:00+00:00'")
        before = connection.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
    assert client.get("/api/session").status_code == 401
    response = client.post("/api/session/connect", headers=HEADERS)
    assert response.status_code == 200
    assert client.cookies.get("desk_companion_session_p8891") != old
    assert response.json()["principal"]["id"] == "owner"
    with store.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == before


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://foreign.example"},
        {"Origin": "capacitor://localhost"},
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Forwarded-Host": "localhost"},
        {"Forwarded": "for=127.0.0.1"},
        {"Host": "foreign.example"},
    ],
)
def test_remote_or_forwarded_request_cannot_bootstrap_owner(tmp_path, headers):
    client = local_client(tmp_path)
    response = client.post("/api/session/connect", headers={**HEADERS, **headers})
    assert response.status_code in (400, 403)
    assert client.get("/api/workspace").status_code == 401
    with client.app.state.runtime.store.connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


def test_public_deployment_and_explicit_disable_never_mint_owner_cookie(tmp_path, monkeypatch):
    client = local_client(tmp_path / "remote", peer="192.168.1.2")
    assert client.post("/api/session/connect", headers=HEADERS).status_code == 403
    monkeypatch.setenv("DESK_PUBLIC_ORIGIN", "https://desk.example")
    client = local_client(tmp_path / "public")
    assert client.post("/api/session/connect", headers=HEADERS).status_code == 403
    monkeypatch.delenv("DESK_PUBLIC_ORIGIN")
    monkeypatch.setenv("DESK_AUTO_OWNER", "0")
    client = local_client(tmp_path / "disabled")
    assert client.post("/api/session/connect", headers=HEADERS).status_code == 403


def test_native_loopback_bridge_can_connect_without_web_origin(tmp_path):
    client = local_client(tmp_path)
    assert client.post("/api/session/connect", headers={"X-Desk-Request": "1"}).status_code == 200


def test_production_media_policy_allows_only_same_origin_devices(tmp_path):
    # Vite previews do not exercise the production HTML response middleware.
    response = local_client(tmp_path).get("/api/health")
    policy = response.headers["permissions-policy"]
    assert "camera=(self)" in policy and "microphone=(self)" in policy
    assert "geolocation=(self)" in policy and "*" not in policy

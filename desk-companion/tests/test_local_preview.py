import pytest
from fastapi.testclient import TestClient
from desk.app import create_app

HEADERS = {"X-Desk-Request": "1"}


def client(tmp_path, **kwargs):
    return TestClient(
        create_app(tmp_path, password="fixture-only", scheduler=False),
        base_url="http://127.0.0.1:8831",
        client=("127.0.0.1", 40000),
        **kwargs,
    )


def test_preview_is_explicit_and_password_login_still_works(tmp_path, monkeypatch):
    monkeypatch.delenv("DESK_LOCAL_PREVIEW", raising=False)
    c = client(tmp_path)
    assert c.get("/api/session-mode").json() == {"local_preview": False}
    assert c.post("/api/session/preview", headers=HEADERS).status_code == 403
    assert c.get("/api/workspace").status_code == 401
    assert (
        c.post(
            "/api/session", headers=HEADERS, json={"username": "owner", "password": "fixture-only"}
        ).status_code
        == 200
    )
    assert c.get("/api/session").json()["principal"]["kind"] == "owner"


def test_loopback_preview_uses_real_expiring_owner_session(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_LOCAL_PREVIEW", "1")
    c = client(tmp_path)
    assert c.get("/api/session-mode").json()["local_preview"] is True
    assert c.post("/api/session/preview").status_code == 403
    response = c.post("/api/session/preview", headers=HEADERS)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Max-Age=28800" in cookie and "SameSite=strict" in cookie
    assert c.get("/api/session").json()["principal"]["kind"] == "owner"
    assert c.get("/api/workspace").status_code == 200
    token = c.cookies.get("desk_companion_session")
    assert c.post("/api/session/preview", headers=HEADERS).status_code == 200
    assert c.cookies.get("desk_companion_session") == token
    assert c.delete("/api/session", headers=HEADERS).status_code == 200
    assert c.get("/api/workspace").status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://foreign.example"},
        {"Origin": "capacitor://localhost"},
        {"X-Forwarded-For": "192.168.1.8"},
        {"X-Forwarded-Host": "public.example"},
        {"Forwarded": "for=192.168.1.8"},
    ],
)
def test_untrusted_or_forwarded_preview_denied(tmp_path, monkeypatch, headers):
    monkeypatch.setenv("DESK_LOCAL_PREVIEW", "1")
    monkeypatch.setenv("DESK_NATIVE_CLIENTS", "1")
    c = client(tmp_path)
    assert c.post("/api/session/preview", headers={**HEADERS, **headers}).status_code == 403
    assert c.get("/api/workspace").status_code == 401


def test_non_loopback_client_and_public_mode_denied(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_LOCAL_PREVIEW", "1")
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    c = TestClient(app, base_url="http://127.0.0.1:8831", client=("192.168.1.2", 40000))
    assert c.post("/api/session/preview", headers=HEADERS).status_code == 403
    monkeypatch.setenv("DESK_PUBLIC_ORIGIN", "https://desk.example")
    c = client(tmp_path)
    assert c.get("/api/session-mode").json()["local_preview"] is False
    assert c.post("/api/session/preview", headers=HEADERS).status_code == 403

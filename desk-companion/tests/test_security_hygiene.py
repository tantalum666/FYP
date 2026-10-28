import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.cookies import cookie_secure
from desk.private_file import write_private
from desk.runtime import Runtime
from desk.store import Store


def test_secret_files_are_created_0600_before_chmod(tmp_path, monkeypatch):
    created = []
    real_open = os.open

    def spy(path, flags, *args, **kwargs):
        name = os.path.basename(os.fspath(path))
        if args and flags & os.O_CREAT and name in {
            "credentials.json",
            "agent.json",
            "vault.key",
            "desk.sqlite3",
        }:
            created.append((name, args[0] & 0o777))
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", spy)
    previous = os.umask(0)
    try:
        Runtime(Store(tmp_path / "runtime"))
    finally:
        os.umask(previous)
    assert {name for name, _ in created} == {
        "credentials.json",
        "agent.json",
        "vault.key",
        "desk.sqlite3",
    }
    assert {mode for _, mode in created} == {0o600}
    for name in ("credentials.json", "agent.json", "vault.key", "desk.sqlite3"):
        assert (tmp_path / "runtime" / name).stat().st_mode & 0o777 == 0o600


def test_write_private_does_not_replace_a_symlink_target(tmp_path):
    target = tmp_path / "target"
    target.write_text("keep")
    link = tmp_path / "secret"
    link.symlink_to(target)
    with pytest.raises(OSError):
        write_private(link, "leaked")
    assert target.read_text() == "keep"


def test_https_public_origin_marks_session_cookie_secure(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_PUBLIC_ORIGIN", "https://desk.example")
    app = create_app(tmp_path / "https", password="fixture-only", scheduler=False)
    with TestClient(app) as client:
        response = client.post(
            "/api/session",
            headers={"X-Desk-Request": "1"},
            json={"username": "owner", "password": "fixture-only"},
        )
    cookie = response.headers["set-cookie"]
    assert response.status_code == 200
    assert "Secure" in cookie and "HttpOnly" in cookie
    assert "samesite=strict" in cookie.casefold()


def test_plain_http_without_public_origin_omits_secure(tmp_path, monkeypatch):
    monkeypatch.delenv("DESK_PUBLIC_ORIGIN", raising=False)
    app = create_app(tmp_path / "http", password="fixture-only", scheduler=False)
    with TestClient(app) as client:
        response = client.post(
            "/api/session",
            headers={"X-Desk-Request": "1"},
            json={"username": "owner", "password": "fixture-only"},
        )
    assert response.status_code == 200
    assert "Secure" not in response.headers["set-cookie"]


def test_cookie_secure_helper_matches_the_proxy_case(monkeypatch):
    class Request:
        class url:
            scheme = "http"

    monkeypatch.delenv("DESK_PUBLIC_ORIGIN", raising=False)
    assert cookie_secure(Request()) is False
    monkeypatch.setenv("DESK_PUBLIC_ORIGIN", "https://desk.example")
    assert cookie_secure(Request()) is True
    text = Path("backend/desk/device_routes.py").read_text(encoding="utf-8")
    assert "cookie_secure(request)" in text
    assert 'request.url.scheme == "https"' not in text


def test_failed_login_does_not_echo_the_password(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    with TestClient(app) as client:
        response = client.post(
            "/api/session",
            headers={"X-Desk-Request": "1"},
            json={"username": "owner", "password": "not-the-real-secret"},
        )
    assert response.status_code == 401
    assert "not-the-real-secret" not in response.text
    assert response.json()["error"]["code"] == "INVALID_LOGIN"


def test_default_origin_and_host_stay_closed(tmp_path, monkeypatch):
    monkeypatch.delenv("DESK_NATIVE_CLIENTS", raising=False)
    monkeypatch.delenv("DESK_PUBLIC_ORIGIN", raising=False)
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    with TestClient(app) as client:
        denied = client.get("/api/health", headers={"Origin": "https://evil.example"})
        foreign = client.get("/api/health", headers={"Host": "evil.example"})
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ORIGIN_NOT_ALLOWED"
    assert "access-control-allow-origin" not in {key.casefold() for key in denied.headers}
    assert foreign.status_code == 400


def test_dev_server_does_not_write_access_logs():
    script = Path("scripts/dev.sh").read_text()
    assert "--host 127.0.0.1" in script
    assert "--no-access-log" in script

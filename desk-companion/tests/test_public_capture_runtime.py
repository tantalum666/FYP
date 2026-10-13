"""App wiring only: synthetic stores and no public-network transport."""

import socket

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.store import DomainError


def sign_in(client):
    response = client.post(
        "/api/session",
        headers={"X-Desk-Request": "1"},
        json={"username": "owner", "password": "fixture-only"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("setting", [None, "0", "true", "yes", ""])
def test_capture_is_disabled_without_exact_opt_in(tmp_path, monkeypatch, setting):
    if setting is None:
        monkeypatch.delenv("DESK_PUBLIC_CAPTURE_ENABLED", raising=False)
    else:
        monkeypatch.setenv("DESK_PUBLIC_CAPTURE_ENABLED", setting)
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    assert app.state.runtime.public_captures.enabled is False
    assert app.state.runtime.public_captures._thread is None
    with TestClient(app) as client:
        assert client.get("/api/public-research/capabilities").status_code == 403
        sign_in(client)
        assert client.get("/api/public-research/capabilities").json() == {
            "enabled": False, "history_limit": 200, "source_cleanup": False,
        }


def test_explicit_false_overrides_environment_and_starts_no_worker(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_PUBLIC_CAPTURE_ENABLED", "1")
    app = create_app(
        tmp_path, password="fixture-only", scheduler=False, public_capture_enabled=False,
    )
    assert not app.state.runtime.public_captures.enabled
    with TestClient(app):
        assert app.state.runtime.public_captures._thread is None


@pytest.mark.parametrize("value", [0, 1, "1", "true", [], {}])
def test_non_boolean_explicit_capability_fails_before_store(tmp_path, value):
    root = tmp_path / "not-created"
    with pytest.raises(DomainError, match="CAPTURE_CAPABILITY_INVALID"):
        create_app(root, scheduler=False, public_capture_enabled=value)
    assert not root.exists()


def test_preparation_is_local_and_route_boundary_is_preserved(tmp_path, monkeypatch):
    app = create_app(
        tmp_path, password="fixture-only", scheduler=False, public_capture_enabled=True,
    )

    def no_dns(*args, **kwargs):
        pytest.fail("Preparing a review must not resolve or connect")

    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    payload = {"url": "https://example.com/public", "retain_capture_record": True}
    with TestClient(app) as client:
        sign_in(client)
        assert client.post("/api/public-research/captures", json=payload).status_code == 403
        headers = {"X-Desk-Request": "1", "X-Operation-Id": "capture-runtime-prepare"}
        assert client.post(
            "/api/public-research/captures", json=payload,
            headers={**headers, "Origin": "https://unapproved.invalid"},
        ).status_code == 403
        response = client.post("/api/public-research/captures", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["capture"]["state"] == "review"
        assert response.json()["capture"]["dispatch_possible"] is False
        assert app.state.runtime.public_captures._thread is None


@pytest.mark.parametrize("scheduler", [False, True])
def test_lifespan_owns_explicit_start_and_stop(tmp_path, monkeypatch, scheduler):
    app = create_app(
        tmp_path, password="fixture-only", scheduler=scheduler, public_capture_enabled=True,
    )
    runtime = app.state.runtime
    calls = []
    monkeypatch.setattr(runtime.public_captures, "start", lambda: calls.append("start"))
    monkeypatch.setattr(runtime.public_captures, "stop", lambda: calls.append("stop"))
    for service, method in (
        (runtime, "tick"), (runtime.responsibilities, "advance"),
        (runtime.data, "poll_weather"), (runtime.text_ai, "enrich_one"),
        (runtime.jobs, "run_one"), (runtime.agent_runs, "advance_one"),
        (runtime.browser_jobs, "advance_one"), (runtime.connectors, "advance_one"),
    ):
        monkeypatch.setattr(service, method, lambda: None)
    with TestClient(app):
        assert calls == (["start"] if scheduler else [])
    assert calls == (["start", "stop"] if scheduler else ["stop"])


def test_capture_stop_failure_does_not_skip_other_service_shutdown(tmp_path, monkeypatch):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    runtime, stopped = app.state.runtime, []

    def failure():
        raise RuntimeError("synthetic capture stop failure")

    monkeypatch.setattr(runtime.public_captures, "stop", failure)
    for name in ("agent_runs", "browser_jobs", "connectors", "jobs"):
        monkeypatch.setattr(
            getattr(runtime, name), "shutdown", lambda name=name: stopped.append(name),
        )
    with pytest.raises(RuntimeError, match="synthetic capture stop failure"):
        with TestClient(app):
            pass
    assert stopped == ["agent_runs", "browser_jobs", "connectors", "jobs"]

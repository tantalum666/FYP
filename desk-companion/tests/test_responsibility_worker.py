"""Actual app lifespan boundaries, with all unrelated workers replaced locally."""

from threading import Event

from fastapi.testclient import TestClient

from desk.app import create_app


def mute_unrelated_workers(monkeypatch, runtime):
    for service, method in (
        (runtime.data, "poll_weather"),
        (runtime.text_ai, "enrich_one"),
        (runtime.jobs, "run_one"),
        (runtime.agent_runs, "advance_one"),
        (runtime.browser_jobs, "advance_one"),
        (runtime.connectors, "advance_one"),
    ):
        monkeypatch.setattr(service, method, lambda: None)


def test_watch_worker_failure_cannot_stop_rules_and_recovers(tmp_path, monkeypatch):
    app = create_app(tmp_path, password="fixture-only", scheduler=True)
    runtime = app.state.runtime
    mute_unrelated_workers(monkeypatch, runtime)
    failed, recovered, rules_ran = Event(), Event(), Event()
    calls = []

    def advance():
        calls.append(1)
        if len(calls) == 1:
            failed.set()
            raise RuntimeError("Synthetic watch failure")
        recovered.set()

    monkeypatch.setattr(runtime.responsibilities, "advance", advance)
    monkeypatch.setattr(runtime, "tick", rules_ran.set)
    with TestClient(app):
        assert failed.wait(3)
        assert rules_ran.wait(3)
        assert recovered.wait(4)
    assert len(calls) >= 2
    assert runtime.worker_health["responsibilities"] == "ready"
    assert runtime.worker_health["rules"] == "ready"


def test_disabled_scheduler_never_advances_watches_or_legacy_tick(tmp_path, monkeypatch):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    runtime = app.state.runtime
    calls = []
    monkeypatch.setattr(runtime.responsibilities, "advance", lambda: calls.append("watch"))
    with TestClient(app) as client:
        assert client.get("/api/responsibilities").status_code == 403
        runtime.tick()
    assert calls == []
    assert runtime.worker_health == {}

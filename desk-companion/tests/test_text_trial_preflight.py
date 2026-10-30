"""Offline fixtures only. Never exercise a provider, credentials or real runtime."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
import pytest

from desk import text_trial_preflight as trial
from desk.text_ai import TextAssistant, TextConfig, TextPlan
from desk.store import DomainError

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_text_trial.py"
QWEN = "https://synthetic.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/chat/completions"


def preview(provider="gemini", **kwargs):
    return trial.offline_preflight(
        provider=provider,
        model=kwargs.get("model", "fixture-model"),
        endpoint=kwargs.get("endpoint", QWEN if provider == "qwen" else ""),
    )


def load_script():
    spec = importlib.util.spec_from_file_location("text_trial_cli", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("provider", ["gemini", "qwen"])
def test_production_adapter_preview_with_no_network_credentials_or_runtime(monkeypatch, provider):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network, credentials or real runtime must not be accessed")

    monkeypatch.setattr(TextConfig, "environment", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "__init__", forbidden)
    monkeypatch.setattr(TextAssistant, "message", forbidden)
    monkeypatch.setenv("DESK_TEXT_API_KEY", "MUST_NOT_LEAK")
    monkeypatch.setenv("DESK_TEXT_MODEL", "MUST_NOT_USE")
    report = preview(provider)
    assert report["status"] == "offline_preflight_passed"
    assert report["live_acceptance"] == "not_run"
    assert report["network_requests"] == 0 and report["mock_requests"] == 1
    assert report["adapter_usage_rows"] == 1
    assert report["request"]["bytes"] <= trial.REQUEST_BYTES
    assert not report["plan_dispatched"] and not report["draft_persisted"]
    assert report["tasks_saved"] == 0
    assert "MUST_NOT" not in json.dumps(report)
    assert trial._FIXTURE_KEY not in json.dumps(report)
    assert report["limits"]["output_tokens_in_actual_payload"] == 1600
    TextPlan.model_validate(report["synthetic_plan"])
    payload = report["request"]["json"]
    if provider == "qwen":
        assert payload["max_tokens"] == 1600 and payload["stream"] is False
        user = payload["messages"][1]["content"]
    else:
        assert payload["generationConfig"]["maxOutputTokens"] == 1600
        user = payload["contents"][0]["parts"][0]["text"]
    context = json.loads(user)
    assert context == trial.synthetic_context()
    assert len(context["tools"]) == 1
    assert context["tools"][0]["name"] == "task_create_draft"


@pytest.mark.parametrize(
    "provider,model,endpoint",
    [
        ("none", "fixture", ""),
        ("gemini", "", ""),
        ("gemini", "fixture?key=secret", ""),
        ("gemini", "fixture", "https://example.invalid"),
        ("qwen", "fixture", QWEN + "?key=secret"),
        ("qwen", "fixture", ""),
        ("qwen_audio", "fixture", QWEN),
    ],
)
def test_invalid_target_rejected_before_transport(monkeypatch, provider, model, endpoint):
    monkeypatch.setattr(
        trial._OfflineCapture, "handle_request", lambda *_: pytest.fail("transport")
    )
    with pytest.raises(ValueError, match="TRIAL_INVALID_PREVIEW_TARGET"):
        trial.offline_preflight(provider=provider, model=model, endpoint=endpoint)


def test_extra_request_is_denied_by_transport_without_another_fixture_response(monkeypatch):
    capture = trial._OfflineCapture(TextConfig("gemini", "fixture", ""))
    calls = []
    original = trial._fixture_body
    monkeypatch.setattr(
        trial, "_fixture_body", lambda provider: calls.append(provider) or original(provider)
    )
    payload = preview()["request"]["json"]
    request = httpx.Request("POST", capture.url, json=payload)
    capture.handle_request(request)
    with pytest.raises(ValueError, match="TRIAL_REQUEST_LIMIT"):
        capture.handle_request(request)
    assert len(calls) == 2
    assert capture.attempts == 2


@pytest.mark.parametrize(
    "mutate",
    [
        lambda body: body["generationConfig"].pop("maxOutputTokens"),
        lambda body: body["generationConfig"].update(maxOutputTokens=1601),
        lambda body: body["generationConfig"].update(maxOutputTokens="1600"),
    ],
)
def test_actual_cap_drift_is_not_reported_as_safe(mutate):
    payload = preview()["request"]["json"]
    mutate(payload)
    capture = trial._OfflineCapture(TextConfig("gemini", "fixture", ""))
    with pytest.raises(ValueError, match="TRIAL_OUTPUT_LIMIT_OR_PROTOCOL_CHANGED"):
        capture.handle_request(httpx.Request("POST", capture.url, json=payload))
    assert capture.payload is None


@pytest.mark.parametrize("mutation", ["cap", "stream", "thinking", "model"])
def test_qwen_actual_protocol_drift_is_denied(mutation):
    payload = preview("qwen")["request"]["json"]
    changes = {
        "cap": ("max_tokens", 9999),
        "stream": ("stream", True),
        "thinking": ("enable_thinking", True),
        "model": ("model", "different"),
    }
    key, value = changes[mutation]
    payload[key] = value
    capture = trial._OfflineCapture(TextConfig("qwen", "fixture-model", QWEN))
    with pytest.raises(ValueError, match="TRIAL_OUTPUT_LIMIT_OR_PROTOCOL_CHANGED"):
        capture.handle_request(httpx.Request("POST", capture.url, json=payload))


@pytest.mark.parametrize("kind", ["size", "url", "method"])
def test_size_method_and_destination_limits(kind):
    capture = trial._OfflineCapture(TextConfig("gemini", "fixture", ""))
    request = httpx.Request(
        "GET" if kind == "method" else "POST",
        "https://example.invalid" if kind == "url" else capture.url,
        content=b"x" * (trial.REQUEST_BYTES + 1) if kind == "size" else b"{}",
    )
    with pytest.raises(ValueError):
        capture.handle_request(request)
    assert capture.payload is None


@pytest.mark.parametrize(
    "arguments",
    [
        {"title": "Another task", "timezone": "UTC", "follow_up_enabled": False},
        {"title": trial.SYNTHETIC_TITLE, "timezone": "UTC"},
        {"title": trial.SYNTHETIC_TITLE, "timezone": "UTC", "follow_up_enabled": True},
        {"title": trial.SYNTHETIC_TITLE, "timezone": "UTC", "follow_up_enabled": 0},
        {
            "title": trial.SYNTHETIC_TITLE,
            "timezone": "UTC",
            "follow_up_enabled": False,
            "approved": True,
        },
    ],
)
def test_plan_scope_is_exact_and_never_dispatched(arguments):
    plan = TextPlan(message="Needs review", tool="task_create_draft", arguments=arguments)
    with pytest.raises(ValueError):
        trial.validate_trial_plan(plan)


@pytest.mark.parametrize(
    "tool", ["none", "computer_job_draft", "task_change_draft", "memory_create"]
)
def test_other_tools_are_rejected(tool):
    with pytest.raises(ValueError):
        trial.validate_trial_plan(TextPlan(message="No", tool=tool))


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"candidates": []},
        {"candidates": [{"content": {"parts": [{"text": "not JSON"}]}}]},
        {"candidates": [{"content": {"parts": [{"text": "x" * 140000}]}}]},
    ],
)
def test_bad_fixture_response_fails_one_attempt_no_retry(monkeypatch, response):
    calls = []
    monkeypatch.setattr(trial, "_fixture_body", lambda provider: calls.append(provider) or response)
    with pytest.raises(DomainError):
        preview()
    assert calls == ["gemini"]


def test_cli_child_environment_is_empty_and_python_is_isolated(monkeypatch):
    cli = load_script()
    seen = {}

    def run(command, **kwargs):
        seen.update(command=command, **kwargs)
        return subprocess.CompletedProcess(command, 0, b'{"status":"offline_preflight_passed"}')

    monkeypatch.setattr(cli.subprocess, "run", run)
    monkeypatch.setenv("DESK_TEXT_API_KEY", "PRIVATE")
    assert cli.main(["--provider", "gemini", "--model", "fixture", "--endpoint", ""]) == 0
    assert seen["env"] == {} and seen["command"][1] == "-I"
    assert seen["stdin"] == subprocess.DEVNULL and seen["timeout"] == 45
    assert "PRIVATE" not in repr(seen)


def test_actual_watchdog_kills_and_reaps_blocked_worker(tmp_path):
    cli = load_script()
    pidfile = tmp_path / "pid"
    command = [
        sys.executable,
        "-I",
        "-c",
        f"import os,time,pathlib; pathlib.Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(60)",
    ]
    start = time.monotonic()
    result, code = cli._supervise(command, timeout=0.5)
    assert code == 1 and result["status"] == "offline_preflight_timeout"
    assert time.monotonic() - start < 5
    pid = int(pidfile.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


@pytest.mark.parametrize("provider", ["qwen", "gemini"])
def test_real_cli_offline_child_ignores_inherited_secrets(provider):
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(SCRIPT),
            "--provider",
            provider,
            "--model",
            "fixture-model",
            "--endpoint",
            QWEN if provider == "qwen" else "",
        ],
        env={
            "DESK_TEXT_API_KEY": "MUST_NOT_LEAK",
            "DESK_TEXT_BACKGROUND": "1",
            "PYTHONPATH": "/invalid",
            "HTTPS_PROXY": "http://invalid.invalid",
        },
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["supervision"]["credential_environment_inherited"] is False
    assert report["status"] == "offline_preflight_passed"
    assert b"MUST_NOT_LEAK" not in result.stdout + result.stderr


def test_live_and_key_flags_rejected_without_echo():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--live", "--api-key", "MUST_NOT_ECHO"],
        env={},
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert b"MUST_NOT_ECHO" not in result.stdout + result.stderr


@pytest.mark.parametrize("status", [302, 401, 403, 429, 500])
def test_http_failure_no_follow_redirects_or_retry(monkeypatch, status):
    calls = []
    original = trial._OfflineCapture.handle_request

    def respond(self, request):
        calls.append(request)
        original(self, request)
        return httpx.Response(status, headers={"Location": "https://example.invalid"})

    monkeypatch.setattr(trial._OfflineCapture, "handle_request", respond)
    with pytest.raises(DomainError):
        preview()
    assert len(calls) == 1


def test_guard_fences_configuration_change_before_request(monkeypatch):
    original = TextAssistant.generate
    calls = []

    def changed(self, *args):
        self.config.model = "different-model"
        return original(self, *args)

    monkeypatch.setattr(TextAssistant, "generate", changed)
    monkeypatch.setattr(trial._OfflineCapture, "handle_request", lambda *_: calls.append(1))
    with pytest.raises(DomainError):
        preview()
    assert not calls


def test_oversize_actual_adapter_input_refused_without_fixture_response(monkeypatch):
    monkeypatch.setattr(trial, "synthetic_context", lambda: {"oversized": "x" * 20000})
    monkeypatch.setattr(
        trial, "_fixture_body", lambda *_: pytest.fail("response must not be reached")
    )
    with pytest.raises(DomainError):
        preview()


def test_fresh_in_memory_store_contains_no_real_user_tables(monkeypatch):
    stores = []
    original = trial._UsageStore

    class InspectStore(original):
        def __init__(self):
            super().__init__()
            assert self.db.execute("PRAGMA database_list").fetchall() == [(0, "main", "")]
            stores.append(self)

    monkeypatch.setattr(trial, "_UsageStore", InspectStore)
    preview()
    preview()
    assert len(stores) == 2 and stores[0] is not stores[1]
    import sqlite3

    for store in stores:
        with pytest.raises(sqlite3.ProgrammingError):
            store.db.execute("SELECT 1")

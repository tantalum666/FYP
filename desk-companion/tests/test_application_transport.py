"""Transport changes must preserve approval scope and fixed local invocation."""

import hashlib
import json

import pytest

from desk.application_executor import ApplicationExecutor
from desk.application_runtime import ApplicationBridge
from desk.computer import ExecutionRejected
from desk.store import encode


@pytest.mark.parametrize("engine", ["docker", "podman"])
def test_fixed_local_transport_excludes_remote_and_provider_environment(monkeypatch, engine):
    monkeypatch.setenv("DESK_APP_ENGINE", engine)
    monkeypatch.setenv("DESK_APP_DOCKER_CONTEXT", "fyp-apps")
    monkeypatch.setenv("DESK_APP_CONTAINER", "desk-applications")
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    for name in ("CONTAINER_HOST", "CONTAINER_CONNECTION", "DOCKER_HOST", "OPENAI_API_KEY"):
        monkeypatch.setenv(name, "must-not-reach-executor")
    calls = []

    class Process:
        returncode = 0

        def __init__(self, command, **kwargs):
            calls.append((command, kwargs))

        def communicate(self, input, timeout):
            assert json.loads(input) == {"mode": "browser", "source_id": "$(untrusted).html"}
            return b'{"text":"observed"}', b""

    monkeypatch.setattr("desk.application_runtime.subprocess.Popen", Process)
    result = ApplicationBridge().run({"mode": "browser", "source_id": "$(untrusted).html"})
    assert result == {"text": "observed"}
    command, options = calls[0]
    prefix = (
        ["docker", "--context", "fyp-apps"] if engine == "docker" else ["podman", "--remote=false"]
    )
    assert command == prefix + [
        "exec",
        "-i",
        "--user",
        "desk",
        "desk-applications",
        "timeout",
        "--kill-after=2s",
        "35s",
        "python3",
        "/opt/desk/application_bridge.py",
    ]
    assert options["env"]["XDG_RUNTIME_DIR"] == "/run/user/1000"
    assert "must-not-reach-executor" not in options["env"].values()


@pytest.mark.parametrize(
    "engine,context,container",
    [
        ("ssh", "fyp", "desk"),
        ("podman; sh", "", "desk"),
        ("docker", "", "desk"),
        ("podman", "", "--privileged"),
    ],
)
def test_invalid_transport_never_launches(monkeypatch, engine, context, container):
    monkeypatch.setenv("DESK_APP_ENGINE", engine)
    monkeypatch.setenv("DESK_APP_DOCKER_CONTEXT", context)
    monkeypatch.setenv("DESK_APP_CONTAINER", container)
    # Leading '-' currently matches the legacy name grammar; reject it at the
    # configuration boundary instead of letting a container CLI parse an option.
    bridge = ApplicationBridge()
    with pytest.raises(ExecutionRejected):
        bridge.run({})


def test_docker_receipts_keep_scope_and_engine_change_invalidates_it(tmp_path, monkeypatch):
    monkeypatch.delenv("DESK_APP_ENGINE", raising=False)
    monkeypatch.setenv("DESK_APP_DOCKER_CONTEXT", "fyp-apps")
    monkeypatch.setenv("DESK_APP_CONTAINER", "desk-applications")
    old = ApplicationExecutor(tmp_path)
    legacy = {
        "root": str(old.root),
        "inputs": old.sources.fingerprint,
        "context": "fyp-apps",
        "container": "desk-applications",
    }
    assert old.scope == "applications:" + hashlib.sha256(encode(legacy).encode()).hexdigest()
    monkeypatch.setenv("DESK_APP_ENGINE", "podman")
    local = ApplicationExecutor(tmp_path)
    assert local.bridge.configured and local.scope != old.scope
    monkeypatch.setenv("DESK_APP_DOCKER_CONTEXT", "another-unrelated-context")
    assert ApplicationExecutor(tmp_path).scope == local.scope

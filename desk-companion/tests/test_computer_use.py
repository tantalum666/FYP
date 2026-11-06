"""New browser preparation uses existing jobs and never calls a real provider."""

import hashlib
import json
import struct
import zlib

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desk.app import create_app
from desk.browser_supervisor import WorkerOutcome
from desk.computer_use_files import write_file
from desk.computer_use_models import ComputerUseInput, SCREEN_WIDTH, SCREEN_HEIGHT
from desk.computer_use_protocol import OpenAIComputerProtocol, validate_actions
from desk.jobs import JobApproval, JobService
from desk.store import DomainError, encode
from desk.text_ai import TextConfig
from desk.permissions import PermissionChange


def png(width=SCREEN_WIDTH, height=SCREEN_HEIGHT):
    def chunk(name, data):
        return (
            struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\0" * width * 3) * height))
        + chunk(b"IEND", b"")
    )


class FakeSupervisor:
    executable = "/fixture/chromium"
    calls = 0
    cleanup = True

    def readiness(self):
        return None

    def run(self, payload, directory, checkpoint, *, on_observation, **kwargs):
        self.calls += 1
        checkpoint("computer_open")
        screen = png()
        write_file(directory, "screen-1.png", screen)
        observation = {
            "sequence": 1,
            "screen": "screen-1.png",
            "sha256": hashlib.sha256(screen).hexdigest(),
            "url": "http://127.0.0.1:8768",
            "title": "Fictional cart",
            "text": "Total HKD55.80; not ordered",
        }
        assert on_observation(observation)["finish"]
        write_file(directory, "browser-state.json", b'{"cookies":[],"origins":[]}')
        return WorkerOutcome(
            {
                "observation": observation,
                "outcome": "review_ready",
                "reason": "review_prepared_page",
                "demo_submissions": 0,
                "demo": True,
                "browser_version": "fixture",
                "network_boundary": "public_request_routing_only",
            },
            None,
            True,
            self.cleanup,
        )


@pytest.fixture
def world(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    r = app.state.runtime
    r.text_ai.config = TextConfig(
        "openai", "gpt-6.1-sol", "https://api.openai.com/v1/responses", "synthetic-key"
    )
    r.jobs.computer_use.enabled = True
    r.jobs.computer_use.supervisor = FakeSupervisor()
    r.text_ai.transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Review the cart."}],
                    }
                ],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )
    )
    c = TestClient(app)
    assert (
        c.post(
            "/api/session",
            json={"username": "owner", "password": "fixture"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    principal = {"kind": "owner", "id": "owner", "session": c.cookies.get("desk_companion_session")}
    return r, c, principal


def prepare(world, key="computer", **changes):
    r, _, principal = world
    data = dict(
        title="Prepare a cart",
        goal="Compare tissue prices",
        start_url="demo:shopping",
        public_only=True,
        share_screen=True,
        max_steps=2,
    )
    data.update(changes)
    return r.jobs.prepare(ComputerUseInput(**data), key, principal=principal)["job"]


def approve(r, job):
    detail = r.jobs.detail(job["id"], review=True)
    r.jobs.approve(
        job["id"],
        JobApproval(expected_version=detail["version"], intent_hash=detail["intent_hash"]),
        job["id"] + "/approve",
    )


def test_queue_approval_observation_and_portable_restore_do_not_replay_input(world):
    r, client, principal = world
    job = prepare(world)
    r.jobs.run_one()
    assert r.jobs.computer_use.supervisor.calls == 0
    approve(r, job)
    r.jobs.run_one()
    result = r.jobs.detail(job["id"], review=True)
    assert result["state"] == "succeeded" and result["result"]["quality"] == "not_goal_completion"
    assert result["result"]["readback"]["demo_submissions"] == 0
    assert not r.jobs.computer_use.blocker.exists()
    response = client.get("/api/computer/computer-use/jobs/" + job["id"] + "/screen")
    assert response.status_code == 200 and response.content == png()
    assert prepare(world)["id"] == job["id"]
    r.jobs.run_one()
    assert r.jobs.computer_use.supervisor.calls == 1
    bundle = JobService.validate_backup(r.jobs.export())
    assert bundle["jobs"][0]["request"]["session_hash"] != principal["session"]
    assert "cookies" not in encode(bundle)


def test_expired_owner_fences_queued_computer_work(world):
    r, _, _ = world
    job = prepare(world)
    approve(r, job)
    with r.store.connection(write=True) as conn:
        conn.execute("UPDATE sessions SET expires='2000-01-01'")
    r.jobs.run_one()
    assert r.jobs.detail(job["id"])["error"] == "RUN_SESSION_EXPIRED"
    assert r.jobs.computer_use.supervisor.calls == 0


def test_full_permission_only_applies_to_new_explicit_screen_requests(world):
    r, client, _ = world
    body = ComputerUseInput(
        title="Public browser",
        goal="Read the public page",
        start_url="demo:shopping",
        share_screen=True,
        public_only=True,
    ).model_dump()
    headers = {"X-Desk-Request": "1", "X-Operation-Id": "before-full"}
    original = client.post("/api/computer/computer-use/jobs", json=body, headers=headers)
    assert original.status_code == 200 and original.json()["job"]["state"] == "review"
    policy = r.permissions.snapshot()
    r.permissions.change(PermissionChange(mode="full", expected_version=policy["version"]), "full")
    repeated = client.post("/api/computer/computer-use/jobs", json=body, headers=headers)
    assert repeated.json()["job"]["state"] == "review"
    current = client.post(
        "/api/computer/computer-use/jobs",
        json=body,
        headers={**headers, "X-Operation-Id": "after-full"},
    )
    assert current.status_code == 200 and current.json()["job"]["state"] == "queued"
    refused = client.post(
        "/api/computer/computer-use/jobs",
        json={**body, "share_screen": False},
        headers={**headers, "X-Operation-Id": "no-screen"},
    )
    assert refused.status_code == 422


def test_portable_browser_job_is_read_only_after_restore(world, tmp_path):
    r, _, _ = world
    job = prepare(world)
    approve(r, job)
    r.jobs.run_one()
    bundle = JobService.validate_backup(r.jobs.export())
    other = create_app(tmp_path / "restored", password="fixture", scheduler=False).state.runtime
    with other.store.connection(write=True) as conn:
        other.jobs.restore(conn, bundle)
    restored = other.jobs.detail(job["id"], review=True)
    assert restored["state"] == "unknown" and restored["result"] is None
    with pytest.raises(DomainError, match="JOB_NOT_REVIEWABLE"):
        approve(other, restored)


def test_uncertain_cleanup_blocks_new_admission_and_is_not_reexecuted(world):
    r, _, _ = world
    r.jobs.computer_use.supervisor.cleanup = False
    job = prepare(world)
    approve(r, job)
    r.jobs.run_one()
    assert r.jobs.detail(job["id"])["state"] == "unknown"
    assert r.jobs.computer_use.blocker.exists()
    with pytest.raises(DomainError, match="COMPUTER_CLEANUP_REQUIRED"):
        prepare(world, "another")
    r.jobs.run_one()
    assert r.jobs.computer_use.supervisor.calls == 1


def test_continuation_binds_state_hash_and_same_destination(world):
    r, _, _ = world
    first = prepare(world)
    approve(r, first)
    r.jobs.run_one()
    with pytest.raises(DomainError, match="COMPUTER_SOURCE_CHANGED"):
        prepare(world, "wrong-site", source_job_id=first["id"], start_url="demo:flights")
    second = prepare(world, "continue", source_job_id=first["id"])
    state = r.jobs.computer_use.root / first["id"] / "browser-state.json"
    state.write_text('{"changed":true}')
    approve(r, second)
    r.jobs.run_one()
    assert r.jobs.detail(second["id"])["state"] == "failed"
    assert r.jobs.detail(second["id"])["error"] == "COMPUTER_SOURCE_CHANGED"


@pytest.mark.parametrize(
    "change",
    [
        {"share_screen": 1},
        {"share_screen": False},
        {"public_only": False},
        {"max_steps": 100},
        {"start_url": "file:///etc/passwd"},
    ],
)
def test_explicit_admission_cannot_be_coerced(change):
    data = dict(
        title="Test", goal="Read", start_url="demo:shopping", share_screen=True, public_only=True
    )
    with pytest.raises(ValidationError):
        ComputerUseInput(**(data | change))


@pytest.mark.parametrize(
    "action",
    [
        {"type": "click", "x": 1280, "y": 3, "button": "left"},
        {"type": "click", "x": True, "y": 3, "button": "left"},
        {"type": "keypress", "keys": ["CTRL", "V"]},
        {"type": "keypress", "keys": ["META", "L"]},
        {"type": "exec", "code": "arbitrary()"},
        {"type": "type", "text": "x" * 2001},
    ],
)
def test_actions_reject_wrong_coordinates_clipboard_and_code(action):
    with pytest.raises(ValueError):
        validate_actions([action])


def test_native_protocol_cannot_replay_duplicate_call_ids():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "computer_call",
                        "call_id": "same-call",
                        "actions": [{"type": "screenshot"}],
                        "status": "completed",
                    }
                ],
            },
        )

    p = OpenAIComputerProtocol(
        TextConfig("openai", "gpt-6.1-sol", "https://api.openai.com/v1/responses", "fake"),
        "Review",
        [],
        transport=httpx.MockTransport(handler),
    )
    observation = {"url": "https://public.example", "title": "Public", "sequence": 1}
    assert p.step(observation, png(), lambda: None)["actions"] == [{"type": "screenshot"}]
    with pytest.raises(ValueError, match="Repeated"):
        p.step(observation | {"sequence": 2}, png(), lambda: None)
    assert bodies[0]["tools"] == [{"type": "computer"}] and bodies[0]["store"] is False
    assert any(
        x.get("type") == "computer_call_output" and x["call_id"] == "same-call"
        for x in bodies[1]["input"]
    )

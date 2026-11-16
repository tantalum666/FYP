"""Agents wire/authority regressions; every request uses an offline transport."""

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desk.app import create_app
from desk.computer_use_models import ComputerUseInput, validate_computer_request
from desk.jobs import JobApproval, JobService
from desk.managed_browser_client import ManagedBrowserClient
from desk.store import DomainError, encode
from desk.text_ai import TextConfig


class Events(httpx.AsyncByteStream):
    def __init__(self, provider):
        self.provider = provider

    async def __aiter__(self):
        p = self.provider
        while not p.input:
            await asyncio.sleep(0.001)
        yield self.line(
            "agent.session.turn.item.added", item={"type": "computer_use_call", "id": "browser-1"}
        )
        while not p.approved or p.never_complete:
            await asyncio.sleep(0.001)
        yield self.line(
            "agent.session.turn.item.done", item={"type": "computer_use_call", "id": "browser-1"}
        )
        yield self.line("agent.session.turn.completed", turn={"id": "turn-1"})

    @staticmethod
    def line(kind, **data):
        return ("data: " + json.dumps({"type": kind, **data}) + "\n\n").encode()


class Provider:
    def __init__(self):
        self.calls, self.decisions = [], []
        self.input = self.approved = self.deleted = False
        self.origin = "https://books.toscrape.com"
        self.authentication = self.never_complete = self.delete_fails = self.create_uncertain = (
            False
        )
        self.on_read = None

    async def __call__(self, request):
        path = request.url.path
        body = json.loads(request.content) if request.content else {}
        self.calls.append((request.method, path, body))
        assert request.url.host == "api.openai.com"
        if request.method == "POST" and path.endswith("/sessions"):
            assert request.headers["Idempotency-Key"].endswith("/create")
            assert body["environment"]["network"] == {
                "access": "restricted",
                "allowed_domains": ["books.toscrape.com"],
            }
            assert body["agent"]["multi_agent"] == {"enabled": False}
            assert body["agent"]["tools"] == [{"type": "computer_use"}]
            if self.create_uncertain:
                raise httpx.ReadTimeout("No creation response", request=request)
            return httpx.Response(201, json={"id": "sess_fixture"})
        if request.method == "GET" and path.endswith("/events"):
            return httpx.Response(200, stream=Events(self))
        if request.method == "POST" and path.endswith("/events"):
            event = body["events"][0]
            if event["type"] == "agent.session.input.message":
                self.input = True
            elif event["type"].endswith("approval_request_result"):
                self.decisions.append(event["response"])
                self.approved = event["response"].get("decision") == "approve"
            return httpx.Response(202, json={"accepted": True})
        if request.method == "DELETE":
            self.deleted = not self.delete_fails
            return httpx.Response(200, json={"deleted": self.deleted})
        if path.endswith("/items"):
            return httpx.Response(
                200,
                json={
                    "has_more": False,
                    "data": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "phase": "commentary",
                            "status": "completed",
                            "content": [{"type": "output_text", "text": "I will look."}],
                        },
                        {
                            "type": "message",
                            "role": "assistant",
                            "phase": "final_answer",
                            "status": "completed",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "The first book costs GBP51.77. https://books.toscrape.com/",
                                }
                            ],
                        },
                    ],
                },
            )
        if self.deleted:
            return httpx.Response(404, json={"error": {"code": "not_found"}})
        if self.on_read:
            callback, self.on_read = self.on_read, None
            callback()
        required = (
            []
            if self.approved
            else [
                {
                    "type": "computer_use_approval_request",
                    "request_id": "approval-1",
                    "request": {"type": "browser_authentication"}
                    if self.authentication
                    else {"type": "browser_origin_access", "origin": self.origin},
                }
            ]
        )
        return httpx.Response(
            200, json={"status": "idle", "usage": None, "required_actions": required}
        )


class FastClient(ManagedBrowserClient):
    active_seconds = 0.25
    poll_seconds = 0.001


@pytest.fixture
def world(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    r = app.state.runtime
    r.text_ai.config = TextConfig(
        "openai", "gpt-6.1-sol", "https://api.openai.com/v1/responses", "synthetic-key"
    )
    provider = Provider()
    r.text_ai.transport = httpx.MockTransport(provider)
    r.jobs.managed_browser.enabled = True
    r.jobs.managed_browser.client_factory = FastClient
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    owner = {"kind": "owner", "session": client.cookies.get("desk_companion_session")}
    return r, provider, client, owner


def prepare(world, key="prepare"):
    r, _, _, owner = world
    return r.jobs.prepare(
        ComputerUseInput(
            engine="managed",
            title="Compare public books",
            goal="Compare two public book prices",
            start_url="https://books.toscrape.com/",
            public_only=True,
            share_screen=True,
        ),
        key,
        principal=owner,
    )["job"]


def approve(r, job):
    detail = r.jobs.detail(job["id"], review=True)
    r.jobs.approve(
        job["id"],
        JobApproval(expected_version=detail["version"], intent_hash=detail["intent_hash"]),
        job["id"] + "/approve",
    )


def result(world, job):
    return world[0].jobs.detail(job["id"], review=True)


def test_approved_job_gets_one_final_report_and_confirmed_deletion(world):
    r, provider, client, _ = world
    job = prepare(world)
    r.jobs.run_one()
    assert provider.calls == []
    approve(r, job)
    r.jobs.run_one()
    done = result(world, job)
    assert done["state"] == "succeeded"
    assert done["result"]["quality"] == "not_goal_completion"
    report = done["result"]["readback"]
    assert report["report"].startswith("The first book") and "I will look" not in report["report"]
    assert report["activity_count"] == 1 and report["cost_receipt"] == "unknown"
    assert report["session_deletion_confirmed"] and report["resumable"] is False
    assert not r.jobs.managed_browser.blocker.exists()
    assert client.get(f"/api/computer/computer-use/jobs/{job['id']}/screen").status_code == 404
    count = len(provider.calls)
    assert prepare(world)["id"] == job["id"]
    r.jobs.run_one()
    assert len(provider.calls) == count  # No replay on retry or polling.
    bundle = JobService.validate_backup(r.jobs.export())
    assert bundle["jobs"][0]["request"]["executor"] == "managed_public_browser_v1"
    raw = r.jobs.managed_browser.root / job["id"] / "managed-result.json"
    raw.write_text(raw.read_text().replace("GBP51.77", "GBP0.00"))
    assert r.jobs.managed_browser.verify(done["request"])["verified"] is False


def test_expired_owner_never_creates_a_managed_session(world):
    r, provider, _, _ = world
    job = prepare(world)
    approve(r, job)
    with r.store.connection(write=True) as conn:
        conn.execute("UPDATE sessions SET expires='2000-01-01'")
    r.jobs.run_one()
    assert result(world, job)["error"] == "RUN_SESSION_EXPIRED"
    assert provider.calls == []


@pytest.mark.parametrize("kind", ["origin", "authentication"])
def test_unadmitted_origin_and_auth_are_never_auto_approved(world, kind):
    r, provider, _, _ = world
    provider.origin = "https://not-admitted.example"
    provider.authentication = kind == "authentication"
    job = prepare(world)
    approve(r, job)
    r.jobs.run_one()
    assert result(world, job)["state"] == "failed"
    assert result(world, job)["error"] == "COMPUTER_MANAGED_OWNER_REQUIRED"
    assert provider.deleted
    assert provider.decisions == (
        [{"type": "browser_authentication", "action": "cancel"}]
        if kind == "authentication"
        else [{"type": "browser_origin_access", "decision": "deny"}]
    )


def test_cancel_during_running_sends_cancel_and_deletes_without_publishing(world):
    r, provider, _, _ = world
    job = prepare(world)
    approve(r, job)
    provider.on_read = lambda: r.jobs.cancel(job["id"], "owner-stop")
    r.jobs.run_one()
    assert result(world, job)["state"] == "cancelled"
    assert result(world, job)["result"] is None
    assert provider.deleted
    assert any(
        c[2].get("events", [{}])[0].get("type") == "agent.session.input.cancel"
        for c in provider.calls
    )
    assert not r.jobs.managed_browser.blocker.exists()


def test_idle_snapshot_without_terminal_event_is_not_success(world):
    r, provider, _, _ = world
    provider.never_complete = True
    job = prepare(world)
    approve(r, job)
    r.jobs.run_one()
    assert result(world, job)["state"] == "failed"
    assert result(world, job)["error"] == "JOB_DEADLINE_EXCEEDED"
    assert provider.deleted


@pytest.mark.parametrize("failure", ["delete_fails", "create_uncertain"])
def test_uncertain_remote_resources_block_new_work_and_never_repeat_creation(world, failure):
    r, provider, _, _ = world
    setattr(provider, failure, True)
    job = prepare(world)
    approve(r, job)
    r.jobs.run_one()
    assert result(world, job)["state"] == "unknown"
    assert r.jobs.managed_browser.blocker.exists()
    with pytest.raises(DomainError, match="COMPUTER_CLEANUP_REQUIRED"):
        prepare(world, "again")
    r.jobs.run_one()
    assert len([c for c in provider.calls if c[0] == "POST" and c[1].endswith("/sessions")]) == 1


def test_managed_requires_explicit_engine_and_does_not_relabel_legacy_intents(world):
    job = prepare(world)
    request = result(world, job)["request"]
    original = {**request, "executor": "public_browser_computer_v1"}
    original.pop("engine")
    before = encode(original)
    assert encode(validate_computer_request(original)) == before
    with pytest.raises(ValueError, match="environment"):
        validate_computer_request({**request, "engine": "local"})
    with pytest.raises(ValidationError):
        ComputerUseInput(
            engine="managed",
            title="No local fixture",
            goal="Read",
            start_url="demo:flights",
            public_only=True,
            share_screen=True,
        )
    with pytest.raises(ValidationError):
        ComputerUseInput(
            engine="managed",
            title="No resumed login",
            goal="Read",
            start_url="https://books.toscrape.com/",
            public_only=True,
            share_screen=True,
            source_job_id=job["id"],
        )


def test_managed_browser_is_disabled_without_operator_opt_in(world):
    r, provider, _, _ = world
    r.jobs.managed_browser.enabled = False
    with pytest.raises(DomainError, match="COMPUTER_USE_UNAVAILABLE"):
        prepare(world)
    assert not provider.calls

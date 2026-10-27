"""Selected task binding across the real conversation service; scripted provider only."""

import asyncio
import json
import time
from uuid import uuid4

import pytest

from desk.app import create_app
from desk.conversation import Conversations, task_context
from desk.schemas import SettingsInput
from desk.store import DomainError
from desk.tasks import TaskInput, TaskAction
from test_tool_dispatch import FakeSocket
from test_voice_omni import QuietOmni, config
from test_omni_conversation import until


@pytest.fixture
def desk(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    principal = {"kind": "owner", "session": runtime.store.authenticate("owner", "fixture")}
    task = runtime.tasks.create(
        TaskInput(title="Selected report", next_step="Review evidence"), uuid4().hex
    )["task"]
    runtime.tasks.create(TaskInput(title="Unrelated private task"), uuid4().hex)
    return runtime, principal, task


def test_selected_task_context_is_current_minimal_and_review_only(desk):
    runtime, principal, task = desk
    context = task_context(runtime, principal, task["id"])
    assert task["id"] in context and '"version": 1' in context
    assert "Review evidence" in context and "untrusted data" in context
    assert "only the owner can confirm" in context
    assert "Unrelated private task" not in context
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM assistant_proposals").fetchone()[0] == 0
    assert runtime.tasks.detail(task["id"])["task"]["status"] == "todo"


def test_task_context_respects_hidden_private_data(desk):
    runtime, principal, task = desk
    runtime.store.update_settings(
        SettingsInput(timezone="Asia/Hong_Kong", hide_private=True, expected_version=1), uuid4().hex
    )
    with pytest.raises(DomainError, match="PRIVATE_TASK_HIDDEN"):
        task_context(runtime, principal, task["id"])


def test_replay_cannot_switch_selected_task_or_owner():
    c = Conversations()
    owner = {"kind": "owner", "session": "first"}
    chat = c.open(owner, "r", task_id="task-a")
    chat.append("user", "Details from task A")
    assert c.open(owner, "r", chat.id, task_id="task-a") is chat
    for task_id in (None, "task-b"):
        with pytest.raises(DomainError, match="CONVERSATION_SCOPE_CHANGED"):
            c.open(owner, "r", chat.id, task_id=task_id)
    with pytest.raises(DomainError, match="CONVERSATION_NOT_FOUND"):
        c.open({"kind": "owner", "session": "second"}, "r", chat.id, task_id="task-a")
    assert c.open(owner, "r", task_id="task-b").items == []
    assert c.open(owner, "r").items == []


@pytest.mark.parametrize(
    "task_id,kind,expected",
    [
        ({"id": "bad"}, "owner", "INVALID_TASK_CONTEXT"),
        ("x" * 65, "owner", "INVALID_TASK_CONTEXT"),
        ("", "owner", "INVALID_TASK_CONTEXT"),
        ("missing", "owner", "TASK_NOT_FOUND"),
        ("selected", "controller", "TASK_CONTEXT_NOT_ALLOWED"),
    ],
)
def test_invalid_selection_never_opens_provider_and_releases_session(desk, task_id, kind, expected):
    runtime, principal, task = desk
    if task_id == "selected":
        task_id = task["id"]
    runtime.voice.config = config()

    def forbidden(*args, **kwargs):
        pytest.fail("invalid selected task reached provider connector")

    runtime.voice.connector = forbidden

    async def scenario():
        socket = FakeSocket()
        runtime.voice.active, runtime.voice.started = True, time.monotonic()
        await runtime.voice.run(socket, {**principal, "kind": kind}, "en", "text", task_id=task_id)
        assert (await until(socket, "error"))["code"] == expected
        assert not runtime.voice.active

    asyncio.run(scenario())


def test_selected_task_reaches_setup_and_refresh_before_next_message(desk):
    runtime, principal, task = desk

    async def scenario():
        provider, socket = QuietOmni(), FakeSocket()
        runtime.voice.config = config()
        runtime.voice.connector = lambda *a, **k: provider
        runtime.voice.active, runtime.voice.started = True, time.monotonic()
        running = asyncio.create_task(
            runtime.voice.run(socket, principal, "en", "text", task_id=task["id"])
        )
        ready = await until(socket, "ready")
        assert runtime.voice.conversations.entries[ready["conversation_id"]].task_id == task["id"]
        first = provider.sent[0]["session"]["instructions"]
        assert "Selected report" in first and "Review evidence" in first
        runtime.tasks.action(
            task["id"],
            TaskAction(
                action="update",
                expected_version=1,
                task=TaskInput(title="Selected report", next_step="Prepare final charts"),
            ),
            uuid4().hex,
        )
        await socket.incoming.put({"type": "text", "text": "What is the next step for this task?"})
        await until(socket, "transcript")
        updates = [
            e["session"]["instructions"]
            for e in provider.sent
            if e.get("type") == "session.update" and "instructions" in e["session"]
        ]
        assert "Prepare final charts" in updates[-1] and '"version": 2' in updates[-1]
        assert "Unrelated private task" not in json.dumps(provider.sent)
        await socket.incoming.put({"type": "stop"})
        await asyncio.wait_for(running, 2)
        with runtime.store.connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM assistant_proposals").fetchone()[0] == 0

    asyncio.run(scenario())


def test_websocket_start_binds_selected_task_through_public_route(tmp_path):
    from fastapi.testclient import TestClient

    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    task = runtime.tasks.create(TaskInput(title="Route-selected task"), uuid4().hex)["task"]
    provider = QuietOmni()
    runtime.voice.config = config()
    runtime.voice.connector = lambda *a, **k: provider
    with TestClient(app) as client:
        headers = {"X-Desk-Request": "1"}
        assert (
            client.post(
                "/api/session", json={"username": "owner", "password": "fixture"}, headers=headers
            ).status_code
            == 200
        )
        ticket = client.post("/api/voice/tickets", headers=headers).json()["ticket"]
        with client.websocket_connect("/api/voice/ws") as socket:
            socket.send_json(
                {"ticket": ticket, "mode": "text", "language": "en", "task_id": task["id"]}
            )
            while True:
                event = socket.receive_json()
                if event["type"] == "ready":
                    break
            assert (
                runtime.voice.conversations.entries[event["conversation_id"]].task_id == task["id"]
            )
            assert "Route-selected task" in provider.sent[0]["session"]["instructions"]
            socket.send_json({"type": "stop"})

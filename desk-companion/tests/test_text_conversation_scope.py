"""HTTP and realtime share one bounded owner/task scope without a transcript table."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.context import pack_conversation
from desk.conversation import memory_context
from desk.store import DomainError
from desk.tasks import TaskInput
from desk.text_ai import TextPlan


def owner_client(app):
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    return client


def send(client, message, *, key=None, **scope):
    return client.post(
        "/api/assistant/messages",
        json={"message": message, **scope},
        headers={"X-Desk-Request": "1", "X-Operation-Id": key or uuid4().hex},
    )


def test_http_replay_is_login_and_task_scoped_and_retries_do_not_duplicate(tmp_path, monkeypatch):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    captured = []
    monkeypatch.setattr(runtime.text_ai.config, "valid", lambda: True)

    def generate(system, context, schema, purpose):
        captured.append(context)
        return TextPlan(message="Acknowledged", tool="none")

    monkeypatch.setattr(runtime.text_ai, "generate", generate)
    first, second = owner_client(app), owner_client(app)
    task = runtime.tasks.create(TaskInput(title="Fixture task"), "fixture-task")["task"]
    result = send(first, "The transient code is cobalt", task_id=task["id"], key="same-key").json()
    chat_id = result["conversation_id"]
    follow = send(first, "Continue", task_id=task["id"], conversation_id=chat_id, key="follow")
    assert follow.status_code == 200
    assert any("cobalt" in turn["body"] for turn in captured[-1]["turns"])
    send(first, "Continue", task_id=task["id"], conversation_id=chat_id, key="follow")
    principal = {"kind": "owner", "session": first.cookies.get("desk_companion_session")}
    conversation = runtime.voice.conversations.open(
        principal, memory_context(runtime, True)[0], chat_id, task_id=task["id"]
    )
    assert sum(item["text"] == "Continue" for item in conversation.items) == 1
    assert send(first, "Wrong task", conversation_id=chat_id).status_code == 409
    assert (
        send(second, "Stolen handle", task_id=task["id"], conversation_id=chat_id).status_code
        == 404
    )
    assert send(second, "The transient code is cobalt", key="same-key").status_code == 409
    assert send(second, "Hello from a fresh login", key="new-session-key").status_code == 200
    assert captured[-1]["turns"] == []
    assert pack_conversation(runtime)["turns"] == []
    with runtime.store.connection() as conn:
        assert (
            conn.execute("SELECT name FROM sqlite_master WHERE name='assistant_turns'").fetchone()
            is None
        )


def test_memory_change_and_logout_prevent_stale_context_reuse(tmp_path, monkeypatch):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    client = owner_client(app)
    principal = {"kind": "owner", "session": client.cookies.get("desk_companion_session")}
    fact = runtime.memory.create("Fixture code cobalt", "fixture-fact")["memory"]
    initial = send(client, "A transient discussion").json()
    chat_id = initial["conversation_id"]
    conversation = runtime.voice.conversations.open(
        principal, memory_context(runtime, True)[0], chat_id
    )
    conversation.append("assistant", "Fixture code cobalt")
    runtime.memory.delete(fact["id"], fact["version"], "forget-fixture")
    seen = []
    monkeypatch.setattr(runtime.text_ai.config, "valid", lambda: True)

    def generate(system, context, schema, purpose):
        seen.append(context)
        return TextPlan(message="Fresh reply", tool="none")

    monkeypatch.setattr(runtime.text_ai, "generate", generate)
    assert send(client, "Continue after deletion", conversation_id=chat_id).status_code == 200
    assert seen[-1]["turns"] == [] and seen[-1]["memory"] == []
    client.delete("/api/session", headers={"X-Desk-Request": "1"})
    assert send(client, "After logout", conversation_id=chat_id).status_code == 401
    other = owner_client(app)
    assert send(other, "After login", conversation_id=chat_id).status_code == 404


def test_internal_and_paired_callers_have_no_reusable_owner_history(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    reply = runtime.text_ai.message(
        AssistantMessage(message="A transient internal line"), "internal"
    )
    assert "conversation_id" not in reply
    assert runtime.voice.conversations.entries == {}
    with pytest.raises(DomainError, match="CONVERSATION_NOT_FOUND"):
        runtime.text_ai.message(
            AssistantMessage(message="Read history", conversation_id="unknown"),
            "paired",
            allow_memory=False,
            principal={"kind": "display", "id": "paired"},
        )


def test_owner_can_recover_the_same_draft_after_login_without_replaying_old_chat(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    first, second = owner_client(app), owner_client(app)
    started = send(first, "A temporary greeting").json()
    body = {"conversation_id": started["conversation_id"]}
    result = send(first, "Remember: fixture receipt recovery", key="lost-receipt", **body).json()
    recovered = send(second, "Remember: fixture receipt recovery", key="lost-receipt", **body)
    assert recovered.status_code == 200
    assert recovered.json()["proposal"]["id"] == result["proposal"]["id"]
    runtime = app.state.runtime
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM assistant_proposals").fetchone()[0] == 1
    principal = {"kind": "owner", "session": second.cookies.get("desk_companion_session")}
    fresh = runtime.voice.conversations.open(
        principal, memory_context(runtime, True)[0], recovered.json()["conversation_id"]
    )
    assert fresh.items == []


def test_forget_that_targets_only_the_fact_cited_in_this_login_conversation(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    fact = runtime.memory.create("I prefer tea", "fact")["memory"]
    first, second = owner_client(app), owner_client(app)
    cited = send(first, "What do you remember about tea?").json()
    assert cited["citations"][0]["id"] == fact["id"]
    unrelated = send(second, "Forget that").json()
    assert unrelated["kind"] == "clarify"
    assert "proposal" not in unrelated
    draft = send(first, "Forget that", conversation_id=cited["conversation_id"]).json()
    assert draft["kind"] == "draft" and draft["saved"] is False
    assert draft["proposal"]["data"]["memory_id"] == fact["id"]
    assert runtime.memory.for_model()[0]["id"] == fact["id"]

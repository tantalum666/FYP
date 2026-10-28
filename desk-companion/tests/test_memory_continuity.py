"""Old facts stay searchable and removable without widening prompt or owner scope."""

from datetime import timedelta

import pytest

from desk.assistant import AssistantMessage
from desk.conversation import memory_context
from desk.memory import MAX_MODEL
from desk.store import DomainError
from desk.tool_policy import execute_tool

from test_agent_loop import _runtime
from test_text_conversation_scope import owner_client, send


def older_fact(runtime, body="My lab locker is Orion.", *, expires_at=None):
    fact = runtime.memory.create(body, "old-fact", expires_at=expires_at)["memory"]
    later = runtime.store.clock() + timedelta(minutes=1)
    runtime.store.clock = lambda: later
    for index in range(MAX_MODEL):
        runtime.memory.create(f"Recent fixture preference {index}", f"recent-{index}")
    assert fact["id"] not in {row["id"] for row in runtime.memory.for_model()}
    return fact


def tool(runtime, name, arguments, key="query", **kwargs):
    return execute_tool(runtime, name, arguments, key, scope=key, **kwargs)


@pytest.mark.parametrize(
    ("body", "query"),
    [("My lab locker is Orion.", "lab locker"), ("实验室柜子的代号是星河", "实验室柜子")],
)
def test_query_finds_older_english_and_chinese_facts_without_expanding_default_prompt(
    tmp_path, body, query
):
    runtime = _runtime(tmp_path)
    fact = older_fact(runtime, body)
    recent = tool(runtime, "memory_query", {})["memories"]
    assert len(recent) == MAX_MODEL and fact["id"] not in {row["id"] for row in recent}
    matched = tool(runtime, "memory_query", {"query": query})["memories"]
    assert [row["id"] for row in matched] == [fact["id"]]
    assert "previous_body" not in matched[0] and "note" not in matched[0]
    assert len(tool(runtime, "memory_query", {"query": "fixture"})["memories"]) == 8
    assert body not in memory_context(runtime, True)[1]


@pytest.mark.parametrize("action", ["replace", "delete"])
def test_older_fact_changes_require_review_and_recheck_version_at_confirmation(tmp_path, action):
    runtime = _runtime(tmp_path)
    fact = older_fact(runtime)
    arguments = {"memory_id": fact["id"], "expected_version": fact["version"]}
    if action == "replace":
        arguments["body"] = "My lab locker is Vega."
    prepared = tool(runtime, f"memory_{action}_draft", arguments, "prepare")
    assert "proposal" in prepared and prepared["saved"] is False
    assert prepared["proposal"]["data"]["previous"] == fact["body"]
    assert any(row["body"] == fact["body"] for row in runtime.memory.listing()["memories"])

    # A second device edits before confirmation: the stale draft must not overwrite it.
    changed = runtime.memory.replace(fact["id"], "My lab locker is Lyra.", 1, "other-device")
    with pytest.raises(DomainError, match="VERSION_CONFLICT"):
        runtime.assistant.decide(prepared["proposal"]["id"], "confirm", "stale-confirm")
    stale = tool(runtime, f"memory_{action}_draft", arguments, "stale-prepare")
    assert stale["error"] == "VERSION_CONFLICT"
    arguments["expected_version"] = changed["memory"]["version"]
    fresh = tool(runtime, f"memory_{action}_draft", arguments, "fresh-prepare")
    runtime.assistant.decide(fresh["proposal"]["id"], "confirm", "fresh-confirm")
    remaining = tool(runtime, "memory_query", {"query": "lab locker"})["memories"]
    assert [row["body"] for row in remaining] == (
        ["My lab locker is Vega."] if action == "replace" else []
    )


@pytest.mark.parametrize("prefix", ["Forget", "忘掉"])
def test_exact_forget_of_an_older_fact_prepares_only_a_draft(tmp_path, prefix):
    runtime = _runtime(tmp_path)
    fact = older_fact(runtime)
    draft = runtime.assistant.memory_turn(
        AssistantMessage(message=f"{prefix}: {fact['body']}"), "forget-old"
    )
    assert draft["kind"] == "draft" and draft["saved"] is False
    assert draft["proposal"]["data"]["memory_id"] == fact["id"]
    runtime.assistant.decide(draft["proposal"]["id"], "cancel", "cancel-forget")
    assert any(row["id"] == fact["id"] for row in runtime.memory.listing()["memories"])


@pytest.mark.parametrize("change", ["delete", "expire"])
def test_older_fact_lifecycle_invalidates_http_replay_even_when_recent_window_is_unchanged(
    tmp_path, monkeypatch, change
):
    from desk.app import create_app
    from desk.text_ai import TextPlan

    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    expiry = runtime.store.clock() + timedelta(minutes=2)
    fact = older_fact(runtime, expires_at=expiry.isoformat() if change == "expire" else None)
    client = owner_client(app)
    principal = {"kind": "owner", "session": client.cookies.get("desk_companion_session")}
    initial = send(client, "A temporary conversation").json()
    revision, _prompt = memory_context(runtime, True)
    chat = runtime.voice.conversations.open(principal, revision, initial["conversation_id"])
    chat.append("assistant", fact["body"])
    chat.recall_id = fact["id"]
    recent = runtime.memory.for_model()
    if change == "delete":
        runtime.memory.delete(fact["id"], fact["version"], "remove-old")
    else:
        # No scheduler tick: read-time expiry alone must invalidate old context.
        runtime.store.clock = lambda: expiry + timedelta(seconds=1)
    assert runtime.memory.for_model() == recent
    assert memory_context(runtime, True)[0] != revision

    seen = []
    monkeypatch.setattr(runtime.text_ai.config, "valid", lambda: True)

    def generate(system, context, schema, purpose):
        seen.append(context)
        return TextPlan(message="Fresh reply", tool="none")

    monkeypatch.setattr(runtime.text_ai, "generate", generate)
    assert send(client, "Continue", conversation_id=chat.id).status_code == 200
    assert seen[-1]["turns"] == [] and chat.recall_id is None
    assert fact["body"] not in str(seen[-1])
    # A repeated read key cannot return a retired fact.
    assert tool(runtime, "memory_query", {"query": "lab locker"})["memories"] == []
    blocked = tool(
        runtime, "memory_replace_draft",
        {"memory_id": fact["id"], "expected_version": 1, "body": "Revive old fact"},
        "revive",
    )
    assert blocked["error"] == "VERSION_CONFLICT"


def test_old_memory_tools_keep_the_paired_owner_boundary(tmp_path):
    runtime = _runtime(tmp_path)
    fact = older_fact(runtime)
    calls = [
        ("memory_query", {"query": "lab locker"}),
        ("memory_replace_draft", {
            "memory_id": fact["id"], "expected_version": 1, "body": "Other value",
        }),
        ("memory_delete_draft", {"memory_id": fact["id"], "expected_version": 1}),
    ]
    for name, arguments in calls:
        assert tool(runtime, name, arguments, name, allow_memory=False) == {
            "error": "OWNER_SIGN_IN_REQUIRED", "saved": False,
        }
    assert fact["body"] not in memory_context(runtime, False)[1]

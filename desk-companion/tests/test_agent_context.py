"""Actual SQLite continuity and privacy boundaries; no live provider requests."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from uuid import uuid4

import pytest
from pydantic import ValidationError

from desk.agent_context import AgentContextBridge, RunPersonalContextSelection
from desk.assistant import AssistantMessage
from desk.context import ContextSettings
from desk.conversations import ConversationAction, ConversationInput
from desk.memory import MemoryAction, MemoryInput
from desk.runtime import Runtime
from desk.schemas import SettingsInput
from desk.store import DomainError, Store
from desk.text_ai import TextConfig


@pytest.fixture
def context_world(tmp_path):
    clock = [datetime(2026, 10, 13, 5, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    token = runtime.store.authenticate("owner", "fixture-only")
    session_hash = hashlib.sha256(token.encode()).hexdigest()
    runtime.text_ai.config = TextConfig(
        provider="gemini", model="fixture-model", api_key="fixture-secret-provider-header"
    )
    destination = runtime.personal_context.destinations()[0]["id"]
    world = {
        "runtime": runtime,
        "bridge": AgentContextBridge(runtime),
        "owner": {"kind": "owner", "session": token},
        "clock": clock,
        "identity": {
            "run_id": uuid4().hex,
            "session_hash": session_hash,
            "provider_destination_id": destination,
        },
    }
    change_settings(
        world,
        save_text_history=True,
        use_text_history_in_ai=True,
        use_memory_in_ai=True,
        approved_destinations=[destination],
    )
    return world


def change_settings(world, **changes):
    runtime = world["runtime"]
    old = runtime.personal_context.settings()
    payload = {
        k: old[k]
        for k in (
            "save_text_history",
            "use_text_history_in_ai",
            "use_memory_in_ai",
            "approved_destinations",
            "share_business_context",
        )
    } | changes
    return runtime.personal_context.update(
        ContextSettings(expected_version=old["version"], **payload), uuid4().hex
    )


def memory(world, content="Prefer short reports", category="preference"):
    return world["runtime"].memories.create(
        MemoryInput(content=content, category=category), uuid4().hex
    )["memory"]


def conversation(
    world, content="The selected project deadline is Friday", title="Selected project"
):
    thread = world["runtime"].conversations.create(ConversationInput(title=title), uuid4().hex)[
        "conversation"
    ]
    append(world, thread["id"], content)
    return world["runtime"].conversations.detail(thread["id"])["conversation"]


def append(world, conversation_id, content, reply="Earlier assistant text is not evidence"):
    return world["runtime"].conversations.send(
        AssistantMessage(message=content, conversation_id=conversation_id),
        uuid4().hex,
        lambda *args, **kwargs: {"mode": "local_rules", "kind": "reply", "message": reply},
        principal=world["owner"],
    )


def selection(*memories, conversation=None):
    return RunPersonalContextSelection(
        memory_ids=[m["id"] for m in memories],
        conversation_id=conversation["id"] if conversation else None,
        retain_derived_context=True,
    )


def bind(world, selected):
    return world["bridge"].bind(selected, **world["identity"])


def project(world, binding):
    return world["bridge"].project(binding, **world["identity"])


def hide(world, value):
    runtime = world["runtime"]
    with runtime.store.connection() as conn:
        settings = runtime.store.settings(conn)
    runtime.store.update_settings(
        SettingsInput(
            expected_version=settings["version"], timezone=settings["timezone"], hide_private=value
        ),
        uuid4().hex,
    )


def dump(world):
    with world["runtime"].store.connection() as conn:
        return list(conn.iterdump())


def test_default_no_context_and_separate_retention_acknowledgement(context_world):
    world = context_world
    memory(world)
    conversation(world)
    assert bind(world, RunPersonalContextSelection()) is None
    assert project(world, None) is None
    for kwargs in ({"memory_ids": ["a"]}, {"conversation_id": "b"}):
        with pytest.raises(ValidationError, match="retained model outputs"):
            RunPersonalContextSelection(**kwargs)
    with pytest.raises(ValidationError):
        RunPersonalContextSelection(
            memory_ids=["duplicate", "duplicate"], retain_derived_context=True
        )
    with pytest.raises(ValidationError):
        RunPersonalContextSelection(
            memory_ids=[str(i) for i in range(9)], retain_derived_context=True
        )
    with pytest.raises(ValidationError):
        RunPersonalContextSelection(retain_derived_context=True, approve_all_tools=True)


def test_only_explicit_selected_context_no_authority_evidence_or_credentials(context_world):
    world = context_world
    selected_memory = memory(world, "Use concise comparison tables")
    memory(world, "UNRELATED_MEMORY_DO_NOT_TRANSMIT")
    selected_thread = conversation(world, "SELECTED_DEADLINE_FRIDAY")
    conversation(world, "UNRELATED_THREAD_DO_NOT_TRANSMIT")
    binding = bind(world, selection(selected_memory, conversation=selected_thread))
    output = project(world, binding)
    text = json.dumps(output)
    assert "Use concise comparison tables" in text and "SELECTED_DEADLINE_FRIDAY" in text
    assert "UNRELATED_" not in text
    assert output["authority"] == "none" and output["is_evidence"] is False
    assert "permissions" in output["notice"] and "verified outcomes" in output["notice"]
    assert set(output) == {"kind", "authority", "is_evidence", "memories", "history", "notice"}
    for secret in (world["owner"]["session"], "fixture-secret-provider-header"):
        assert secret not in json.dumps(binding) + text
    assert world["identity"]["session_hash"] not in text
    assert "SELECTED_DEADLINE_FRIDAY" not in json.dumps(binding)
    assert "Use concise comparison tables" not in json.dumps(binding)


def test_bridge_and_catalog_are_read_only_and_restart_has_no_projection_cache(context_world):
    world = context_world
    remembered = memory(world, "PERSIST_ONLY_IN_MEMORY_TABLE")
    thread = conversation(world, "PERSIST_ONLY_IN_THREAD")
    before = dump(world)
    binding = bind(world, selection(remembered, conversation=thread))
    first = project(world, binding)
    world["bridge"].catalog(session_hash=world["identity"]["session_hash"])
    assert dump(world) == before
    # A restored metadata-only binding resolves the same original selected messages.
    world["bridge"] = AgentContextBridge(world["runtime"])
    assert project(world, json.loads(json.dumps(binding))) == first
    first["memories"][0]["content"] = "MUTATED_CALLER_COPY"
    assert "MUTATED_CALLER_COPY" not in json.dumps(project(world, binding))
    assert dump(world) == before


@pytest.mark.parametrize("forged", [None, "owner", "0" * 64, {"kind": "owner"}])
def test_catalog_and_binding_reject_owner_shaped_or_unrecognized_identity(context_world, forged):
    world = context_world
    remembered = memory(world)
    with pytest.raises(DomainError, match="RUN_SESSION_EXPIRED"):
        world["bridge"].catalog(session_hash=forged)
    with pytest.raises(DomainError, match="RUN_SESSION_EXPIRED"):
        world["bridge"].bind(
            selection(remembered), **(world["identity"] | {"session_hash": forged})
        )


def test_exact_original_session_run_and_provider_bound(context_world):
    world = context_world
    binding = bind(world, selection(memory(world)))
    second = world["runtime"].store.authenticate("owner", "fixture-only")
    for change in (
        {"run_id": uuid4().hex},
        {"provider_destination_id": "1" * 64},
        {"session_hash": hashlib.sha256(second.encode()).hexdigest()},
    ):
        with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_BINDING_CHANGED"):
            world["bridge"].project(binding, **(world["identity"] | change))
    world["runtime"].store.logout(world["owner"]["session"])
    with pytest.raises(DomainError, match="RUN_SESSION_EXPIRED"):
        project(world, binding)


def test_expiry_stops_existing_projection(context_world):
    binding = bind(context_world, selection(memory(context_world)))
    context_world["clock"][0] += timedelta(hours=8)
    with pytest.raises(DomainError, match="RUN_SESSION_EXPIRED"):
        project(context_world, binding)


def test_catalog_only_displays_permitted_choices_to_visible_owner(context_world):
    world = context_world
    remembered = memory(world, "x" * 1000)
    thread = conversation(world)
    catalog = world["bridge"].catalog(session_hash=world["identity"]["session_hash"])
    assert catalog["memories"] == [
        {"id": remembered["id"], "version": 1, "category": "preference", "summary": "x" * 160}
    ]
    assert catalog["conversations"] == [
        {
            "id": thread["id"],
            "version": thread["version"],
            "title": "Selected project",
            "eligible_message_count": 2,
        }
    ]
    change_settings(world, use_memory_in_ai=False)
    assert not world["bridge"].catalog(session_hash=world["identity"]["session_hash"])["memories"]
    with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_NOT_APPROVED"):
        bind(world, selection(remembered))
    change_settings(world, approved_destinations=[])
    catalog = world["bridge"].catalog(session_hash=world["identity"]["session_hash"])
    assert not catalog["memories"] and not catalog["conversations"]
    with pytest.raises(DomainError, match="PROVIDER_CONTEXT_NOT_APPROVED"):
        bind(world, selection(conversation=thread))
    hide(world, True)
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        world["bridge"].catalog(session_hash=world["identity"]["session_hash"])


def test_message_watermark_does_not_expand_on_append_or_rename(context_world):
    world = context_world
    thread = conversation(world, "ORIGINAL_SELECTED_MESSAGE")
    binding = bind(world, selection(conversation=thread))
    old = project(world, binding)
    append(world, thread["id"], "LATER_MESSAGE_NOT_SELECTED")
    current = world["runtime"].conversations.detail(thread["id"])["conversation"]
    world["runtime"].conversations.action(
        thread["id"],
        ConversationAction(action="rename", expected_version=current["version"], title="New title"),
        uuid4().hex,
    )
    assert project(world, binding) == old
    assert "LATER_MESSAGE" not in json.dumps(project(world, binding))
    rebound = bind(world, selection(conversation=thread))
    assert "LATER_MESSAGE" in json.dumps(project(world, rebound))


def test_explicit_thread_selection_with_zero_messages_does_not_follow_future_messages(
    context_world,
):
    world = context_world
    thread = world["runtime"].conversations.create(
        ConversationInput(title="Empty selection"), uuid4().hex
    )["conversation"]
    binding = bind(world, selection(conversation=thread))
    append(world, thread["id"], "FUTURE_UNSELECTED_TEXT")
    assert project(world, binding)["history"] == []


@pytest.mark.parametrize("action", ["forget", "update"])
def test_forget_and_correction_fence_original_binding_and_exclude_old_history(
    context_world, action
):
    world = context_world
    remembered = memory(world, "OLD_FACT_UNIQUE")
    thread = conversation(world, "OLD_FACT_UNIQUE was repeated in a transcript")
    binding = bind(world, selection(remembered, conversation=thread))
    world["runtime"].memories.action(
        remembered["id"],
        MemoryAction(
            action=action,
            expected_version=remembered["version"],
            content="CORRECTED_FACT" if action == "update" else None,
        ),
        uuid4().hex,
    )
    for bridge in (world["bridge"], AgentContextBridge(world["runtime"])):
        with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_CHANGED"):
            bridge.project(binding, **world["identity"])
        with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_CHANGED"):
            bridge.validate(binding, **world["identity"])
    # Readable retained transcript is a separate retention contract, never reprojected.
    assert "OLD_FACT_UNIQUE" in json.dumps(world["runtime"].conversations.detail(thread["id"]))
    new_selection = selection(conversation=thread)
    if action == "update":
        new_selection.memory_ids = [remembered["id"]]
    fresh = project(world, bind(world, new_selection))
    assert fresh["history"] == [] and "OLD_FACT_UNIQUE" not in json.dumps(fresh)
    if action == "update":
        assert "CORRECTED_FACT" in json.dumps(fresh)


@pytest.mark.parametrize(
    "setting", ["save_text_history", "use_text_history_in_ai", "use_memory_in_ai"]
)
def test_retention_and_context_off_on_never_revalidate_old_binding(context_world, setting):
    world = context_world
    remembered = memory(world)
    thread = conversation(world)
    binding = bind(world, selection(remembered, conversation=thread))
    change_settings(world, **{setting: False})
    change_settings(world, **{setting: True})
    with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_CHANGED"):
        project(world, binding)


def test_saving_off_still_allows_explicit_existing_history_under_separate_consent(context_world):
    world = context_world
    thread = conversation(world)
    change_settings(world, save_text_history=False)
    assert len(project(world, bind(world, selection(conversation=thread)))["history"]) == 2


def test_hide_show_provider_change_and_revocation_do_not_restore_old_binding(context_world):
    world = context_world
    remembered = memory(world)
    binding = bind(world, selection(remembered))
    hide(world, True)
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        project(world, binding)
    hide(world, False)
    with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_CHANGED"):
        project(world, binding)
    binding = bind(world, selection(remembered))
    change_settings(world, approved_destinations=[])
    change_settings(world, approved_destinations=[world["identity"]["provider_destination_id"]])
    with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_CHANGED"):
        project(world, binding)
    binding = bind(world, selection(remembered))
    world["runtime"].text_ai.config = TextConfig(
        provider="qwen",
        model="fixture-model",
        api_key="fixture-only",
        endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    )
    with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_CHANGED"):
        project(world, binding)


def test_deleted_selected_conversation_is_never_recovered_from_binding(context_world):
    world = context_world
    thread = conversation(world)
    binding = bind(world, selection(conversation=thread))
    world["runtime"].conversations.action(
        thread["id"],
        ConversationAction(action="delete", expected_version=thread["version"]),
        uuid4().hex,
    )
    with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_CHANGED"):
        project(world, binding)
    assert "deadline" not in json.dumps(binding)


@pytest.mark.parametrize(
    "mutation", ["message_text", "message_exclusion", "message_delete", "memory_text"]
)
def test_selected_integrity_checked_even_without_epoch_bump(context_world, mutation):
    world = context_world
    remembered = memory(world)
    thread = conversation(world)
    binding = bind(world, selection(remembered, conversation=thread))
    with world["runtime"].store.connection(write=True) as conn:
        if mutation == "memory_text":
            conn.execute(
                "UPDATE personal_memories SET content='changed' WHERE id=?", (remembered["id"],)
            )
        else:
            message_id = binding["messages"][0]["id"]
            sql = {
                "message_text": "UPDATE conversation_messages SET content='changed' WHERE id=?",
                "message_exclusion": "UPDATE conversation_messages SET context_allowed=0 WHERE id=?",
                "message_delete": "DELETE FROM conversation_messages WHERE id=?",
            }[mutation]
            conn.execute(sql, (message_id,))
    with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_CHANGED"):
        project(world, binding)


def test_count_character_and_utf8_byte_bounds(context_world):
    world = context_world
    memories = [memory(world, str(i) + "x" * 999) for i in range(8)]
    thread = conversation(world, "history-0")
    for i in range(1, 8):
        append(world, thread["id"], f"history-{i}")
    output = project(world, bind(world, selection(*memories, conversation=thread)))
    assert len(output["memories"]) == 8 and len(output["history"]) == 12
    assert "history-0" not in json.dumps(output)
    large = conversation(world, "u" * 3000)
    for _ in range(4):
        append(world, large["id"], "u" * 3000, reply="a" * 4000)
    bounded = project(world, bind(world, selection(conversation=large)))
    assert sum(len(x["content"]) for x in bounded["history"]) <= 12000
    # A multibyte projection cannot evade the encoded provider-context cap.
    for m in memories:
        world["runtime"].memories.action(
            m["id"],
            MemoryAction(action="update", expected_version=1, content="😀" * 1000),
            uuid4().hex,
        )
    with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_LIMIT"):
        bind(world, selection(*memories))


def test_late_result_rejected_without_holding_privacy_lock_over_provider(context_world):
    world = context_world
    remembered = memory(world, "LATE_PRIVATE_TEXT")
    binding = bind(world, selection(remembered))
    dispatched, release = Event(), Event()
    retained = []

    def fake_provider_flow():
        context = project(world, binding)
        assert "LATE_PRIVATE_TEXT" in json.dumps(context)
        dispatched.set()
        assert release.wait(5)
        result = "Model repeated LATE_PRIVATE_TEXT"
        with world["runtime"].store.connection(write=True) as conn:
            world["bridge"].validate(binding, **world["identity"], conn=conn)
            retained.append(result)

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(fake_provider_flow)
        assert dispatched.wait(5)
        world["runtime"].memories.action(
            remembered["id"], MemoryAction(action="forget", expected_version=1), uuid4().hex
        )
        release.set()
        with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_CHANGED"):
            pending.result(timeout=5)
    assert retained == []
    assert "LATE_PRIVATE_TEXT" not in "\n".join(dump(world))


def test_binding_is_strict_and_missing_selected_record_fails_closed(context_world):
    world = context_world
    with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_UNAVAILABLE"):
        bind(
            world, RunPersonalContextSelection(memory_ids=["missing"], retain_derived_context=True)
        )
    binding = bind(world, selection(memory(world)))
    binding["raw_cookie"] = "unexpected"
    with pytest.raises(DomainError, match="RUN_PERSONAL_CONTEXT_BINDING_INVALID"):
        project(world, binding)

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage, TOOLS
from desk.context import ContextSettings
from desk.conversations import ConversationInput, ConversationAction
from desk.memory import MemoryInput, MemoryAction
from desk.runtime import Runtime
from desk.schemas import SettingsInput
from desk.store import DomainError, Store
from desk.text_ai import TextConfig, TextPlan
from desk.voice import VoiceConfig

OWNER = {"kind": "owner", "id": "owner"}


@pytest.fixture
def desk(tmp_path):
    clock = [datetime(2026, 10, 12, 12, tzinfo=UTC)]
    r = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    return r, clock


def settings(r, **changes):
    current = r.personal_context.settings()
    payload = {
        k: current[k]
        for k in (
            "save_text_history",
            "use_memory_in_ai",
            "use_text_history_in_ai",
            "share_business_context",
            "approved_destinations",
        )
    }
    payload.update(changes)
    return r.personal_context.update(
        ContextSettings(expected_version=current["version"], **payload), uuid4().hex
    )


def memory(r, text="I prefer early meetings"):
    return r.memories.create(MemoryInput(content=text, category="preference"), uuid4().hex)[
        "memory"
    ]


def thread(r):
    settings(r, save_text_history=True)
    return r.conversations.create(ConversationInput(title="Research"), uuid4().hex)["conversation"]


def configure(r):
    r.text_ai.config = TextConfig(provider="gemini", model="fixture-model", api_key="fixture-only")
    r.voice.config = VoiceConfig(provider="gemini", model="fixture-model", api_key="fixture-only")
    return [d["id"] for d in r.personal_context.settings()["destinations"]]


def hide(r, value=True):
    with r.store.connection() as conn:
        current = r.store.settings(conn)
    r.store.update_settings(
        SettingsInput(
            expected_version=current["version"], timezone=current["timezone"], hide_private=value
        ),
        uuid4().hex,
    )


def test_default_off_temporary_plaintext_not_retained_and_restart_does_not_rerun(desk):
    r, _ = desk
    secret = "unique personal sentence: cedar 417"
    payload = AssistantMessage(message=secret)
    reply = r.text_ai.message(payload, "temp", principal=OWNER)
    assert reply["history_saved"] is False and reply["conversation_id"] is None
    assert r.text_ai.message(payload, "temp", principal=OWNER) == reply
    with r.store.connection() as conn:
        for table in (
            "personal_operations",
            "conversation_sends",
            "assistant_replies",
            "conversation_messages",
            "operations",
        ):
            assert secret not in str([tuple(row) for row in conn.execute(f"SELECT * FROM {table}")])
    restarted = Runtime(r.store)
    with pytest.raises(DomainError, match="ASSISTANT_REPLY_NOT_RETAINED"):
        restarted.text_ai.message(payload, "temp", principal=OWNER)
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        r.text_ai.message(AssistantMessage(message="different"), "temp", principal=OWNER)


def test_opt_in_history_survives_restart_receipts_are_references_and_delete_forgets(desk):
    r, _ = desk
    t = thread(r)
    payload = AssistantMessage(message="A simple hello with private words", conversation_id=t["id"])
    sent = r.text_ai.message(payload, "saved", principal=OWNER)
    assert sent["history_saved"] and sent["user_message_id"]
    restarted = Runtime(r.store)
    messages = restarted.conversations.detail(t["id"])["messages"]
    assert len(messages) == 2 and messages[0]["content"] == payload.message
    recovered = restarted.text_ai.message(payload, "saved", principal=OWNER)
    assert (
        recovered["reply_recovered"]
        and recovered["assistant_message_id"] == sent["assistant_message_id"]
    )
    current = restarted.conversations.detail(t["id"])["conversation"]
    restarted.conversations.action(
        t["id"],
        ConversationAction(action="delete", expected_version=current["version"]),
        "delete-thread",
    )
    with pytest.raises(DomainError, match="CONVERSATION_NOT_FOUND"):
        restarted.conversations.detail(t["id"])
    with restarted.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM conversation_messages").fetchone()[0] == 0
        assert payload.message not in str(
            [tuple(row) for row in conn.execute("SELECT * FROM personal_operations")]
        )
    with pytest.raises(DomainError, match="ASSISTANT_REPLY_NOT_RETAINED"):
        restarted.text_ai.message(payload, "saved", principal=OWNER)


def test_disabling_retention_keeps_history_readable_but_blocks_new_writes(desk):
    r, _ = desk
    t = thread(r)
    r.text_ai.message(
        AssistantMessage(message="hello", conversation_id=t["id"]), "saved", principal=OWNER
    )
    settings(r, save_text_history=False)
    assert len(r.conversations.detail(t["id"])["messages"]) == 2
    with pytest.raises(DomainError, match="TEXT_HISTORY_DISABLED"):
        r.text_ai.message(
            AssistantMessage(message="new", conversation_id=t["id"]), "blocked", principal=OWNER
        )
    with pytest.raises(DomainError, match="TEXT_HISTORY_DISABLED"):
        r.conversations.create(ConversationInput(title="No"), "new-thread")
    assert not r.text_ai.message(AssistantMessage(message="temporary"), "temp", principal=OWNER)[
        "history_saved"
    ]


def test_memory_correction_versions_receipts_never_resurrect_old_content(desk):
    r, _ = desk
    old = r.memories.create(MemoryInput(content="old unique preference"), "create-memory")["memory"]
    new = r.memories.action(
        old["id"],
        MemoryAction(
            action="update", expected_version=old["version"], content="corrected preference"
        ),
        "correct",
    )["memory"]
    assert new["version"] == 2
    with pytest.raises(DomainError, match="VERSION_CONFLICT"):
        r.memories.action(old["id"], MemoryAction(action="forget", expected_version=1), "stale")
    assert (
        r.memories.create(MemoryInput(content="old unique preference"), "create-memory")["memory"][
            "content"
        ]
        == "corrected preference"
    )
    r.memories.action(old["id"], MemoryAction(action="forget", expected_version=2), "forget")
    assert (
        r.memories.create(MemoryInput(content="old unique preference"), "create-memory")["memory"]
        is None
    )
    with r.store.connection() as conn:
        assert "old unique preference" not in str(
            [tuple(x) for x in conn.execute("SELECT * FROM personal_operations")]
        )
        assert (
            conn.execute(
                "SELECT content FROM personal_memories WHERE id=?", (old["id"],)
            ).fetchone()[0]
            == ""
        )


def test_model_can_only_draft_owner_confirmation_is_atomic_and_scrubbed(desk):
    r, _ = desk
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        r.assistant.tool("memory_create", {"content": "blue preference"}, "no-owner")
    draft = r.assistant.tool(
        "memory_create", {"content": "blue preference"}, "draft", personal_context=True
    )["proposal"]
    assert r.memories.listing()["memories"] == []
    assert not r.assistant.proposals()
    assert len(r.assistant.proposals(personal_context=True)) == 1
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        r.assistant.decide(draft["id"], "confirm", "denied")
    saved = r.assistant.decide(draft["id"], "confirm", "confirm", personal_context=True)
    repeated = r.assistant.decide(draft["id"], "confirm", "new-key", personal_context=True)
    assert saved["memory_id"] == repeated["memory_id"]
    assert len(r.memories.listing()["memories"]) == 1
    assert r.memories.listing()["memories"][0]["source"] == "confirmed_assistant"
    with r.store.connection() as conn:
        row = conn.execute(
            "SELECT * FROM assistant_proposals WHERE id=?", (draft["id"],)
        ).fetchone()
        assert row["data"] == "{}" and "blue preference" not in row["result"]
        assert "blue preference" not in str(
            [tuple(x) for x in conn.execute("SELECT * FROM personal_operations")]
        )
    assert all("confirm" not in tool["name"] for tool in TOOLS)
    with pytest.raises(DomainError, match="TOOL_NOT_ALLOWED"):
        r.assistant.tool("memory_confirm", {"id": draft["id"]}, "attack", personal_context=True)


def test_expired_and_cancelled_memory_drafts_are_scrubbed(desk):
    r, clock = desk
    one = r.assistant.tool(
        "memory_create", {"content": "first secret"}, "one", personal_context=True
    )["proposal"]
    r.assistant.decide(one["id"], "cancel", "cancel", personal_context=True)
    two = r.assistant.tool(
        "memory_create", {"content": "second secret"}, "two", personal_context=True
    )["proposal"]
    clock[0] += timedelta(minutes=6)
    r.tick()
    with pytest.raises(DomainError, match="DRAFT_EXPIRED"):
        r.assistant.decide(two["id"], "confirm", "late", personal_context=True)
    with r.store.connection() as conn:
        assert all(row[0] == "{}" for row in conn.execute("SELECT data FROM assistant_proposals"))


def test_context_requires_independent_explicit_destination_consent_and_owner(desk):
    r, _ = desk
    m = memory(r)
    destinations = configure(r)

    def get(**kw):
        return r.personal_context.for_provider(kind="text", principal=kw.get("principal", OWNER))

    assert not get()["memories"]
    settings(r, use_memory_in_ai=True)
    assert not get()["memories"]  # Display-visible does not mean provider-approved.
    settings(r, approved_destinations=destinations)
    assert get()["memories"][0]["id"] == m["id"]
    assert not get(principal={"kind": "display"})["memories"]
    assert not get(principal={"kind": "owner", "session": "revoked"})["memories"]
    assert r.personal_context.for_provider(kind="voice", principal=OWNER)["memories"]
    hide(r)
    assert not get()["memories"]
    hide(r, False)
    r.text_ai.config = TextConfig(
        provider="qwen",
        model="fixture-model",
        endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        api_key="fixture-only",
    )
    assert not r.personal_context.settings()["authorization_current"]
    assert not get()["memories"]


def test_context_bounds_and_correction_excludes_old_history_without_deleting_transcript(desk):
    r, _ = desk
    t = thread(r)
    m = memory(r, "old fact")
    for i in range(8):
        r.text_ai.message(
            AssistantMessage(message="user " + str(i), conversation_id=t["id"]),
            f"send-{i}",
            principal=OWNER,
        )
    settings(
        r, use_memory_in_ai=True, use_text_history_in_ai=True, approved_destinations=configure(r)
    )
    projection = r.personal_context.for_provider(
        kind="text", principal=OWNER, conversation_id=t["id"]
    )
    assert len(projection["history"]) == 12
    for i in range(10):
        memory(r, (str(i) + "A") * 500)
    projection = r.personal_context.for_provider(
        kind="text", principal=OWNER, conversation_id=t["id"]
    )
    assert sum(len(x["content"]) for x in projection["memories"]) <= 8000
    r.memories.action(m["id"], MemoryAction(action="forget", expected_version=1), "forget")
    assert not r.personal_context.for_provider(
        kind="text", principal=OWNER, conversation_id=t["id"]
    )["history"]
    assert len(r.conversations.detail(t["id"])["messages"]) == 16
    with pytest.raises(DomainError, match="ASSISTANT_REPLY_NOT_RETAINED"):
        r.text_ai.message(
            AssistantMessage(message="user 0", conversation_id=t["id"]), "send-0", principal=OWNER
        )


def test_provider_sees_only_permitted_projection_and_no_voice_retention(desk):
    r, _ = desk
    memory(r, "sensitive fixture preference")
    destinations = configure(r)
    seen = []

    def generate(system, context, schema, purpose):
        seen.append(context)
        return TextPlan(message="Mock model reply")

    r.text_ai.generate = generate
    r.text_ai.message(AssistantMessage(message="hello"), "unapproved", principal=OWNER)
    assert "sensitive fixture preference" not in json.dumps(seen[-1])
    settings(r, use_memory_in_ai=True, approved_destinations=destinations)
    r.text_ai.message(AssistantMessage(message="hello"), "approved", principal=OWNER)
    assert "sensitive fixture preference" in json.dumps(seen[-1])
    r.personal_context.for_provider(kind="voice", principal=OWNER)
    with r.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM conversation_messages").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM assistant_replies").fetchone()[0] == 0


def test_privacy_flip_during_provider_call_prevents_late_save(desk):
    r, _ = desk
    t = thread(r)
    configure(r)

    def generate(*args):
        hide(r)
        return TextPlan(message="do not store this late reply")

    r.text_ai.generate = generate
    with pytest.raises(DomainError, match="PROVIDER_CONTEXT_CHANGED|PRIVATE_CONTEXT_HIDDEN"):
        r.text_ai.message(
            AssistantMessage(message="hello", conversation_id=t["id"]), "racing", principal=OWNER
        )
    assert not r.conversations.detail(t["id"])["messages"]


def test_owner_only_api_routes_hide_private_and_paired_proposals(desk, tmp_path):
    app = create_app(tmp_path / "api", password="fixture-only", scheduler=False)
    r = app.state.runtime
    client = TestClient(app)
    headers = {"X-Desk-Request": "1", "X-Operation-Id": "create"}
    client.post(
        "/api/session", json={"username": "owner", "password": "fixture-only"}, headers=headers
    )
    created = client.post(
        "/api/assistant/memories", json={"content": "owner private fact"}, headers=headers
    )
    assert created.status_code == 200
    draft = r.assistant.tool(
        "memory_create", {"content": "owner pending fact"}, "draft", personal_context=True
    )["proposal"]
    enrolled = r.access.enrol_display("screen", "enroll")
    display = TestClient(app)
    display.headers["Authorization"] = "Bearer " + enrolled["token"]
    for path in ("memories", "conversations", "context-settings"):
        assert display.get("/api/assistant/" + path).status_code == 403
    assert not display.get("/api/workspace").json()["personal_context_visible"]
    assert not display.get("/api/assistant/proposals").json()["proposals"]
    assert (
        display.post(
            f"/api/assistant/proposals/{draft['id']}/decisions",
            json={"action": "confirm"},
            headers=headers,
        ).status_code
        == 403
    )
    t = thread(r)
    assert (
        display.post(
            "/api/assistant/messages",
            json={"message": "hello", "conversation_id": t["id"]},
            headers={**headers, "X-Operation-Id": "display-send"},
        ).status_code
        == 403
    )
    hide(r)
    assert not client.get("/api/workspace").json()["personal_context_visible"]
    assert client.get("/api/assistant/memories").json()["error"]["code"] == "PRIVATE_CONTEXT_HIDDEN"
    assert client.get("/api/assistant/context-settings").status_code == 200
    blocked = client.post(
        "/api/assistant/messages",
        json={"message": "Save note: hidden API draft"},
        headers={**headers, "X-Operation-Id": "hidden-api-note"},
    )
    assert (
        blocked.status_code == 403 and blocked.json()["error"]["code"] == "PRIVATE_CONTEXT_HIDDEN"
    )
    with r.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM computer_jobs").fetchone()[0] == 0


def test_cancel_and_expiry_invalidate_volatile_draft_replies(desk):
    r, clock = desk
    request = AssistantMessage(message="remember: rare fruit preference")
    reply = r.text_ai.message(request, "remember", principal=OWNER)
    r.assistant.decide(reply["proposal"]["id"], "cancel", "cancel", personal_context=True)
    with pytest.raises(DomainError, match="ASSISTANT_REPLY_NOT_RETAINED"):
        r.text_ai.message(request, "remember", principal=OWNER)
    other = r.text_ai.message(request, "remember-again", principal=OWNER)
    clock[0] += timedelta(minutes=6)
    with pytest.raises(DomainError, match="ASSISTANT_REPLY_NOT_RETAINED"):
        r.text_ai.message(request, "remember-again", principal=OWNER)
    replay = r.assistant.tool(
        "memory_create",
        {"content": "rare fruit preference", "category": "fact"},
        "memory/remember-again",
        personal_context=True,
    )
    assert replay["proposal"]["id"] == other["proposal"]["id"]
    assert replay["proposal"]["data"] == {}


def test_settings_destination_validation_version_and_secret_safe_metadata(desk):
    r, _ = desk
    configure(r)
    current = r.personal_context.settings()
    values = {
        k: current[k]
        for k in (
            "save_text_history",
            "use_memory_in_ai",
            "use_text_history_in_ai",
            "share_business_context",
            "approved_destinations",
        )
    }
    with pytest.raises(DomainError, match="CONTEXT_DESTINATION_CHANGED"):
        r.personal_context.update(
            ContextSettings(
                expected_version=current["version"],
                **{**values, "approved_destinations": ["https://evil.invalid"]},
            ),
            "bad",
        )
    settings(r, use_memory_in_ai=True)
    with pytest.raises(DomainError, match="VERSION_CONFLICT"):
        r.personal_context.update(
            ContextSettings(expected_version=current["version"], **values), "stale-settings"
        )
    r.text_ai.config.endpoint = "https://evil.invalid/?key=secret"
    value = r.personal_context.settings()
    assert "secret" not in json.dumps(value) and "fixture-only" not in json.dumps(value)


def test_bounded_capacity_and_stale_conversation_rename(desk):
    r, _ = desk
    t = thread(r)
    rename = ConversationAction(action="rename", title="Updated", expected_version=t["version"])
    r.conversations.action(t["id"], rename, "rename")
    with pytest.raises(DomainError, match="VERSION_CONFLICT"):
        r.conversations.action(t["id"], rename, "stale-rename")
    with r.store.connection(write=True) as conn:
        for i in range(200):
            conn.execute(
                "INSERT INTO conversation_messages VALUES(?,?,?,?,?,?,NULL,NULL,1)",
                (str(i), t["id"], "user", "fixture", "2026-10-12T12:00:00+00:00", None),
            )
    with pytest.raises(DomainError, match="CONVERSATION_FULL"):
        r.text_ai.message(
            AssistantMessage(message="beyond cap", conversation_id=t["id"]), "full", principal=OWNER
        )
    for i in range(29):
        r.conversations.create(ConversationInput(title="Thread " + str(i)), uuid4().hex)
    with pytest.raises(DomainError, match="CONVERSATION_LIMIT_REACHED"):
        r.conversations.create(ConversationInput(title="beyond cap"), "thread-cap")


def test_parallel_confirmation_creates_only_one_fact(desk):
    from concurrent.futures import ThreadPoolExecutor

    r, _ = desk
    proposal = r.assistant.tool(
        "memory_create", {"content": "one fact only"}, "draft", personal_context=True
    )["proposal"]

    def confirm(index):
        return r.assistant.decide(
            proposal["id"], "confirm", "confirmation-" + str(index), personal_context=True
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(confirm, range(8)))
    assert len({receipt["memory_id"] for receipt in receipts}) == 1
    assert len(r.memories.listing()["memories"]) == 1


def test_saved_business_context_is_never_sent_without_separate_consent(desk):
    from desk.tasks import TaskInput
    from desk.schemas import CreateEvents, EventInput

    r, clock = desk
    task = r.tasks.create(
        TaskInput(
            title="confidential task cedar", next_step="secret progress step", interval_minutes=15
        ),
        "task",
    )["task"]
    r.store.create(
        CreateEvents(
            event=EventInput(
                title="private calendar cedar",
                start_local="2026-10-12T21:00",
                end_local="2026-10-12T22:00",
            )
        ),
        "event",
    )
    destinations = configure(r)
    memory(r, "unshared memory cedar")
    seen = []

    def generate(system, context, schema, purpose):
        seen.append(json.loads(json.dumps(context)))
        return TextPlan(
            message="Read saved tasks", tool="task_details", arguments={"task_id": task["id"]}
        )

    r.text_ai.generate = generate
    settings(r, use_memory_in_ai=True, approved_destinations=destinations)
    reply = r.text_ai.message(
        AssistantMessage(message="Please help", task_id=task["id"]), "no-business", principal=OWNER
    )
    assert reply["error"] == "PROVIDER_CONTEXT_NOT_APPROVED"
    sent = json.dumps(seen[-1])
    assert (
        "confidential task cedar" not in sent
        and "secret progress step" not in sent
        and "private calendar cedar" not in sent
    )
    assert (
        "unshared memory cedar" in sent
    )  # Distinct memory consent does not authorize tasks/calendar.
    assert not any(
        t["name"].startswith(("task_", "calendar_", "computer_job_")) for t in seen[-1]["tools"]
    )
    with pytest.raises(DomainError, match="PROVIDER_CONTEXT_NOT_APPROVED"):
        r.assistant.tool("calendar_query", {}, "model-read", provider_kind="text", principal=OWNER)
    # Background consent defaults off even though the provider is configured.
    r.text_ai.config.background = True
    clock[0] += timedelta(minutes=16)
    r.tick()
    before = len(seen)
    r.text_ai.enrich_one()
    assert len(seen) == before
    settings(r, share_business_context=True, approved_destinations=destinations)
    context = r.text_ai.context(task["id"], principal=OWNER)
    assert "confidential task cedar" in json.dumps(context)
    assert not r.personal_context.business_allowed(kind="voice", principal={"kind": "display"})
    assert r.personal_context.business_allowed(kind="voice", principal=OWNER)


def test_privacy_off_on_transition_fences_inflight_response_and_cached_reply(desk):
    r, _ = desk
    request = AssistantMessage(message="a temporary phrase")
    r.text_ai.message(request, "old", principal=OWNER)
    old_revision = r.personal_context.revision()
    hide(r)
    hide(r, False)
    assert r.personal_context.revision() != old_revision
    with pytest.raises(DomainError, match="ASSISTANT_REPLY_NOT_RETAINED"):
        r.text_ai.message(request, "old", principal=OWNER)
    configure(r)

    def generate(*args):
        hide(r)
        hide(r, False)
        return TextPlan(message="outdated context reply")

    r.text_ai.generate = generate
    with pytest.raises(DomainError, match="PROVIDER_CONTEXT_CHANGED"):
        r.text_ai.message(request, "inflight", principal=OWNER)


def test_inflight_provider_does_not_block_revoke_and_late_reply_is_discarded(desk):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    r, _ = desk
    t = thread(r)
    configure(r)
    settings(
        r,
        use_memory_in_ai=True,
        approved_destinations=[d["id"] for d in r.personal_context.destinations()],
    )
    entered, release = threading.Event(), threading.Event()

    def generate(*args):
        entered.set()
        assert release.wait(5)
        return TextPlan(message="late private model response")

    r.text_ai.generate = generate
    payload = AssistantMessage(message="private user input", conversation_id=t["id"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(r.text_ai.message, payload, "inflight-revoke", OWNER)
        assert entered.wait(2)
        revocation = pool.submit(settings, r, use_memory_in_ai=False)
        try:
            updated = revocation.result(timeout=2)
            assert not updated["use_memory_in_ai"]
        finally:
            release.set()
        with pytest.raises(DomainError, match="PROVIDER_CONTEXT_CHANGED"):
            pending.result(timeout=2)
    assert not r.conversations.detail(t["id"])["messages"]
    assert "inflight-revoke" not in r.personal_context.replies
    with pytest.raises(DomainError, match="ASSISTANT_REPLY_NOT_RETAINED"):
        r.text_ai.message(payload, "inflight-revoke", principal=OWNER)


def test_one_active_turn_per_saved_thread_preserves_order_without_privacy_lock(desk):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    r, _ = desk
    t = thread(r)
    entered, release = threading.Event(), threading.Event()

    def reply(*args, **kwargs):
        entered.set()
        assert release.wait(4)
        return {"mode": "fixture", "message": "first response"}

    payload = AssistantMessage(message="first", conversation_id=t["id"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(r.conversations.send, payload, "first-turn", reply, OWNER)
        assert entered.wait(2)
        try:
            with pytest.raises(DomainError, match="CONVERSATION_BUSY"):
                r.text_ai.message(
                    AssistantMessage(message="second", conversation_id=t["id"]),
                    "second-turn",
                    principal=OWNER,
                )
        finally:
            release.set()
        assert pending.result(timeout=2)["history_saved"]
    assert not r.conversations.active_conversations
    assert len(r.conversations.detail(t["id"])["messages"]) == 2


def test_local_note_fallback_cannot_bypass_owner_or_hidden_job_guard(desk):
    r, _ = desk
    payload = AssistantMessage(message="Save note: sensitive draft body")
    with pytest.raises(DomainError, match="OWNER_SIGN_IN_REQUIRED"):
        r.text_ai.message(payload, "paired-note", principal={"kind": "display", "id": "screen"})
    hide(r)
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        r.text_ai.message(payload, "hidden-note", principal=OWNER)
    with r.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM computer_jobs").fetchone()[0] == 0
        assert "sensitive draft body" not in str(
            [tuple(row) for row in conn.execute("SELECT * FROM operations")]
        )

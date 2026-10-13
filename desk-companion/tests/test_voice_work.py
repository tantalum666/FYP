"""Protocol-fake voice review; actual SQLite/files, never microphones or providers."""

import hashlib
from uuid import uuid4

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.agent_runs import AgentRunService
from desk.voice import GeminiProtocol, QwenAudioProtocol, VoiceConfig
from desk.voice_work import VoiceDraftFreeze, VoiceWorkLedger

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from desk.agent_run_schemas import RunCreate
from desk.runtime import Runtime
from desk.schemas import SettingsInput
from desk.sources import SourceInput
from desk.store import DomainError, Store


@pytest.fixture
def world(tmp_path):
    clock = [datetime(2026, 10, 13, 6, tzinfo=UTC)]
    runtime = Runtime(Store(tmp_path, password="fixture-only", clock=lambda: clock[0]))
    token = runtime.store.authenticate("owner", "fixture-only")
    owner = {"kind": "owner", "session": token}
    session = hashlib.sha256(token.encode()).hexdigest()
    source = runtime.sources.ingest(
        SourceInput(name="synthetic.csv", format="csv"),
        b"item,hours\nreview,2\nwrite,3\n",
        "synthetic-source",
        session_hash=session,
    )["source"]
    return runtime, owner, source, clock


def request(world, **changes):
    runtime, owner, source, _ = world
    return RunCreate(
        **(
            dict(
                goal="Synthetic reviewed goal",
                retain=True,
                source_ids=[source["id"]],
                scope_revision=runtime.agent_runs.scope(owner)["scope_revision"],
            )
            | changes
        )
    )


def test_creation_rechecks_privacy_after_preflight_before_commit(world, monkeypatch):
    runtime, owner, _, _ = world
    payload = request(world)
    original = runtime.agent_runs._authorize

    def hide_after_preflight(run):
        original(run)
        with runtime.store.connection() as conn:
            settings = runtime.store.settings(conn)
        runtime.store.update_settings(
            SettingsInput(
                expected_version=settings["version"],
                timezone=settings["timezone"],
                hide_private=True,
            ),
            "hide-at-admission",
        )

    monkeypatch.setattr(runtime.agent_runs, "_authorize", hide_after_preflight)
    with pytest.raises(DomainError, match="PRIVATE_CONTEXT_HIDDEN"):
        runtime.agent_runs.create(payload, "create-during-hide", owner)
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM agent_run_operations").fetchone()[0] == 0


@pytest.mark.parametrize("retain", [1, "true"])
def test_retention_requires_actual_boolean(world, retain):
    with pytest.raises(ValidationError):
        request(world, retain=retain)


def voice(world, provider="qwen_audio"):
    runtime, owner, _, _ = world
    runtime.voice.config = VoiceConfig(
        provider=provider,
        model="protocol-fixture",
        api_key="fake-only",
        endpoint="wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
        if provider == "qwen_audio"
        else "",
    )
    return runtime.voice.work, runtime.voice.work.begin(owner)


def observe(
    ledger,
    ref,
    text="Synthetic recognized input",
    *,
    key="one",
    seq=1,
    boundary="provider_final",
    operation="replace",
    **changes,
):
    return ledger.observe(
        ref,
        dict(
            type="transcript",
            role="user",
            text=text,
            input_key=key,
            input_sequence=seq,
            boundary=boundary,
            input_operation=operation,
        )
        | changes,
    )


def freeze(world, ledger, event):
    return ledger.freeze(
        VoiceDraftFreeze(
            voice_session_ref=event["voice_session_ref"],
            input_segment_id=event["input_segment_id"],
            expected_revision=event["revision"],
        ),
        world[1],
    )


def selected(world, text="Synthetic recognized input"):
    ledger, ref = voice(world)
    event = observe(ledger, ref, text)
    return ledger, ref, event, freeze(world, ledger, event)


def test_normalized_append_snapshot_and_replacement_contract(world):
    ledger, ref = voice(world, "gemini")
    protocol = GeminiProtocol()
    first = ledger.observe(
        ref, protocol.events({"serverContent": {"inputTranscription": {"text": "Review "}}})[0]
    )
    draft = freeze(world, ledger, first)
    second = ledger.observe(
        ref,
        protocol.events(
            {"serverContent": {"inputTranscription": {"text": "the table"}, "turnComplete": True}}
        )[0],
    )
    assert second["text"] == "Review the table"
    assert first["input_segment_id"] == second["input_segment_id"]
    assert second["revision"] == 2 and second["operation"] == "replace"
    assert second["boundary"] == "unfinalized"
    assert draft["text"] == "Review " and draft["snapshot_kind"] == "owner_snapshot"
    assert freeze(world, ledger, first) == draft  # Stable acknowledged snapshot retry.
    third = ledger.observe(
        ref,
        protocol.events({"serverContent": {"inputTranscription": {"text": "A separate snapshot"}}})[
            0
        ],
    )
    assert third["input_segment_id"] != first["input_segment_id"]
    assert third["boundary"] == "unfinalized"


def test_qwen_final_dedup_conflict_and_separate_item(world):
    ledger, ref = voice(world)
    protocol = QwenAudioProtocol()
    raw = {
        "type": "conversation.item.input_audio_transcription.completed",
        "item_id": "untrusted-provider-item",
        "transcript": "Review this",
    }
    one = ledger.observe(ref, protocol.events(raw)[0])
    assert one["input_segment_id"] != raw["item_id"]
    assert one["boundary"] == "provider_final"
    assert ledger.observe(ref, protocol.events(raw)[0]) is None
    two = ledger.observe(ref, protocol.events(raw | {"item_id": "another"})[0])
    assert two["input_segment_id"] != one["input_segment_id"]
    invalid = ledger.observe(ref, protocol.events(raw | {"transcript": "Contradiction"})[0])
    assert invalid["eligible"] is False and invalid["text"] == ""
    with pytest.raises(DomainError, match="VOICE_INPUT_INVALID"):
        freeze(world, ledger, invalid)
    assert ledger.observe(ref, protocol.events(raw)[0]) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"role": "assistant"},
        {"role": "invented"},
        {"type": "tool"},
        {"type": "turn_complete"},
        {"boundary": "final"},
        {"input_sequence": 0},
        {"input_sequence": True},
        {"input_operation": "invented"},
        {"text": []},
    ],
)
def test_non_input_or_malformed_events_never_become_candidates(world, changes):
    ledger, ref = voice(world)
    assert observe(ledger, ref, **changes) is None
    assert not ledger.sessions[ref]["segments"] and not ledger.drafts
    assert world[0].agent_runs.listing(world[1])["runs"] == []


def test_stale_sequence_stale_review_and_overflow_never_tail(world):
    ledger, ref = voice(world, "gemini")
    one = observe(ledger, ref, "first", boundary="unfinalized", operation="append")
    assert observe(ledger, ref, "old", seq=1, boundary="unfinalized", operation="append") is None
    two = observe(ledger, ref, " second", seq=2, boundary="unfinalized", operation="append")
    with pytest.raises(DomainError, match="VOICE_INPUT_CHANGED"):
        freeze(world, ledger, one)
    assert two["text"] == "first second"
    over = observe(ledger, ref, "x" * 4001, seq=3, boundary="unfinalized", operation="append")
    assert not over["eligible"] and not over["text"] and over["reason"] == "VOICE_INPUT_TOO_LARGE"
    assert observe(ledger, ref, "tail", seq=4, boundary="unfinalized", operation="append") is None
    with pytest.raises(DomainError, match="VOICE_INPUT_TOO_LARGE"):
        freeze(world, ledger, over)


def test_utf8_blank_segment_draft_and_byte_bounds(world):
    ledger, ref = voice(world)
    assert not observe(ledger, ref, "   ")["eligible"]
    for n in range(1, 9):
        event = observe(ledger, ref, "界" * 1400, key=str(n), seq=n + 1)
    assert len(ledger.sessions[ref]["segments"]) <= 8
    assert ledger._size(ledger.sessions[ref]) <= 32768
    assert not event["eligible"]
    # Fresh short segments evict oldest, never reactivate an evicted correlation.
    for n in range(10, 14):
        event = observe(ledger, ref, str(n), key=str(n), seq=n + 1)
        freeze(world, ledger, event)
    event = observe(ledger, ref, "fifth", key="fifth", seq=20)
    with pytest.raises(DomainError, match="VOICE_DRAFT_LIMIT"):
        freeze(world, ledger, event)
    assert observe(ledger, ref, "late oldest", key="one", seq=21) is None


@pytest.mark.parametrize(
    "principal",
    [
        {"kind": "owner"},
        {"kind": "paired", "session": "fake"},
        {"kind": "agent"},
        {"kind": "owner", "session": "fake"},
    ],
)
def test_forged_wrong_principals_cannot_capture_or_freeze(world, principal):
    ledger, _, event, _ = selected(world)
    assert ledger.begin(principal) is None
    with pytest.raises(DomainError):
        ledger.freeze(
            VoiceDraftFreeze(
                voice_session_ref=event["voice_session_ref"],
                input_segment_id=event["input_segment_id"],
                expected_revision=1,
            ),
            principal,
        )


def test_other_real_owner_session_cannot_use_reference(world):
    ledger, _, event, draft = selected(world)
    other = {"kind": "owner", "session": world[0].store.authenticate("owner", "fixture-only")}
    with pytest.raises(DomainError, match="VOICE_CONTEXT_CHANGED"):
        ledger.freeze(
            VoiceDraftFreeze(
                voice_session_ref=event["voice_session_ref"],
                input_segment_id=event["input_segment_id"],
                expected_revision=1,
            ),
            other,
        )
    with pytest.raises(DomainError, match="VOICE_CONTEXT_CHANGED"):
        world[0].agent_runs.create(
            request(world, voice_origin_ref=draft["voice_origin_ref"]), "different-session", other
        )


@pytest.mark.parametrize("change", ["hide", "signout", "model", "endpoint", "privacy_epoch"])
def test_private_config_and_session_changes_clear_transient_candidates(world, change):
    ledger, ref, event, draft = selected(world)
    runtime, owner, _, _ = world
    if change == "hide":
        with runtime.store.connection() as conn:
            settings = runtime.store.settings(conn)
        runtime.store.update_settings(
            SettingsInput(
                expected_version=settings["version"],
                timezone=settings["timezone"],
                hide_private=True,
            ),
            "hide",
        )
    elif change == "signout":
        runtime.store.logout(owner["session"])
    elif change == "model":
        runtime.voice.config.model = "different-model"
    elif change == "endpoint":
        runtime.voice.config.endpoint = "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime"
    else:
        with runtime.store.connection(write=True) as conn:
            conn.execute("UPDATE personal_settings SET epoch=epoch+1")
    ledger.cleanup()
    assert not ledger.sessions and not ledger.drafts
    with pytest.raises(DomainError):
        freeze(world, ledger, event)
    with pytest.raises(DomainError):
        observe(ledger, ref, "late", seq=2)


def test_disconnect_expiry_restart_and_plaintext_exclusion(world):
    ledger, ref, _, draft = selected(world, "UNRETAINED_INPUT_MARKER_867")
    observe(ledger, ref, "UNSELECTED_NEIGHBOR_412", key="neighbor", seq=2)
    assert observe(ledger, ref, "ASSISTANT_MARKER_888", role="assistant", seq=3) is None
    ledger.end(ref)
    assert ledger.sessions[ref]["segments"] == {}
    assert draft["voice_origin_ref"] in ledger.drafts
    world[3][0] += timedelta(seconds=301)
    ledger.cleanup()
    assert not ledger.sessions and not ledger.drafts
    with pytest.raises(DomainError, match="VOICE_DRAFT_EXPIRED"):
        world[0].agent_runs.create(
            request(world, voice_origin_ref=draft["voice_origin_ref"]), "expired", world[1]
        )
    with world[0].store.connection() as conn:
        dump = "\n".join(conn.iterdump())
    assert all(
        marker not in dump
        for marker in ["UNRETAINED_INPUT", "UNSELECTED_NEIGHBOR", "ASSISTANT_MARKER"]
    )
    assert VoiceWorkLedger(world[0]).drafts == {}


def test_exact_receipt_first_after_expiry_restart_no_duplicate_or_fallback(world):
    runtime, owner, _, clock = world
    ledger, ref, _, draft = selected(world, "ORIGINAL_SPOKEN_PRIVATE_MARKER")
    payload = request(
        world,
        goal="Deliberately edited and retained goal",
        voice_origin_ref=draft["voice_origin_ref"],
    )
    created = runtime.agent_runs.create(payload, "original-operation", owner)
    run = created["run"]
    assert run["voice_origin"]["edited"] and "voice_origin_ref" not in run
    assert run["voice_origin"]["provider"] == "qwen_audio"
    assert "ORIGINAL_SPOKEN_PRIVATE_MARKER" not in str(run)
    ledger.end(ref)
    clock[0] += timedelta(seconds=301)
    runtime.voice.work = VoiceWorkLedger(runtime)
    runtime.agent_runs = AgentRunService(runtime)
    assert runtime.agent_runs.create(payload, "original-operation", owner) == created
    with pytest.raises(DomainError, match="OPERATION_ID_CONFLICT"):
        runtime.agent_runs.create(
            payload.model_copy(update={"goal": "changed"}), "original-operation", owner
        )
    with pytest.raises(DomainError, match="VOICE_DRAFT_ALREADY_USED"):
        runtime.agent_runs.create(payload, "new-operation", owner)
    with pytest.raises(DomainError, match="VOICE_DRAFT_EXPIRED"):
        runtime.agent_runs.create(
            payload.model_copy(update={"voice_origin_ref": uuid4().hex}), "guessed", owner
        )
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0] == 1
        dump = "\n".join(conn.iterdump())
    assert "ORIGINAL_SPOKEN_PRIVATE_MARKER" not in dump
    assert draft["voice_origin_ref"] not in dump
    assert "Deliberately edited and retained goal" in dump


def test_deterministic_goal_to_actual_files_survives_voice_end_and_restart(world):
    runtime, owner, _, clock = world
    ledger, ref, _, draft = selected(world)
    payload = request(world, goal=draft["text"], voice_origin_ref=draft["voice_origin_ref"])
    run = runtime.agent_runs.create(payload, "work-start", owner)["run"]
    assert run["voice_origin"]["edited"] is False
    ledger.end(ref)
    runtime.voice.work.cleanup()
    for _ in range(12):
        runtime.agent_runs.advance_one()
        clock[0] += timedelta(seconds=2)
    runtime.agent_runs = AgentRunService(runtime)
    detail = runtime.agent_runs.detail(run["id"], owner)
    assert detail["run"]["state"] == "succeeded"
    assert detail["run"]["model_calls"] == 0
    assert {a["format"] for a in detail["artifacts"]} == {"markdown", "csv"}
    session = runtime.agent_runs.session(owner)
    for artifact in detail["artifacts"]:
        metadata, body = runtime.artifacts.download(artifact["id"], session_hash=session)
        assert hashlib.sha256(body).hexdigest() == metadata["sha256"]
        assert b"synthetic.csv" in body
        if artifact["format"] == "markdown":
            assert b"review" in body
    assert runtime.agent_runs.detail(run["id"], owner)["run"]["voice_origin"] == run["voice_origin"]


def test_owner_http_route_strict_body_and_cookie_required(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    runtime = app.state.runtime
    runtime.voice.config = VoiceConfig("gemini", "", "protocol-fixture", "fake-only")
    client = TestClient(app)
    headers = {"X-Desk-Request": "1"}
    client.post(
        "/api/session", json={"username": "owner", "password": "fixture-only"}, headers=headers
    )
    owner = {"kind": "owner", "session": client.cookies.get("desk_companion_session")}
    ref = runtime.voice.work.begin(owner)
    event = observe(runtime.voice.work, ref)
    body = dict(
        voice_session_ref=ref, input_segment_id=event["input_segment_id"], expected_revision=1
    )
    response = client.post("/api/voice/work-drafts", json=body, headers=headers)
    assert response.status_code == 200 and response.json()["text"] == event["text"]
    assert (
        client.post(
            "/api/voice/work-drafts", json=body | {"text": "forged"}, headers=headers
        ).status_code
        == 422
    )
    assert TestClient(app).post(
        "/api/voice/work-drafts", json=body, headers=headers
    ).status_code in {401, 403}
    assert not runtime.agent_runs.listing(owner)["runs"]


def test_scope_change_at_final_admission_is_rejected(world, monkeypatch):
    from desk.tasks import TaskInput

    runtime, owner, _, _ = world
    payload = request(world)
    original = runtime.agent_runs._authorize

    def change(run):
        original(run)
        runtime.tasks.create(TaskInput(title="Changed scope"), "new-task")

    monkeypatch.setattr(runtime.agent_runs, "_authorize", change)
    with pytest.raises(DomainError, match="RUN_SCOPE_CHANGED"):
        runtime.agent_runs.create(payload, "scope-race", owner)


def test_actual_fake_socket_input_freeze_interrupt_end_keeps_independent_run(world):
    import asyncio
    import json
    import time
    from test_voice_context import Provider

    runtime, owner, _, _ = world
    runtime.voice.config = VoiceConfig(
        "qwen_audio",
        "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
        "protocol-fixture",
        "fake-only",
    )

    class SyntheticProvider(Provider):
        async def send(self, raw):
            await super().send(raw)
            if json.loads(raw).get("type") == "session.update":
                await self.queue.put(
                    {
                        "type": "conversation.item.input_audio_transcription.completed",
                        "item_id": "fake-item",
                        "transcript": "Synthetic audio protocol goal",
                    }
                )

    class SyntheticSocket:
        def __init__(self):
            self.messages, self.queue, self.run = [], asyncio.Queue(), None
            self.closed = False

        async def send_json(self, event):
            self.messages.append(event)
            if event["type"] == "voice_input":
                draft = freeze(world, runtime.voice.work, event)
                self.run = runtime.agent_runs.create(
                    request(world, voice_origin_ref=draft["voice_origin_ref"]),
                    "socket-start",
                    owner,
                )["run"]
                await self.queue.put({"type": "interrupt"})
            elif event["type"] == "interrupted":
                await self.queue.put({"type": "stop"})

        async def iter_text(self):
            while True:
                yield json.dumps(await self.queue.get())

        async def close(self):
            self.closed = True

    async def scenario():
        provider, socket = SyntheticProvider(), SyntheticSocket()
        runtime.voice.connector = lambda *args, **kwargs: provider
        runtime.voice.active, runtime.voice.started = True, time.monotonic()
        await asyncio.wait_for(runtime.voice.run(socket, owner, "en"), 4)
        assert socket.closed and not runtime.voice.active
        assert socket.run
        assert runtime.agent_runs.detail(socket.run["id"], owner)["run"]["state"] == "queued"
        assert any(
            json.loads(json.dumps(e)).get("type") == "response.cancel" for e in provider.sent
        )
        assert len([e for e in socket.messages if e["type"] == "voice_input"]) == 1
        assert all("input_key" not in e for e in socket.messages)
        assert runtime.voice.work.sessions
        assert all(not s["segments"] for s in runtime.voice.work.sessions.values())

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "name", ["work_start", "agent_run_create", "approve", "run_cancel", "memory_create"]
)
def test_invented_provider_controls_cannot_create_approve_or_control_work(world, name):
    import asyncio
    from desk.tool_dispatch import ToolDispatcher
    from desk.voice import VOICE_TOOLS

    runtime = world[0]
    assert name not in {t["name"] for t in VOICE_TOOLS}

    async def scenario():
        dispatcher = ToolDispatcher(runtime, "synthetic-session")
        try:
            dispatcher.submit(
                {
                    "id": "invented",
                    "name": name,
                    "arguments": {"goal": "TOOL_MARKER_NOT_A_VOICE_INPUT"},
                }
            )
            _, result = await asyncio.wait_for(dispatcher.results.get(), 3)
            assert result.get("error") and result.get("saved") is False
        finally:
            await dispatcher.close()

    asyncio.run(scenario())
    assert runtime.agent_runs.listing(world[1])["runs"] == []
    assert runtime.voice.work.drafts == {}


def test_model_payload_contains_reviewed_goal_not_origin_or_unselected_speech(world):
    from desk.agent_run_schemas import AgentDecision
    from desk.context import ContextSettings
    from desk.text_ai import TextConfig

    runtime, owner, source, clock = world
    runtime.text_ai.config = TextConfig(
        provider="gemini", model="scripted-text-model", api_key="fake-only"
    )
    current = runtime.personal_context.settings()
    dest = next(d["id"] for d in current["destinations"] if d["kind"] == "text")
    runtime.personal_context.update(
        ContextSettings(
            expected_version=current["version"],
            save_text_history=False,
            use_text_history_in_ai=False,
            use_memory_in_ai=False,
            approved_destinations=[dest],
        ),
        "scripted-work-consent",
    )
    ledger, ref, _, draft = selected(world, "RAW_VOICE_MARKER_264")
    observe(ledger, ref, "UNSELECTED_VOICE_MARKER_983", key="other", seq=2)
    observed = []
    decisions = [
        {"action": "plan", "plan": ["Inspect selected synthetic table"]},
        {"action": "read", "evidence_ids": ["source:" + source["id"]]},
        {"action": "ask", "question": "Synthetic owner question"},
    ]

    def generate(system, context, schema, purpose):
        observed.append(context)
        return AgentDecision.model_validate(decisions.pop(0))

    runtime.text_ai.generate = generate
    run = runtime.agent_runs.create(
        request(
            world,
            goal="REVIEWED_GOAL_ONLY",
            mode="model",
            provider_destination_id=dest,
            share_sources_with_provider=True,
            voice_origin_ref=draft["voice_origin_ref"],
        ),
        "model-start",
        owner,
    )["run"]
    for _ in range(5):
        runtime.agent_runs.advance_one()
        clock[0] += timedelta(seconds=2)
        if runtime.agent_runs.detail(run["id"], owner)["run"]["state"] == "waiting_input":
            break
    assert len(observed) == 3
    serialized = str(observed)
    assert "REVIEWED_GOAL_ONLY" in serialized and "synthetic.csv" in serialized
    assert all(
        s not in serialized
        for s in [
            "RAW_VOICE_MARKER",
            "UNSELECTED_VOICE_MARKER",
            "voice_origin",
            draft["voice_origin_ref"],
            "protocol-fixture",
            "qwen_audio",
        ]
    )
    assert run["provider_destination_id"] != run["voice_origin"]["destination_id"]


def test_forged_provenance_and_nonboolean_review_fields_fail(world):
    with pytest.raises(ValidationError):
        request(world, voice_origin={"channel": "voice", "edited": False})
    with pytest.raises(ValidationError):
        VoiceDraftFreeze(
            voice_session_ref="a" * 32, input_segment_id="b" * 32, expected_revision=True
        )


def test_provider_change_or_expired_owner_between_preflight_and_commit(world, monkeypatch):
    runtime, owner, _, _ = world
    _, _, _, draft = selected(world)
    payload = request(world, voice_origin_ref=draft["voice_origin_ref"])
    original = runtime.agent_runs._authorize

    def change(run):
        original(run)
        runtime.voice.config.model = "changed-at-boundary"

    monkeypatch.setattr(runtime.agent_runs, "_authorize", change)
    with pytest.raises(DomainError, match="VOICE_DRAFT_EXPIRED|VOICE_CONTEXT_CHANGED"):
        runtime.agent_runs.create(payload, "provider-race", owner)
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM agent_voice_origins").fetchone()[0] == 0


def test_voice_teardown_cannot_be_stranded_by_ledger_failure(world, monkeypatch):
    import asyncio
    import sqlite3
    import time
    from test_voice_context import Provider, Socket

    runtime, owner, _, _ = world
    runtime.voice.config = VoiceConfig(
        "qwen_audio",
        "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
        "protocol-fixture",
        "fake-only",
    )

    def fail_end(_):
        raise sqlite3.OperationalError("synthetic cleanup failure")

    monkeypatch.setattr(runtime.voice.work, "end", fail_end)

    async def scenario():
        provider, socket = Provider(), Socket()
        runtime.voice.connector = lambda *args, **kwargs: provider
        runtime.voice.active, runtime.voice.started = True, time.monotonic()
        await asyncio.wait_for(runtime.voice.run(socket, owner, "en"), 4)
        assert not runtime.voice.active and runtime.voice.started is None
        assert socket.closed

    asyncio.run(scenario())


def test_ledger_end_clears_unselected_text_without_database(world, monkeypatch):
    ledger, ref = voice(world)
    observe(ledger, ref, "VOLATILE_END_MARKER")

    def unavailable(*args, **kwargs):
        raise AssertionError("Transport cleanup must not use SQLite")

    monkeypatch.setattr(world[0].store, "connection", unavailable)
    ledger.end(ref)
    assert not ledger.sessions and not ledger.drafts


def test_clock_rollback_cannot_extend_frozen_plaintext_lifetime(world, monkeypatch):
    monotonic = [100.0]
    monkeypatch.setattr("desk.voice_work.time.monotonic", lambda: monotonic[0])
    ledger, ref, _, draft = selected(world, "ROLLBACK_EXPIRES_MARKER")
    ledger.end(ref)
    world[3][0] -= timedelta(hours=1)
    monotonic[0] += 301
    ledger.cleanup()
    assert not ledger.drafts and not ledger.sessions
    with pytest.raises(DomainError, match="VOICE_DRAFT_EXPIRED"):
        world[0].agent_runs.create(
            request(world, voice_origin_ref=draft["voice_origin_ref"]), "rollback-expired", world[1]
        )


def test_malformed_utf8_cannot_mutate_sequence_or_erase_existing_input(world):
    ledger, ref = voice(world, "gemini")
    one = observe(ledger, ref, "valid", boundary="unfinalized", operation="append")
    assert observe(ledger, ref, "\ud800", seq=2, boundary="unfinalized", operation="append") is None
    assert observe(ledger, ref, "valid", key="\ud800", seq=2) is None
    state = ledger.sessions[ref]
    assert state["sequence"] == 1
    assert next(iter(state["segments"].values())) == one
    assert freeze(world, ledger, one)["text"] == "valid"
    protocol = QwenAudioProtocol()
    assert (
        protocol.events(
            {
                "type": "conversation.item.input_audio_transcription.completed",
                "transcript": "\ud800",
            }
        )
        == []
    )
    assert protocol.input_sequence == 0

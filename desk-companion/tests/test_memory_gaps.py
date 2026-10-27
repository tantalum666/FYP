"""Backup of owner memory, local session cleanup, and review beyond exact wording."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from desk.access import digest
from desk.exchange import BackupInput, ImportApply
from desk.runtime import Runtime
from desk.store import DomainError, Store, encode


def _runtime(tmp_path, clock=None):
    return Runtime(
        Store(
            tmp_path,
            password="fixture-only",
            clock=clock or (lambda: datetime(2026, 10, 2, tzinfo=UTC)),
        )
    )


def test_backup_restores_missing_facts_and_keeps_a_newer_local_correction(tmp_path):
    clock = [datetime(2026, 10, 2, tzinfo=UTC)]
    runtime = _runtime(tmp_path / "source", clock=lambda: clock[0])
    saved = runtime.memory.create("I prefer tea", "save")["memory"]
    clock[0] += timedelta(seconds=1)
    runtime.memory.replace(saved["id"], "I prefer tea without sugar", saved["version"], "edit")
    forgotten = runtime.memory.create("Secret code 42", "secret")["memory"]
    runtime.memory.delete(forgotten["id"], forgotten["version"], "forget-secret")
    backup = runtime.exchange.backup()
    assert "I prefer tea without sugar" in json.dumps(backup["payload"]["memory_bundle"])
    assert "Secret code 42" not in json.dumps(backup)
    restored = _runtime(tmp_path / "restored", clock=lambda: clock[0])
    preview = restored.exchange.preview_backup(BackupInput(content=json.dumps(backup)), "preview")
    assert preview["metadata"]["memories_count"] == 1
    applied = restored.exchange.apply(preview["preview_id"], ImportApply(), "restore")
    assert applied["memories_created"] == 1 and applied["memories_kept"] == 0
    current = restored.memory.listing()["memories"][0]
    assert current["body"] == "I prefer tea without sugar"
    assert current["previous_body"] == "I prefer tea"
    again = restored.exchange.preview_backup(BackupInput(content=json.dumps(backup)), "second")
    assert (
        restored.exchange.apply(again["preview_id"], ImportApply(), "second-restore")[
            "memories_created"
        ]
        == 0
    )
    restored.memory.replace(current["id"], "I prefer coffee", current["version"], "local")
    third = restored.exchange.preview_backup(BackupInput(content=json.dumps(backup)), "third")
    restored.exchange.apply(third["preview_id"], ImportApply(), "third-restore")
    assert restored.memory.listing()["memories"][0]["body"] == "I prefer coffee"
    legacy = json.loads(json.dumps(backup))
    legacy["payload"].pop("memory_bundle")
    legacy["sha256"] = digest(encode(legacy["payload"]))
    legacy_preview = restored.exchange.preview_backup(
        BackupInput(content=json.dumps(legacy)), "legacy"
    )
    assert legacy_preview["metadata"]["memories_count"] == 0
    broken = json.loads(json.dumps(backup))
    broken["payload"]["memory_bundle"]["memories"][0]["body"] = "tampered"
    with pytest.raises(DomainError, match="INVALID_BACKUP"):
        restored.exchange.preview_backup(BackupInput(content=json.dumps(broken)), "tampered")


def test_restore_refuses_to_pass_the_active_memory_cap(tmp_path):
    source = _runtime(tmp_path / "source")
    source.memory.create("I prefer tea", "one")
    document = json.dumps(source.exchange.backup())
    full = _runtime(tmp_path / "full")
    now = "2026-10-02T00:00:00.000000Z"
    with full.store.connection(write=True) as conn:
        for index in range(200):
            conn.execute(
                "INSERT INTO owner_memories("
                "id, body, source, state, version, created_at, updated_at, attribution"
                ") VALUES(?,?,?,'active',1,?,?, '')",
                (uuid4().hex, f"Saved fact {index}", "owner", now, now),
            )
    preview = full.exchange.preview_backup(BackupInput(content=document), "preview")
    with pytest.raises(DomainError, match="MEMORY_LIMIT"):
        full.exchange.apply(preview["preview_id"], ImportApply(), "restore")
    assert len(full.memory.listing()["memories"]) == 200


def test_forgetting_clears_local_provider_copies_and_closes_a_live_voice_session(tmp_path):
    runtime = _runtime(tmp_path)
    fact = runtime.memory.create("I prefer tea without sugar", "save")["memory"]
    runtime.assistant.propose(
        "memory_save",
        {"body": "I prefer tea without sugar", "memory_id": fact["id"]},
        "draft",
    )
    with runtime.store.connection(write=True) as conn:
        conn.execute(
            "INSERT INTO assistant_replies VALUES(?,?,?)",
            (
                "cached-reply",
                "hash",
                json.dumps({"message": "Noted: I prefer tea without sugar", "id": fact["id"]}),
            ),
        )
        conn.execute(
            "INSERT INTO assistant_replies VALUES(?,?,?)",
            ("unrelated", "hash-2", json.dumps({"message": "The lamp is on"})),
        )
        conn.execute(
            "INSERT INTO assistant_replies VALUES(?,?,?)",
            ("short-equal", "hash-3", json.dumps({"message": "Tea"})),
        )
    runtime.voice.active = True
    result = runtime.memory.delete(fact["id"], fact["version"], "forget")
    assert result["local_session"]["replies_removed"] == 1
    assert result["local_session"]["proposals_cleared"] == 1
    assert result["live_voice_closed"] is True
    assert runtime.voice.forget_session.is_set()
    with runtime.store.connection() as conn:
        left = {row["id"] for row in conn.execute("SELECT id FROM assistant_replies")}
        proposal = conn.execute("SELECT state, data FROM assistant_proposals").fetchone()
    assert left == {"unrelated", "short-equal"}
    assert proposal["state"] == "cancelled"
    assert "I prefer tea without sugar" not in proposal["data"]
    assert runtime.memory.for_model() == []
    runtime.voice.active = False
    assert runtime.voice.drop_live_session() is False
    assert not runtime.voice.forget_session.is_set()


def test_same_subject_preferences_and_names_are_reviewable_without_a_model(tmp_path):
    clock = [datetime(2026, 10, 2, tzinfo=UTC)]
    runtime = _runtime(tmp_path, clock=lambda: clock[0])

    def save(body):
        clock[0] += timedelta(seconds=1)
        return runtime.memory.create(body, uuid4().hex)["memory"]

    tea = save("I prefer tea")
    detailed = save("I prefer tea without sugar")
    suggestion = runtime.memory.listing()["suggestions"][0]
    assert suggestion["kind"] == "preference"
    assert suggestion["keep"]["id"] == detailed["id"]
    assert "tea" in suggestion["reason_en"]
    draft = runtime.memory.prepare_consolidation(
        suggestion["keep"]["id"], [row["id"] for row in suggestion["retire"]], "review"
    )
    runtime.assistant.decide(draft["proposal"]["id"], "confirm", "confirm")
    assert [row["body"] for row in runtime.memory.for_model()] == ["I prefer tea without sugar"]
    assert runtime.memory.listing()["retired"][0]["id"] == tea["id"]

    save("I prefer short answers")
    assert runtime.memory.listing()["suggestions"] == []
    save("I prefer team meetings")
    assert runtime.memory.listing()["suggestions"] == []

    save("I prefer oolong")
    save("I always prefer oolong")
    normalized = runtime.memory.listing()["suggestions"][0]
    assert normalized["kind"] == "normalized"
    assert "filler" in normalized["reason_en"]

    save("My name is Yuan")
    save("My name is Ada")
    identity = next(
        item for item in runtime.memory.listing()["suggestions"] if item["kind"] == "identity"
    )
    assert identity["keep"]["body"] == "My name is Ada"
    assert "name" in identity["reason_en"]
    with pytest.raises(DomainError, match="MEMORY_REVIEW_STALE"):
        runtime.memory.prepare_consolidation(tea["id"], [detailed["id"]], "stale")

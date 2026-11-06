"""Volatile server-observed voice snapshots, never speaker identity or authority.

Lock order: personal-context lock, ledger lock, SQLite transaction. No network or
provider dispatch occurs here. Only explicit run admission can retain provenance.
"""

import hashlib
import threading
import time
from datetime import timedelta
from uuid import uuid4

from pydantic import Field

from .calendar import iso
from .personal_context import fingerprint
from .schemas import StrictModel
from .store import DomainError

SEGMENT_LIMIT = 8
DRAFT_LIMIT = 4
TEXT_BYTES = 32768
TEXT_CHARS = 4000
TTL_SECONDS = 300


class VoiceDraftFreeze(StrictModel):
    voice_session_ref: str = Field(pattern=r"^[a-f0-9]{32}$")
    input_segment_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    expected_revision: int = Field(ge=1, strict=True)


class VoiceWorkLedger:
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.lock = threading.RLock()
        self.sessions, self.drafts = {}, {}

    def transport(self):
        cfg = self.runtime.voice.config
        if not cfg.valid():
            return None
        destination = next(
            (d for d in self.runtime.personal_context.destinations() if d["kind"] == "voice"), None
        )
        if not destination:
            return None
        return {"provider": cfg.provider, "model": cfg.model, "destination_id": destination["id"]}

    def config_revision(self):
        return fingerprint(self.transport())

    def _revision(self, conn):
        return fingerprint(
            [
                conn.execute("SELECT epoch FROM personal_settings WHERE id=1").fetchone()[0],
                self.store.settings(conn)["version"],
                [d["id"] for d in self.runtime.personal_context.destinations()],
            ]
        )

    def _owner(self, conn, principal):
        if (
            not principal
            or principal.get("kind") != "owner"
            or not isinstance(principal.get("session"), str)
            or not principal["session"]
        ):
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        digest = hashlib.sha256(principal["session"].encode()).hexdigest()
        self._authority(conn, digest)
        return digest

    def _authority(self, conn, digest):
        if not conn.execute(
            "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
            (digest, iso(self.store.clock())),
        ).fetchone():
            raise DomainError("RUN_SESSION_EXPIRED", 403)
        if self.store.settings(conn)["hide_private"]:
            raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)

    def _check(self, conn, state, session_hash=None):
        self._authority(conn, state["session_hash"])
        if session_hash is not None and state["session_hash"] != session_hash:
            raise DomainError("VOICE_CONTEXT_CHANGED", 403)
        if (
            state["privacy_revision"] != self._revision(conn)
            or state["transport"] != self.transport()
        ):
            raise DomainError("VOICE_CONTEXT_CHANGED", 409)

    def _purge(self, conn):
        now, monotonic_now = iso(self.store.clock()), time.monotonic()
        for ref, draft in list(self.drafts.items()):
            if draft["expires_at"] <= now or draft["expires_monotonic"] <= monotonic_now:
                del self.drafts[ref]
        for ref, state in list(self.sessions.items()):
            try:
                self._check(conn, state)
            except DomainError:
                self.drafts = {k: d for k, d in self.drafts.items() if d["session_ref"] != ref}
                del self.sessions[ref]
                continue
            if state["ended_at"] and not any(d["session_ref"] == ref for d in self.drafts.values()):
                del self.sessions[ref]

    def cleanup(self):
        with self.runtime.personal_context.lock, self.lock, self.store.connection() as conn:
            self._purge(conn)

    def begin(self, principal):
        """Legacy paired/agent/hidden voice still works, without an owner ledger."""
        with self.runtime.personal_context.lock, self.lock, self.store.connection() as conn:
            self._purge(conn)
            try:
                session = self._owner(conn, principal)
            except DomainError:
                return None
            transport = self.transport()
            if transport is None:
                return None
            if any(not state["ended_at"] for state in self.sessions.values()):
                raise DomainError("VOICE_BUSY", 409)
            ref = uuid4().hex
            self.sessions[ref] = {
                "session_hash": session,
                "privacy_revision": self._revision(conn),
                "transport": transport,
                "segments": {},
                "seen": set(),
                "sequence": 0,
                "ended_at": None,
            }
            return ref

    def _size(self, state, *, extra=None):
        # Immutable snapshot strings shared by a segment and draft count once.
        values = {
            (s["input_segment_id"], s["revision"]): s["text"] for s in state["segments"].values()
        }
        for d in self.drafts.values():
            if self.sessions.get(d["session_ref"]) is state:
                values[(d["input_segment_id"], d["revision"])] = d["text"]
        if extra:
            values[(extra["input_segment_id"], extra["revision"])] = extra["text"]
        return sum(len(text.encode("utf-8")) for text in values.values())

    def observe(self, session_ref, event):
        """Accept adapter-owned input updates only, never arbitrary provider tools."""
        if not session_ref or event.get("type") != "transcript" or event.get("role") != "user":
            return None
        operation, boundary = event.get("input_operation"), event.get("boundary")
        text, key = event.get("text"), event.get("input_key")
        sequence = event.get("input_sequence")
        if (
            operation not in {"append", "replace"}
            or boundary not in {"provider_final", "unfinalized"}
            or not isinstance(text, str)
            or not isinstance(key, str)
            or not 1 <= len(key) <= 256
            or type(sequence) is not int
            or sequence < 1
        ):
            return None
        try:
            text.encode("utf-8")
            key.encode("utf-8")
        except UnicodeEncodeError:
            return None  # Validate before sequence, eviction or segment mutation.
        with self.runtime.personal_context.lock, self.lock, self.store.connection() as conn:
            self._purge(conn)
            state = self.sessions.get(session_ref)
            if not state or state["ended_at"]:
                raise DomainError("VOICE_CONTEXT_CHANGED", 409)
            self._check(conn, state)
            if sequence <= state["sequence"]:
                return None
            state["sequence"] = sequence
            key = fingerprint(key)  # Untrusted correlation, never public ID or authority.
            old = state["segments"].get(key)
            if old is None:
                if key in state["seen"]:
                    return None
                if len(state["seen"]) >= 128:
                    raise DomainError("VOICE_INPUT_LIMIT", 422)
                state["seen"].add(key)
                if len(state["segments"]) >= SEGMENT_LIMIT:
                    del state["segments"][next(iter(state["segments"]))]
            elif old["boundary"] == "provider_final" and old["eligible"]:
                if operation == "replace" and text == old["text"] and boundary == "provider_final":
                    return None
                # A contradictory final is no longer a selectable observation.
                text, operation = "", "replace"
            if old and not old["eligible"]:
                return None  # Overflow/contradiction cannot become a tail-only candidate.
            value = (old["text"] if old and operation == "append" else "") + text
            segment = {
                "type": "voice_input",
                "voice_session_ref": session_ref,
                "input_segment_id": old["input_segment_id"] if old else uuid4().hex,
                "revision": old["revision"] + 1 if old else 1,
                "sequence": sequence,
                "role": "user",
                "text": value,
                "operation": "replace",
                "boundary": boundary,
                "eligible": bool(value.strip()),
                "reason": None,
                "observed_at": iso(self.store.clock()),
                **state["transport"],
            }
            prior = state["segments"].pop(key, None)
            oversized = len(value) > TEXT_CHARS or self._size(state, extra=segment) > TEXT_BYTES
            if oversized or not value.strip():
                segment.update(
                    text="",
                    eligible=False,
                    reason="VOICE_INPUT_TOO_LARGE" if oversized else "VOICE_INPUT_INVALID",
                )
            state["segments"][key] = segment
            del prior
            return dict(segment)

    def freeze(self, payload, principal):
        with self.runtime.personal_context.lock, self.lock, self.store.connection() as conn:
            session = self._owner(conn, principal)
            self._purge(conn)
            state = self.sessions.get(payload.voice_session_ref)
            if not state:
                raise DomainError("VOICE_DRAFT_EXPIRED", 410)
            self._check(conn, state, session)
            for draft in self.drafts.values():
                if (
                    draft["session_ref"] == payload.voice_session_ref
                    and draft["input_segment_id"] == payload.input_segment_id
                    and draft["revision"] == payload.expected_revision
                ):
                    return self._draft_view(draft)
            segment = next(
                (
                    s
                    for s in state["segments"].values()
                    if s["input_segment_id"] == payload.input_segment_id
                ),
                None,
            )
            if not segment or segment["revision"] != payload.expected_revision:
                raise DomainError("VOICE_INPUT_CHANGED", 409)
            if not segment["eligible"]:
                raise DomainError(segment["reason"] or "VOICE_INPUT_INVALID", 422)
            if len(self.drafts) >= DRAFT_LIMIT:
                raise DomainError("VOICE_DRAFT_LIMIT", 422)
            now = self.store.clock()
            draft = {
                **segment,
                "voice_origin_ref": uuid4().hex,
                "session_ref": payload.voice_session_ref,
                "owner_reviewed_at": iso(now),
                "expires_at": iso(now + timedelta(seconds=TTL_SECONDS)),
                "expires_monotonic": time.monotonic() + TTL_SECONDS,
                "snapshot_kind": "owner_snapshot",
            }
            self.drafts[draft["voice_origin_ref"]] = draft
            return self._draft_view(draft)

    @staticmethod
    def _draft_view(draft):
        return {
            k: draft[k]
            for k in (
                "voice_origin_ref",
                "text",
                "revision",
                "boundary",
                "provider",
                "model",
                "destination_id",
                "observed_at",
                "owner_reviewed_at",
                "expires_at",
                "snapshot_kind",
            )
        }

    def reviewed_text(self, ref, principal) -> str | None:
        """Live owner snapshot text. Missing or expired is None. Does not steer or start work."""
        with self.runtime.personal_context.lock, self.lock, self.store.connection() as conn:
            session = self._owner(conn, principal)
            self._purge(conn)
            draft = self.drafts.get(ref)
            if not draft:
                return None
            state = self.sessions.get(draft["session_ref"])
            if state is None:
                return None
            self._check(conn, state, session)
            return draft["text"]

    def resolve(self, ref, *, session_hash, goal, conn):
        """Caller holds personal lock + ledger lock + its atomic create transaction."""
        self._purge(conn)
        draft = self.drafts.get(ref)
        if not draft:
            raise DomainError("VOICE_DRAFT_EXPIRED", 410)
        state = self.sessions.get(draft["session_ref"])
        if state is None:
            raise DomainError("VOICE_DRAFT_EXPIRED", 410)
        self._check(conn, state, session_hash)
        return {
            "channel": "voice",
            **state["transport"],
            "observed_at": draft["observed_at"],
            "boundary": draft["boundary"],
            "owner_reviewed_at": draft["owner_reviewed_at"],
            "retained_at": iso(self.store.clock()),
            "edited": goal != draft["text"],
            "snapshot_kind": "owner_snapshot",
        }

    def end(self, session_ref):
        """Transport cleanup cannot depend on SQLite availability or privacy locks."""
        if not session_ref:
            return
        with self.lock:
            state = self.sessions.get(session_ref)
            if state:
                state["ended_at"] = iso(self.store.clock())
                state["segments"].clear()
                state["seen"].clear()
                if not any(d["session_ref"] == session_ref for d in self.drafts.values()):
                    del self.sessions[session_ref]

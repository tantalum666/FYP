"""OpenAI-default text reasoning with optional Qwen/Gemini adapters.

Persistent memory is owner-reviewed facts plus confirmed tasks. Deleted facts are omitted.
The model can only prepare proposals; background advice cannot mutate task or memory state.
"""

import hashlib
import json
import os
import re
import threading
from queue import Queue
from dataclasses import dataclass, field as dataclass_field
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from .openai_transport import model_proxy, validate_openai_proxy
from pydantic import Field, ValidationError

from .agent_loop import AgentLoop
from .bounded_json import (
    TEXT_NETWORK_TIMEOUT,
    TEXT_RESPONSE_BYTES as TEXT_RESPONSE_BYTES,
    bounded_json_post as bounded_json_post,
    TextDispatchRefused,
    _DISPATCH_CHECKPOINT,
    _request_checkpoint,
)
from .provider_policy import (
    GEMINI_TEXT_ENDPOINT,
    OPENAI_TEXT_ENDPOINT,
    valid_api_key,
    valid_model,
    valid_provider_endpoint,
)
from .calendar import iso
from .context import pack_conversation
from .conversation import memory_context, task_context
from .turns import remember_exchange
from .model_provider import HostedTextProvider
from .memory_extract import EXTRACT_INSTRUCTIONS, accept_stated_fact
from .reply_stream import audit_events, sse_encode, text_chunks
from .retention import retired_reply_key
from .token_stream import extract_message
from .style import present, render_prompt
from .text_providers import text_adapter
from .voice_credentials import openai_key
from .workspace_data import is_quiet
from .schemas import StrictModel
from .store import DomainError, encode
from .tool_policy import tool_visible
from .chat_attachments import ChatAttachments, FILE_POLICY, capability as attachment_capability

DEFAULT_DAILY_CAP = 40
MAX_DAILY_CAP = 500


class TextPlan(StrictModel):
    message: str = Field(min_length=1, max_length=2000)
    tool: Literal[
        "none",
        "task_query",
        "task_details",
        "task_create_draft",
        "task_change_draft",
        "calendar_query",
        "calendar_create_draft",
        "calendar_change_draft",
        "computer_job_draft",
        "computer_job_status",
        "computer_job_cancel",
        "memory_query",
        "memory_save_draft",
        "memory_replace_draft",
        "memory_delete_draft",
        "owner_search",
        "plate_summary",
        "owner_clock",
        "propose_plan",
    ] = "none"
    arguments: dict = Field(default_factory=dict)


class FollowUpAdvice(StrictModel):
    en: str = Field(min_length=1, max_length=600)
    zh: str = Field(min_length=1, max_length=600)


class ExtractedFact(StrictModel):
    body: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=160)


class ExtractionResult(StrictModel):
    fact: ExtractedFact | None = None


def configured_extract_cap() -> int:
    """Hosted extraction stays off until both the flag and a positive cap are set."""
    if os.environ.get("DESK_MEMORY_EXTRACT") != "1":
        return 0
    raw = os.environ.get("DESK_MEMORY_EXTRACT_CAP", "0")
    if not re.fullmatch(r"\d{1,2}", raw):
        return 0
    return min(int(raw), 20)


@dataclass
class TextConfig:
    provider: str = "none"
    model: str = ""
    endpoint: str = ""
    api_key: str = dataclass_field(default="", repr=False)
    background: bool = False
    extract_cap: int = 0
    configuration_error: str = ""
    proxy_url: str = ""

    @classmethod
    def environment(cls):
        config = cls(
            *(
                os.environ.get("DESK_TEXT_" + key, default)
                for key, default in [
                    ("PROVIDER", "openai"),
                    ("MODEL", ""),
                    ("ENDPOINT", ""),
                    ("API_KEY", ""),
                ]
            ),
            background=os.environ.get("DESK_TEXT_BACKGROUND") == "1",
            extract_cap=configured_extract_cap(),
        )
        if config.provider == "openai":
            config.proxy_url = os.environ.get("DESK_OPENAI_PROXY_URL", "")
            try:
                validate_openai_proxy(config.proxy_url)
            except ValueError:
                config.configuration_error = "OPENAI_PROXY_INVALID"
            config.model = config.model or "gpt-6.1-sol"
            config.endpoint = config.endpoint or OPENAI_TEXT_ENDPOINT
            path = os.environ.get("DESK_OPENAI_CREDENTIAL_FILE")
            if path:
                try:
                    config.api_key = openai_key(path)
                except (ValueError, OSError, UnicodeError):
                    config.api_key = ""
                    config.configuration_error = "TEXT_CREDENTIALS_INVALID"
            elif not config.api_key or "DESK_TEXT_PROVIDER" not in os.environ:
                config.api_key = os.environ.get("OPENAI_API_KEY", "")
            if os.environ.get("DESK_OPENAI_REGION_UNSUPPORTED") == "1":
                config.configuration_error = "OPENAI_REGION_UNSUPPORTED"
        return config

    def valid(self):
        # Offline demonstration only. The fake adapter never reads the API key.
        if self.provider == "fake":
            return True
        try:
            model_proxy(self)
        except ValueError:
            return False
        return (
            not self.configuration_error
            and valid_model(self.model)
            and valid_api_key(self.api_key)
            and valid_provider_endpoint(self.provider, self.endpoint, kind="text")
        )


class TextAssistant:
    def __init__(self, runtime, config=None, transport=None):
        self.runtime, self.store = runtime, runtime.store
        self.config = config or TextConfig.environment()
        self.transport = transport
        self.lock = threading.RLock()
        self.background_lock = threading.Lock()
        self.attachments = ChatAttachments(runtime)
        with self.store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS assistant_replies(id TEXT PRIMARY KEY,request_hash TEXT NOT NULL,result TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS text_ai_usage(id TEXT PRIMARY KEY,at TEXT NOT NULL,purpose TEXT NOT NULL,provider TEXT NOT NULL,usage TEXT NOT NULL)"
            )

    def snapshot(self):
        return {
            "configured": self.config.valid(),
            "provider": self.config.provider,
            "model": self.config.model,
            "background": self.config.valid() and self.config.background,
            "configuration_error": self.config.configuration_error,
            "attachments": attachment_capability(self.config),
        }

    def daily_cap(self) -> int:
        raw = os.environ.get("DESK_TEXT_DAILY_CAP", str(DEFAULT_DAILY_CAP))
        if not raw.isdigit():
            return DEFAULT_DAILY_CAP
        value = int(raw)
        if not 1 <= value <= MAX_DAILY_CAP:
            return DEFAULT_DAILY_CAP
        return value

    def conversation_calls_today(self) -> int:
        today = iso(self.store.clock())[:10]
        with self.store.connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM text_ai_usage WHERE purpose='conversation' AND at>=?",
                (today,),
            ).fetchone()[0]

    def _reserve_usage(self, purpose):
        """Reserve every provider attempt atomically, including streaming fallback."""
        from uuid import uuid4

        usage_id = uuid4().hex
        now = iso(self.store.clock())
        with self.store.connection(write=True) as conn:
            if (
                purpose in {"conversation", "computer_use"}
                and conn.execute(
                    "SELECT COUNT(*) FROM text_ai_usage WHERE purpose IN ('conversation','computer_use') AND at>=?",
                    (now[:10],),
                ).fetchone()[0]
                >= self.daily_cap()
            ):
                raise DomainError("TEXT_AI_CAP", 429)
            conn.execute(
                "INSERT INTO text_ai_usage VALUES(?,?,?,?,?)",
                (usage_id, now, purpose, self.config.provider, "{}"),
            )
        return usage_id

    def generate_guarded(self, system, context, schema, purpose, *, checkpoint):
        """Preserve the generate test/provider seam while fencing real HTTP dispatch."""
        config = self.config
        expected_url = (
            config.endpoint
            if config.provider in {"qwen", "openai"}
            else (
                (config.endpoint or GEMINI_TEXT_ENDPOINT)
                + "/models/"
                + config.model
                + ":generateContent"
            )
        )

        def guard(request=None):
            try:
                checkpoint()
                if request is not None and str(request.url) != expected_url:
                    raise DomainError("PROVIDER_CONTEXT_NOT_APPROVED", 403)
            except DomainError as exc:
                raise TextDispatchRefused(exc.code, exc.status) from None

        guard()  # Includes schema/context construction done by the run planner.
        token = _DISPATCH_CHECKPOINT.set(guard)
        try:
            return self.generate(system, context, schema, purpose)
        finally:
            _DISPATCH_CHECKPOINT.reset(token)

    def generate(
        self, system, context, schema, purpose, *, attachment_parts=None, attachment_guard=None
    ):
        if not self.config.valid():
            raise DomainError("TEXT_AI_NOT_CONFIGURED", 503)
        if attachment_parts and self.config.provider != "openai":
            raise DomainError("CHAT_FILES_UNAVAILABLE", 409)
        if attachment_guard:
            attachment_guard()
        prompt = (
            system
            + "\nReturn only JSON matching this schema: "
            + encode(schema.model_json_schema())
        )
        content = encode(context)
        usage_id = self._reserve_usage(purpose)
        try:
            with httpx.Client(
                timeout=TEXT_NETWORK_TIMEOUT,
                transport=self.transport,
                follow_redirects=False,
                trust_env=False,
                proxy=model_proxy(self.config, self.transport),
                event_hooks={
                    "request": [
                        _request_checkpoint,
                        *([attachment_guard] if attachment_guard else []),
                    ]
                },
            ) as client:
                raw, usage = text_adapter(self.config.provider).complete(
                    client,
                    self.config,
                    prompt,
                    content,
                    **({"attachment_parts": attachment_parts} if attachment_parts else {}),
                )
                if not isinstance(raw, str) or len(raw) > 20000:
                    raise ValueError()
                parsed = schema.model_validate_json(raw)
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            AttributeError,
            RecursionError,
            ValidationError,
        ):
            raise DomainError("TEXT_AI_UNAVAILABLE", 503) from None
        # Store numeric usage only; never log provider responses, prompts, or secrets.
        safe_usage = (
            {
                k: v
                for k, v in usage.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            }
            if isinstance(usage, dict)
            else {}
        )
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE text_ai_usage SET usage=? WHERE id=?", (encode(safe_usage), usage_id)
            )
        return parsed

    def generate_live(
        self,
        system,
        context,
        schema,
        purpose,
        on_delta,
        *,
        attachment_parts=None,
        attachment_guard=None,
    ):
        """Stream provider deltas. Each actual fallback consumes its own call slot."""
        if self.config.valid() and not hasattr(text_adapter(self.config.provider), "deltas"):
            return self.generate(
                system,
                context,
                schema,
                purpose,
                **(
                    {"attachment_parts": attachment_parts, "attachment_guard": attachment_guard}
                    if attachment_parts
                    else {}
                ),
            ), False
        if attachment_parts:
            raise DomainError("CHAT_FILES_UNAVAILABLE", 409)
        if not self.config.valid():
            raise DomainError("TEXT_AI_NOT_CONFIGURED", 503)
        prompt = (
            system
            + "\nReturn only JSON matching this schema: "
            + encode(schema.model_json_schema())
        )
        content = encode(context)
        usage_id = self._reserve_usage(purpose)
        streamed = False
        try:
            with httpx.Client(
                timeout=TEXT_NETWORK_TIMEOUT,
                transport=self.transport,
                follow_redirects=False,
                trust_env=False,
                proxy=model_proxy(self.config, self.transport),
                event_hooks={"request": [_request_checkpoint]},
            ) as client:
                adapter = text_adapter(self.config.provider)
                try:
                    raw, usage, streamed = _read_deltas(
                        adapter, client, self.config, prompt, content, on_delta
                    )
                except _StreamFailed:
                    usage_id = self._reserve_usage(purpose)
                    raw, usage = adapter.complete(client, self.config, prompt, content)
                    streamed = False
                if not isinstance(raw, str) or len(raw) > 20000:
                    raise ValueError()
                parsed = schema.model_validate_json(raw)
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            IndexError,
            TypeError,
            AttributeError,
            RecursionError,
            ValidationError,
        ):
            raise DomainError("TEXT_AI_UNAVAILABLE", 503) from None
        safe_usage = (
            {
                k: v
                for k, v in usage.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            }
            if isinstance(usage, dict)
            else {}
        )
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE text_ai_usage SET usage=? WHERE id=?", (encode(safe_usage), usage_id)
            )
        return parsed, streamed

    def context(self, task_id=None, *, include_memory=True, user_message="", conversation=None):
        return pack_conversation(
            self.runtime,
            task_id,
            include_memory=include_memory,
            user_message=user_message,
            conversation=conversation,
        )

    def message(self, payload, key, *, allow_memory=True, on_event=None, principal=None):
        # Serialize receipt lookup, action application and reply persistence together.
        # A duplicate arriving during a permission change must not gain a new grant.
        with self.lock:
            return self._scoped_message(
                payload, key, allow_memory=allow_memory, on_event=on_event, principal=principal
            )

    def _scoped_message(self, payload, key, *, allow_memory=True, on_event=None, principal=None):
        if not key or len(key) > 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)
        conversation = None
        cached = None
        grant = self.runtime.permissions.capture(principal, payload.task_id)
        if principal is not None:
            task_context(self.runtime, principal, payload.task_id)
            # Durable business receipts follow the principal, while temporary
            # chat replay follows the specific login session and selected task.
            scope = f"{principal.get('kind')}:{principal.get('id', 'owner')}"
            key = "chat/" + hashlib.sha256(f"{scope}/{key}".encode()).hexdigest()
            cached = self._cached_reply(payload, key, allow_memory)
            revision, _ = memory_context(self.runtime, allow_memory)
            try:
                conversation = self.runtime.voice.conversations.open(
                    principal, revision, payload.conversation_id, task_id=payload.task_id
                )
            except DomainError as error:
                if error.code != "CONVERSATION_NOT_FOUND" or cached is None:
                    raise
                # The same authorized owner can recover an acknowledged
                # operation after signing in again. Never replay the old chat.
                conversation = self.runtime.voice.conversations.open(
                    principal, revision, task_id=payload.task_id
                )
        admitted = None
        if cached is None:
            self.attachments.select(conversation, payload.attachment_ids, principal)
        if cached is None and principal is not None:
            # An explicit goal change is owner authority. It never reaches the model.
            admitted = self.runtime.conversation_work.turn(payload, key, principal)
        if cached is not None:
            reply = cached
        elif admitted is not None:
            reply = present(admitted, self.runtime.data.preferences(), payload.language)
            with self.store.connection(write=True) as conn:
                conn.execute(
                    "INSERT INTO assistant_replies VALUES(?,?,?)",
                    (key, self._fingerprint(payload, allow_memory), encode(reply)),
                )
        else:
            reply = self._message(
                payload,
                key,
                allow_memory=allow_memory,
                on_event=on_event,
                conversation=conversation,
            )
        reply = (
            self.runtime.permissions.apply_reply(reply, grant, language=payload.language)
            if cached is None
            else self.runtime.permissions.refresh_reply(reply, language=payload.language)
        )
        with self.store.connection(write=True) as conn:
            conn.execute("UPDATE assistant_replies SET result=? WHERE id=?", (encode(reply), key))
        if cached is None:
            remember_exchange(
                self.runtime,
                key,
                payload.message,
                str(reply.get("message") or ""),
                conversation=conversation,
            )
        if conversation is not None:
            reply = {**reply, "conversation_id": conversation.id}
        return reply

    @staticmethod
    def _fingerprint(payload, allow_memory):
        # Absent review-screen fields stay out of the hash so older receipts still match.
        body = payload.model_dump()
        if not body.get("voice_origin_ref"):
            body.pop("voice_origin_ref", None)
        if body.get("voice_steer") is not True:
            body.pop("voice_steer", None)
        if not body.get("steer_run_id"):
            body.pop("steer_run_id", None)
        if not body.get("attachment_ids"):
            body.pop("attachment_ids", None)
        return hashlib.sha256(encode({**body, "allow_memory": allow_memory}).encode()).hexdigest()

    def _cached_reply(self, payload, key, allow_memory):
        with self.store.connection() as conn:
            old = conn.execute("SELECT * FROM assistant_replies WHERE id=?", (key,)).fetchone()
            retired = (
                conn.execute(
                    "SELECT request FROM operations WHERE id=?", (retired_reply_key(key),)
                ).fetchone()
                if old is None
                else None
            )
        if old:
            if old["request_hash"] != self._fingerprint(payload, allow_memory):
                raise DomainError("OPERATION_ID_CONFLICT")
            return json.loads(old["result"])
        if retired:
            marker = json.loads(retired["request"])
            if marker.get("type") != "assistant_reply_retired" or marker.get(
                "request_hash"
            ) != self._fingerprint(payload, allow_memory):
                raise DomainError("OPERATION_ID_CONFLICT")
            return {
                "mode": "local_rules",
                "kind": "reply",
                "saved": False,
                "message": (
                    "遗忘信息后，这条旧回复已清除。没有执行新的操作。"
                    if payload.language == "zh"
                    else "This earlier response was cleared after forgetting information. No new action was run."
                ),
            }
        return None

    def _message(self, payload, key, *, allow_memory=True, on_event=None, conversation=None):
        if not self.config.valid():
            with self.lock:
                cached = self._cached_reply(payload, key, allow_memory)
                if cached is not None:
                    return cached
                before = {row["id"] for row in self.runtime.assistant.audit.listing(100)}
                reply = self.runtime.assistant.local_message(
                    payload, key, allow_memory=allow_memory, conversation=conversation
                )
                if on_event is not None:
                    fresh = [
                        row
                        for row in self.runtime.assistant.audit.listing(100)
                        if row["id"] not in before and row["call_key"] == key
                    ]
                    for event in audit_events(sorted(fresh, key=lambda row: row["id"])):
                        on_event(event)
                with self.store.connection(write=True) as conn:
                    conn.execute(
                        "INSERT INTO assistant_replies VALUES(?,?,?)",
                        (key, self._fingerprint(payload, allow_memory), encode(reply)),
                    )
                return reply
        if not key or len(key) > 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)
        fingerprint = self._fingerprint(payload, allow_memory)
        with self.lock:
            cached = self._cached_reply(payload, key, allow_memory)
            if cached is not None:
                return cached
            before = {row["id"] for row in self.runtime.assistant.audit.listing(100)}
            has_files = bool(conversation and conversation.attachment_ids)
            turn = (
                None
                if has_files
                else self.runtime.assistant.memory_turn(payload, key, allow_memory=allow_memory)
            )
            if turn is None and not has_files:
                turn = self.runtime.goals.turn(payload, key, allow=allow_memory)
            if turn is None and not has_files:
                turn = self.runtime.assistant.recall_turn(
                    payload, key, allow_memory=allow_memory, conversation=conversation
                )
            if turn is None and not has_files:
                turn = self.maybe_extract(payload, key, allow_memory=allow_memory)
            if turn is not None:
                if on_event is not None:
                    fresh = [
                        row
                        for row in self.runtime.assistant.audit.listing(100)
                        if row["id"] not in before and row["call_key"] == key
                    ]
                    for event in audit_events(sorted(fresh, key=lambda row: row["id"])):
                        on_event(event)
                reply = present(turn, self.runtime.data.preferences(), payload.language)
                with self.store.connection(write=True) as conn:
                    conn.execute(
                        "INSERT INTO assistant_replies VALUES(?,?,?)",
                        (key, fingerprint, encode(reply)),
                    )
                return reply
            from .assistant import TOOLS

            context = {
                "language": payload.language,
                **self.context(
                    payload.task_id,
                    include_memory=allow_memory,
                    user_message=payload.message,
                    conversation=conversation,
                ),
                "tools": [
                    t
                    for t in TOOLS
                    if t["name"] in TextPlan.model_fields["tool"].annotation.__args__
                    and tool_visible(t["name"], allow_memory)
                ],
            }
            system = render_prompt(
                self.runtime.persona.current()["body"],
                self.runtime.data.preferences(),
                payload.language,
            )
            files, attachment_parts, attachment_guard = self.attachments.context(
                conversation, required_ids=payload.attachment_ids
            )
            if files:
                context["attachments"] = files
                system += "\n" + FILE_POLICY
            reply = AgentLoop(
                self.runtime,
                HostedTextProvider(
                    self.generate,
                    self.generate_live,
                    attachment_parts=attachment_parts,
                    attachment_guard=attachment_guard,
                ),
            ).run(
                system=system,
                context=context,
                key=key,
                language=payload.language,
                allow_memory=allow_memory,
                on_event=on_event,
            )
            reply = present(reply, self.runtime.data.preferences(), payload.language)
            with self.store.connection(write=True) as conn:
                conn.execute(
                    "INSERT INTO assistant_replies VALUES(?,?,?)", (key, fingerprint, encode(reply))
                )
            return reply

    def event_stream(self, payload, key, *, allow_memory=True, principal=None):
        """SSE bytes. Real message deltas when the provider streams; otherwise short pieces."""
        pending = Queue()
        live = {"final": False}

        def on_event(event):
            outgoing = dict(event)
            if outgoing.get("type") == "preview" and outgoing.pop("final", False):
                live["final"] = True
            pending.put(outgoing)

        def work():
            try:
                reply = self.message(
                    payload, key, allow_memory=allow_memory, on_event=on_event, principal=principal
                )
                if not live["final"]:
                    for piece in text_chunks(str(reply.get("message") or "")):
                        pending.put({"type": "delta", "text": piece})
                pending.put({"type": "done", "reply": reply})
            except DomainError as error:
                pending.put({"type": "error", "code": error.code, "status": error.status})
            except Exception:
                pending.put({"type": "error", "code": "REQUEST_FAILED", "status": 500})
            finally:
                pending.put(None)

        threading.Thread(target=work, name="desk-reply-stream", daemon=True).start()
        while True:
            item = pending.get()
            if item is None:
                break
            yield sse_encode(item)

    def _quiet_now(self):
        prefs = self.runtime.data.preferences()
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        return is_quiet(prefs, self.store.clock().astimezone(zone))

    def _purpose_count(self, purpose: str) -> int:
        today = iso(self.store.clock())[:10]
        with self.store.connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM text_ai_usage WHERE purpose=? AND at>=?",
                (purpose, today),
            ).fetchone()[0]

    def maybe_extract(self, payload, key, *, allow_memory=True):
        """One capped model suggestion. A rejected or failed call does not save a fact."""
        if (
            not allow_memory
            or self.config.extract_cap <= 0
            or not self.config.valid()
            or self._purpose_count("memory_extract") >= self.config.extract_cap
        ):
            return None
        try:
            result = self.generate(
                EXTRACT_INSTRUCTIONS,
                {"user_message": payload.message},
                ExtractionResult,
                "memory_extract",
            )
        except DomainError:
            return None
        if result.fact is None:
            return None
        fact = accept_stated_fact(payload.message, result.fact.body)
        if fact is None:
            return None
        return self.runtime.assistant.propose_fact(
            fact, key, origin="conversation", note=result.fact.reason
        )

    def enrich_one(self):
        if not (self.config.valid() and self.config.background) or not self.background_lock.acquire(
            False
        ):
            return
        kept_reason = {}
        try:
            if self._quiet_now():
                return
            with self.store.connection(write=True) as conn:
                today = iso(self.store.clock())[:10]
                if (
                    conn.execute(
                        "SELECT COUNT(*) FROM text_ai_usage WHERE purpose='followup' AND at>=?",
                        (today,),
                    ).fetchone()[0]
                    >= 20
                ):
                    return
                row = conn.execute(
                    "SELECT f.* FROM task_followups f JOIN tasks t ON t.id=f.task_id WHERE f.state='pending' AND f.ai_status='pending' AND t.version=f.task_version AND t.paused=0 LIMIT 1"
                ).fetchone()
                if not row:
                    return
                task = self.runtime.tasks.get(conn, row["task_id"])
                # Hidden private material never goes to the background provider.
                # A task with follow-up turned off keeps its record, but optional
                # text advice is not sent even if a check-in was already queued.
                if (
                    self.store.settings(conn)["hide_private"] and task["visibility"] == "private"
                ) or not task.get("follow_up_enabled", True):
                    conn.execute(
                        "UPDATE task_followups SET ai_status='skipped' WHERE id=?", (row["id"],)
                    )
                    return
                notice = json.loads(row["content"])
                kept_reason = {
                    name: notice[name] for name in ("reason_en", "reason_zh") if notice.get(name)
                }
                conn.execute(
                    "UPDATE task_followups SET ai_status='running' WHERE id=?", (row["id"],)
                )
            try:
                advice = self.generate(
                    render_prompt(
                        self.runtime.persona.current()["body"],
                        self.runtime.data.preferences(),
                        "en",
                        channel="followup",
                    ),
                    self.context(row["task_id"]),
                    FollowUpAdvice,
                    "followup",
                )
            except DomainError:
                with self.store.connection(write=True) as conn:
                    conn.execute(
                        "UPDATE task_followups SET ai_status='failed' WHERE id=?", (row["id"],)
                    )
                return
            with self.store.connection(write=True) as conn:
                current = self.runtime.tasks.get(conn, row["task_id"])
                if (
                    current["version"] == row["task_version"]
                    and current["status"] in {"todo", "in_progress", "waiting"}
                    and not current["paused"]
                    and current.get("follow_up_enabled", True)
                ):
                    conn.execute(
                        "UPDATE task_followups SET content=?,ai_status='complete' WHERE id=? AND state='pending'",
                        (encode({**advice.model_dump(), "mode": "ai", **kept_reason}), row["id"]),
                    )
                    self.store.bump(conn)
        finally:
            self.background_lock.release()


class _StreamFailed(Exception):
    """The provider stream produced no text, so complete() may still run once."""


def _read_deltas(adapter, client, config, prompt, content, on_delta):
    parts: list[str] = []
    shown = ""
    try:
        iterator, box = adapter.deltas(client, config, prompt, content)
        for piece in iterator:
            if not isinstance(piece, str) or not piece:
                continue
            parts.append(piece)
            raw = "".join(parts)
            if len(raw) > 20000:
                raise ValueError()
            grown = extract_message(raw)
            if isinstance(grown, str) and grown.startswith(shown) and len(grown) > len(shown):
                on_delta(grown[len(shown) :])
                shown = grown
        if not parts:
            raise _StreamFailed()
        usage = dict(box) if isinstance(box, dict) else {}
        return "".join(parts), usage, shown != ""
    except _StreamFailed:
        raise
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        if parts:
            raise
        raise _StreamFailed() from None

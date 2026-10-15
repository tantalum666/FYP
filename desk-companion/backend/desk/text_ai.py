"""Optional Qwen/Gemini text reasoning. No provider call without explicit configuration.

Persistent memory is owner-reviewed facts plus confirmed tasks. Deleted facts are omitted.
The model can only prepare proposals; background advice cannot mutate task or memory state.
"""

import hashlib
import json
import os
import re
import threading
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx
from pydantic import Field, ValidationError

from .calendar import iso
from .context import pack_conversation
from .persona import followup_system, text_system
from .workspace_data import is_quiet
from .schemas import StrictModel
from .store import DomainError, encode


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
    ] = "none"
    arguments: dict = Field(default_factory=dict)


class FollowUpAdvice(StrictModel):
    en: str = Field(min_length=1, max_length=600)
    zh: str = Field(min_length=1, max_length=600)


@dataclass
class TextConfig:
    provider: str = "none"
    model: str = ""
    endpoint: str = ""
    api_key: str = ""
    background: bool = False

    @classmethod
    def environment(cls):
        return cls(
            *(
                os.environ.get("DESK_TEXT_" + key, default)
                for key, default in [
                    ("PROVIDER", "none"),
                    ("MODEL", ""),
                    ("ENDPOINT", ""),
                    ("API_KEY", ""),
                ]
            ),
            background=os.environ.get("DESK_TEXT_BACKGROUND") == "1",
        )

    def valid(self):
        if self.provider not in {"qwen", "gemini"} or not self.model or not self.api_key:
            return False
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", self.model):
            return False
        parsed = urlsplit(self.endpoint)
        if self.provider == "gemini":
            return (
                not self.endpoint
                or self.endpoint == "https://generativelanguage.googleapis.com/v1beta"
            )
        return bool(
            parsed.scheme == "https"
            and parsed.hostname
            and (
                parsed.hostname.endswith(".maas.aliyuncs.com")
                or parsed.hostname
                in {
                    "dashscope.aliyuncs.com",
                    "dashscope-intl.aliyuncs.com",
                    "dashscope-us.aliyuncs.com",
                }
            )
            and parsed.path.endswith("/compatible-mode/v1/chat/completions")
            and not any(
                [parsed.username, parsed.password, parsed.query, parsed.fragment, parsed.port]
            )
        )


class TextAssistant:
    def __init__(self, runtime, config=None, transport=None):
        self.runtime, self.store = runtime, runtime.store
        self.config = config or TextConfig.environment()
        self.transport = transport
        self.lock = threading.Lock()
        self.background_lock = threading.Lock()
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
        }

    def generate(self, system, context, schema, purpose):
        if not self.config.valid():
            raise DomainError("TEXT_AI_NOT_CONFIGURED", 503)
        prompt = (
            system
            + "\nReturn only JSON matching this schema: "
            + encode(schema.model_json_schema())
        )
        content = encode(context)
        from uuid import uuid4

        usage_id = uuid4().hex
        with self.store.connection(write=True) as conn:
            conn.execute(
                "INSERT INTO text_ai_usage VALUES(?,?,?,?,?)",
                (usage_id, iso(self.store.clock()), purpose, self.config.provider, "{}"),
            )
        try:
            with httpx.Client(
                timeout=20, transport=self.transport, follow_redirects=False
            ) as client:
                if self.config.provider == "qwen":
                    result = client.post(
                        self.config.endpoint,
                        headers={"Authorization": "Bearer " + self.config.api_key},
                        json={
                            "model": self.config.model,
                            "messages": [
                                {"role": "system", "content": prompt},
                                {"role": "user", "content": content},
                            ],
                            "response_format": {"type": "json_object"},
                            "stream": False,
                            "max_tokens": 1600,
                            "enable_thinking": False,
                        },
                    )
                    result.raise_for_status()
                    body = result.json()
                    raw = body["choices"][0]["message"]["content"]
                    usage = body.get("usage", {})
                else:
                    endpoint = (
                        (self.config.endpoint or "https://generativelanguage.googleapis.com/v1beta")
                        + "/models/"
                        + self.config.model
                        + ":generateContent"
                    )
                    result = client.post(
                        endpoint,
                        headers={"x-goog-api-key": self.config.api_key},
                        json={
                            "systemInstruction": {"parts": [{"text": prompt}]},
                            "contents": [{"role": "user", "parts": [{"text": content}]}],
                            "generationConfig": {
                                "responseMimeType": "application/json",
                                "maxOutputTokens": 1600,
                            },
                        },
                    )
                    result.raise_for_status()
                    body = result.json()
                    raw = "".join(
                        p.get("text", "")
                        for p in body["candidates"][0]["content"]["parts"]
                        if not p.get("thought")
                    )
                    usage = body.get("usageMetadata", {})
                if not isinstance(raw, str) or len(raw) > 20000:
                    raise ValueError()
                parsed = schema.model_validate_json(raw)
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, ValidationError):
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

    def context(self, task_id=None, *, include_memory=True):
        return pack_conversation(self.runtime, task_id, include_memory=include_memory)

    def message(self, payload, key, *, allow_memory=True):
        if not self.config.valid():
            return self.runtime.assistant.local_message(payload, key, allow_memory=allow_memory)
        if not key or len(key) > 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)
        fingerprint = hashlib.sha256(
            encode({**payload.model_dump(), "allow_memory": allow_memory}).encode()
        ).hexdigest()
        with self.lock:
            with self.store.connection() as conn:
                old = conn.execute("SELECT * FROM assistant_replies WHERE id=?", (key,)).fetchone()
            if old:
                if old["request_hash"] != fingerprint:
                    raise DomainError("OPERATION_ID_CONFLICT")
                return json.loads(old["result"])
            from .assistant import TOOLS

            context = {
                "user_message": payload.message,
                "language": payload.language,
                **self.context(payload.task_id, include_memory=allow_memory),
                "tools": [
                    t
                    for t in TOOLS
                    if t["name"] in TextPlan.model_fields["tool"].annotation.__args__
                    and (allow_memory or not t["name"].startswith("memory_"))
                ],
            }
            system = text_system(self.runtime.persona.current()["body"])
            reply = None
            for index in range(3):
                plan = self.generate(system, context, TextPlan, "conversation")
                if plan.tool == "none":
                    reply = {"mode": "ai", "kind": "reply", "message": plan.message}
                    break
                result = self.runtime.assistant.tool(
                    plan.tool,
                    plan.arguments,
                    "text/" + hashlib.sha256((key + "/" + str(index)).encode()).hexdigest(),
                    allow_memory=allow_memory,
                )
                if "proposal" in result:
                    reply = {"mode": "ai", "kind": "draft", "message": plan.message, **result}
                    break
                if "job" in result:
                    reply = {"mode": "ai", "kind": "job", "message": plan.message, **result}
                    break
                context["last_tool_result"] = {"tool": plan.tool, "result": result}
            if reply is None:
                reply = {
                    "mode": "ai",
                    "kind": "clarify",
                    "message": "请明确要跟进哪件事。"
                    if payload.language == "zh"
                    else "Please identify the task you want to follow up.",
                }
            with self.store.connection(write=True) as conn:
                conn.execute(
                    "INSERT INTO assistant_replies VALUES(?,?,?)", (key, fingerprint, encode(reply))
                )
            return reply

    def _quiet_now(self):
        prefs = self.runtime.data.preferences()
        with self.store.connection() as conn:
            zone = ZoneInfo(self.store.settings(conn)["timezone"])
        return is_quiet(prefs, self.store.clock().astimezone(zone))

    def enrich_one(self):
        if not (self.config.valid() and self.config.background) or not self.background_lock.acquire(
            False
        ):
            return
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
                conn.execute(
                    "UPDATE task_followups SET ai_status='running' WHERE id=?", (row["id"],)
                )
            try:
                advice = self.generate(
                    followup_system(self.runtime.persona.current()["body"]),
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
                        (encode({**advice.model_dump(), "mode": "ai"}), row["id"]),
                    )
                    self.store.bump(conn)
        finally:
            self.background_lock.release()

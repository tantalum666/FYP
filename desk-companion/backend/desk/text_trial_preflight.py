"""Offline-only preview of a bounded synthetic text trial through production adapters.

No runtime, credential loader, network transport, tool dispatcher or live mode.
The only database is an in-memory adapter-usage ledger, discarded after the run.
"""

from contextlib import contextmanager
from datetime import UTC, datetime
import hashlib
import json
import sqlite3
from types import SimpleNamespace
from typing import Literal

import httpx

from .provider_policy import GEMINI_TEXT_ENDPOINT
from .store import DomainError, encode
from .tasks import TaskInput
from .text_ai import TextAssistant, TextConfig, TextPlan, TEXT_RESPONSE_BYTES

REQUEST_BYTES = 16 * 1024
OUTPUT_TOKENS = 1600
WALL_SECONDS = 45
SYNTHETIC_TITLE = "FYP synthetic test A"
SYNTHETIC_COMMAND = (
    "请只建立一个待审阅的本地任务草稿，标题为“FYP synthetic test A”，不要保存任务或安排提醒。"
)
_FIXTURE_KEY = "offline-fixture-not-a-credential"
_SYSTEM = (
    "You are Desk Companion in a synthetic acceptance fixture. Prepare exactly one "
    "task_create_draft plan for review, with only the requested title, UTC timezone and follow_up_enabled=false. "
    "Do not save, approve, schedule, execute or claim any completed action. "
    "Only the one advertised draft tool is available. Return JSON only."
)


class SyntheticTrialPlan(TextPlan):
    """Narrow existing production plan schema; never a separate planner."""

    tool: Literal["task_create_draft"]


def synthetic_context():
    """Construct fresh fixed data; never project a real store or user context."""
    return {
        "user_message": SYNTHETIC_COMMAND,
        "language": "zh",
        "now": "2026-01-01T00:00:00Z",
        "timezone": "UTC",
        "tools": [
            {
                "name": "task_create_draft",
                "description": "Prepare a local task draft for review. Does not save or schedule.",
                "parameters": TaskInput.model_json_schema(),
            }
        ],
    }


def validate_trial_plan(plan):
    """Admit just the fixed plan; do not invoke even the draft creation tool."""
    # Revalidate even if a caller supplies a constructed Pydantic instance.
    parsed = SyntheticTrialPlan.model_validate_json(plan.model_dump_json())
    expected = {"title": SYNTHETIC_TITLE, "timezone": "UTC", "follow_up_enabled": False}
    if encode(parsed.arguments) != encode(expected):
        raise ValueError("TRIAL_PLAN_OUTSIDE_SYNTHETIC_SCOPE")
    TaskInput.model_validate(parsed.arguments)
    return parsed


class _UsageStore:
    """Minimum real SQLite seam required by TextAssistant.generate, no user tables."""

    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.clock = lambda: datetime(2026, 1, 1, tzinfo=UTC)

    @contextmanager
    def connection(self, write=False):
        with self.db:
            yield self.db


def _fixture_body(provider):
    raw = encode(
        {
            "message": "这是待审阅的虚构任务计划，尚未保存，也未安排提醒。",
            "tool": "task_create_draft",
            "arguments": {"title": SYNTHETIC_TITLE, "timezone": "UTC", "follow_up_enabled": False},
        }
    )
    if provider == "qwen":
        return {"choices": [{"message": {"content": raw}}], "usage": {}}
    return {"candidates": [{"content": {"parts": [{"text": raw}]}}], "usageMetadata": {}}


class _OfflineCapture(httpx.BaseTransport):
    """Terminal in-memory transport: there is no delegation to a network transport."""

    def __init__(self, config):
        self.provider = config.provider
        self.model = config.model
        self.url = (
            config.endpoint
            if self.provider == "qwen"
            else (
                (config.endpoint or GEMINI_TEXT_ENDPOINT)
                + "/models/"
                + config.model
                + ":generateContent"
            )
        )
        self.attempts = 0
        self.payload = None
        self.body_bytes = None

    def handle_request(self, request):
        self.attempts += 1
        if self.attempts != 1:
            raise ValueError("TRIAL_REQUEST_LIMIT")
        if request.method != "POST" or str(request.url) != self.url:
            raise ValueError("TRIAL_REQUEST_DESTINATION_CHANGED")
        raw = request.content
        if len(raw) > REQUEST_BYTES:
            raise ValueError("TRIAL_REQUEST_SIZE_LIMIT")
        body = json.loads(raw)
        # Fail closed if the production adapter drops or changes its documented cap.
        if self.provider == "qwen":
            valid = (
                body.get("model") == self.model
                and type(body.get("max_tokens")) is int
                and body["max_tokens"] == OUTPUT_TOKENS
                and body.get("stream") is False
                and body.get("enable_thinking") is False
                and body.get("response_format") == {"type": "json_object"}
            )
        else:
            generation = body.get("generationConfig", {})
            valid = (
                type(generation.get("maxOutputTokens")) is int
                and generation["maxOutputTokens"] == OUTPUT_TOKENS
                and generation.get("responseMimeType") == "application/json"
            )
        if not valid:
            raise ValueError("TRIAL_OUTPUT_LIMIT_OR_PROTOCOL_CHANGED")
        self.payload, self.body_bytes = body, raw
        return httpx.Response(200, json=_fixture_body(self.provider))


def offline_preflight(*, provider, model, endpoint):
    """One fixed synthetic mock exchange, never authorization or live acceptance.

    Invoke through scripts/check_text_trial.py for the external process timeout.
    This pure worker has no standalone hard wall-clock guarantee.
    """
    # No TextConfig.environment call, config argument, key input or custom transport.
    config = TextConfig(provider=provider, model=model, endpoint=endpoint, api_key=_FIXTURE_KEY)
    if provider not in {"gemini", "qwen"} or not config.valid():
        raise ValueError("TRIAL_INVALID_PREVIEW_TARGET")
    transport = _OfflineCapture(config)
    store = _UsageStore()
    try:
        service = TextAssistant(SimpleNamespace(store=store), config=config, transport=transport)
        pinned = (config.provider, config.model, config.endpoint, config.api_key, config.background)

        def checkpoint():
            if pinned != (
                config.provider,
                config.model,
                config.endpoint,
                config.api_key,
                config.background,
            ):
                raise DomainError("TRIAL_CONFIGURATION_CHANGED", 403)

        plan = service.generate_guarded(
            _SYSTEM,
            synthetic_context(),
            SyntheticTrialPlan,
            "offline_trial_preflight",
            checkpoint=checkpoint,
        )
        plan = validate_trial_plan(plan)
        usage_count = store.db.execute("SELECT COUNT(*) FROM text_ai_usage").fetchone()[0]
        if transport.attempts != 1 or usage_count != 1 or transport.payload is None:
            raise ValueError("TRIAL_ATTEMPT_ACCOUNTING_FAILED")
        return {
            "status": "offline_preflight_passed",
            "live_acceptance": "not_run",
            "network_requests": 0,
            "mock_requests": transport.attempts,
            "adapter_usage_rows": usage_count,
            "provider": provider,
            "model": model,
            "endpoint": transport.url,
            "request": {
                "method": "POST",
                "json": transport.payload,
                "bytes": len(transport.body_bytes),
                "sha256": hashlib.sha256(transport.body_bytes).hexdigest(),
                "headers": "Credential headers intentionally omitted; fixture key only",
            },
            "limits": {
                "request_bytes": REQUEST_BYTES,
                "output_tokens_in_actual_payload": OUTPUT_TOKENS,
                "response_bytes": TEXT_RESPONSE_BYTES,
                "requests": 1,
                "retries": 0,
            },
            "synthetic_plan": plan.model_dump(),
            "plan_dispatched": False,
            "draft_persisted": False,
            "tasks_saved": 0,
            "billing": "not_run; no estimate or financial cap established",
            "remaining_gates": [
                "Explicit provider/model/region and exact data approval",
                "Account eligibility, secure credential setup and one-call spending approval",
                "Separately reviewed live transport and account cost controls",
                "Actual provider response, semantic review and independent draft-only verification",
            ],
        }
    finally:
        store.db.close()

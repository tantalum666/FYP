"""One durable USD1 live-evaluation ledger; unknown requests retain their holds.

Rates checked 2026-11-07 against official Standard pricing for GPT6.1Sol:
input2/output10/cached0.10/cache-write2.50 or5 USD per million. This controller
uses the highest input rate plus10% for every token and11/M for output. It is
test-run accounting, not a provider billing limit or proof of the final invoice.
"""

from contextlib import contextmanager
import hashlib
import json
import math
import re
import sqlite3
import time
from uuid import uuid4

import httpx

from desk.bounded_json import _request_checkpoint
from desk.openai_transport import validate_openai_proxy

MODEL = "gpt-6.1-sol"
ENDPOINT = "https://api.openai.com/v1/responses"
CEILING = 1_000_000_000  # Integer nanodollars, one USD across ALL cases.
INPUT_RATE, OUTPUT_RATE = 5500, 11000
NORMAL_INPUT_RATE, CACHED_RATE = 2200, 110


class EvalStopped(ValueError):
    pass


class EvalBudget:
    def __init__(self, path):
        self.path = path
        with self.connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS policy(id INTEGER PRIMARY KEY, ceiling INTEGER, closed INTEGER)"
            )
            db.execute("INSERT OR IGNORE INTO policy VALUES(1,?,0)", (CEILING,))
            if db.execute("SELECT ceiling FROM policy").fetchone()[0] != CEILING:
                raise EvalStopped("BUDGET_POLICY_CHANGED")
            db.execute("""CREATE TABLE IF NOT EXISTS attempts(
                id TEXT PRIMARY KEY, case_name TEXT, request_hash TEXT, input_bound INTEGER,
                output_bound INTEGER, reserve INTEGER, accounted INTEGER, state TEXT,
                usage TEXT, at REAL)""")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        finally:
            db.close()

    def reserve(self, case, body, inputs, outputs):
        if (
            type(inputs) is not int
            or not 0 <= inputs <= 120000
            or type(outputs) is not int
            or not 16 <= outputs <= 1600
        ):
            raise EvalStopped("TOKEN_LIMIT")
        bound = math.ceil(inputs * 1.1) + 64
        amount = bound * INPUT_RATE + outputs * OUTPUT_RATE
        request_id = uuid4().hex
        with self.connection() as db:
            if db.execute("SELECT COUNT(*) FROM attempts WHERE state='unknown'").fetchone()[0]:
                raise EvalStopped("UNRECONCILED_REQUEST")
            used = db.execute("SELECT COALESCE(SUM(accounted),0) FROM attempts").fetchone()[0]
            if db.execute("SELECT closed FROM policy").fetchone()[0] or used + amount > CEILING:
                raise EvalStopped("EVALUATION_BUDGET_EXHAUSTED")
            db.execute(
                "INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    request_id,
                    case,
                    hashlib.sha256(body).hexdigest(),
                    bound,
                    outputs,
                    amount,
                    amount,
                    "unknown",
                    "{}",
                    time.time(),
                ),
            )
        return request_id

    def ensure_active(self):
        with self.connection() as db:
            if db.execute("SELECT closed FROM policy").fetchone()[0]:
                raise EvalStopped("EVALUATION_BUDGET_EXHAUSTED")
            if db.execute("SELECT COUNT(*) FROM attempts WHERE state='unknown'").fetchone()[0]:
                raise EvalStopped("UNRECONCILED_REQUEST")

    def finish(self, request_id, response):
        usage = response.get("usage")
        with self.connection() as db:
            row = db.execute("SELECT * FROM attempts WHERE id=?", (request_id,)).fetchone()
            if not row or row["state"] != "unknown":
                raise EvalStopped("RECEIPT_ALREADY_FINAL")
            if not isinstance(usage, dict):
                return  # Preserve the entire reservation; never assume zero.
            incoming, outgoing = usage.get("input_tokens"), usage.get("output_tokens")
            valid = (
                response.get("model") == MODEL
                and response.get("service_tier", "default") == "default"
                and type(incoming) is int
                and 0 <= incoming <= row["input_bound"]
                and type(outgoing) is int
                and 0 <= outgoing <= row["output_bound"]
            )
            if not valid:
                db.execute("UPDATE policy SET closed=1")
                return
            details = usage.get("input_tokens_details") or usage.get("input_token_details") or {}
            cached = details.get("cached_tokens", 0)
            written = details.get("cache_write_tokens", incoming - cached)
            if (
                type(cached) is not int
                or type(written) is not int
                or min(cached, written) < 0
                or cached + written > incoming
            ):
                db.execute("UPDATE policy SET closed=1")
                return
            amount = (
                cached * CACHED_RATE
                + written * INPUT_RATE
                + (incoming - cached - written) * NORMAL_INPUT_RATE
                + outgoing * OUTPUT_RATE
            )
            db.execute(
                "UPDATE attempts SET accounted=?,state='received',usage=? WHERE id=?",
                (amount, json.dumps(usage), request_id),
            )

    def snapshot(self):
        with self.connection() as db:
            rows = [dict(x) for x in db.execute("SELECT * FROM attempts ORDER BY at")]
            return {
                "ceiling_usd": 1,
                "closed": bool(db.execute("SELECT closed FROM policy").fetchone()[0]),
                "requests": len(rows),
                "conservative_accounted_usd": sum(x["accounted"] for x in rows) / 1e9,
                "unreconciled_requests": sum(x["state"] == "unknown" for x in rows),
                "attempts": [{**x, "usage": json.loads(x["usage"])} for x in rows],
                "billing_note": "Conservative token accounting, not a verified invoice; unknown attempts retain their reservations.",
            }

    def close(self):
        with self.connection() as db:
            db.execute("UPDATE policy SET closed=1")


class BudgetTransport(httpx.BaseTransport):
    """Count -> reserve -> one real call -> receipt, with no automatic retries."""

    def __init__(self, budget, case, *, proxy, upstream=None):
        self.budget, self.case = budget, case
        self.proxy = validate_openai_proxy(proxy)
        self.borrowed = upstream is not None
        self.upstream = upstream
        self.responses = []
        self.errors = []
        self.generation_times = []
        self.on_generation_start = None

    def json_response(self, request):
        if self.upstream is None:
            self.upstream = httpx.HTTPTransport(proxy=self.proxy, retries=0, trust_env=False)
        response = self.upstream.handle_request(request)
        data = bytearray()
        try:
            if response.headers.get("content-encoding", "identity") != "identity":
                raise EvalStopped("ENCODED_RESPONSE")
            chunks = [response.content] if response.is_stream_consumed else response.iter_raw()
            for part in chunks:
                if len(data) + len(part) > 128000:
                    raise EvalStopped("RESPONSE_TOO_LARGE")
                data.extend(part)
        finally:
            response.close()
        return httpx.Response(
            response.status_code, headers=response.headers, content=bytes(data), request=request
        )

    def handle_request(self, request):
        self.budget.ensure_active()
        if request.method != "POST" or str(request.url) != ENDPOINT:
            raise EvalStopped("UNEXPECTED_MODEL_DESTINATION")
        payload = json.loads(request.content)
        if (
            payload.get("model") != MODEL
            or payload.get("stream")
            or payload.get("store") is not False
        ):
            raise EvalStopped("UNBOUNDED_REQUEST")
        if payload.get("tools", []) not in ([], [{"type": "computer"}]):
            raise EvalStopped("UNBUDGETED_HOSTED_TOOL")
        payload["service_tier"] = "default"
        count_keys = {
            "model",
            "input",
            "instructions",
            "reasoning",
            "text",
            "tools",
            "tool_choice",
            "parallel_tool_calls",
        }
        count_body = {key: value for key, value in payload.items() if key in count_keys}
        counted = self.json_response(
            httpx.Request(
                "POST",
                ENDPOINT + "/input_tokens",
                json=count_body,
                headers={
                    "Authorization": request.headers["authorization"],
                    "Accept-Encoding": "identity",
                },
                extensions=request.extensions,
            )
        )
        if counted.status_code != 200:
            error = counted.json().get("error", {})
            message = str(error.get("message", "")).replace(
                request.headers["authorization"].removeprefix("Bearer "), "[redacted]"
            )
            self.errors.append(
                {
                    "phase": "count",
                    "status": counted.status_code,
                    "code": error.get("code"),
                    "param": error.get("param"),
                    "message": re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted]", message)[:300],
                }
            )
            raise EvalStopped("INPUT_TOKEN_COUNT_FAILED")
        encoded = json.dumps(payload, ensure_ascii=False).encode()
        _request_checkpoint(request)
        hold = self.budget.reserve(
            self.case, encoded, counted.json()["input_tokens"], payload["max_output_tokens"]
        )
        timing = {"start": time.monotonic(), "end": None}
        self.generation_times.append(timing)
        if self.on_generation_start:
            self.on_generation_start(len(self.generation_times))
        try:
            response = self.json_response(
                httpx.Request(
                    "POST",
                    ENDPOINT,
                    content=encoded,
                    headers={
                        "Authorization": request.headers["authorization"],
                        "Content-Type": "application/json",
                        "Accept-Encoding": "identity",
                    },
                    extensions=request.extensions,
                )
            )
        finally:
            timing["end"] = time.monotonic()
        try:
            value = response.json()
        except ValueError:
            raise EvalStopped("UNREADABLE_RESPONSE_RECEIPT") from None
        self.budget.finish(hold, value)
        # Test data only. Do not retain encrypted reasoning or raw image bodies.
        self.responses.append(
            {
                "id": value.get("id"),
                "status": value.get("status"),
                "http_status": response.status_code,
                "model": value.get("model"),
                "usage": value.get("usage"),
                "error": {k: value.get("error", {}).get(k) for k in ("type", "code", "param")}
                if value.get("error")
                else None,
                "output": [
                    x
                    for x in value.get("output", [])
                    if x.get("type") in {"message", "computer_call"}
                ],
            }
        )
        return response

    def close(self):
        if self.upstream is not None and not self.borrowed:
            self.upstream.close()
            self.upstream = None

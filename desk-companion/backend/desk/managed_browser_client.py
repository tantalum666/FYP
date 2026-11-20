"""Official Agents session transport, with bounded observation recovery.

The managed harness owns browser reasoning. FYP admits exact public origins,
fences its authority while work runs, and deletes the session before publishing
a report. An unknown creation/deletion keeps the executor blocked for inspection.
"""

import asyncio
import contextlib
import hashlib
import json
import re
import time

import httpx

from .flight_search import recorded_quote, uses_flight_connector
from .managed_session_config import managed_session
from .computer import ExecutionRejected
from .openai_transport import OPENAI_API as API, SESSION_ID, model_proxy, numeric_usage


class ManagedBrowserClient:
    setup_seconds = 45
    active_seconds = 90
    auth_seconds = 90
    cleanup_seconds = 60
    poll_seconds = 0.25
    snapshot_seconds = 1

    def __init__(self, config, *, transport=None):
        self.config, self.transport = config, transport
        self.budget_observation = None

    async def run(self, intent, checkpoint, on_session, *, authentication=None):
        sid, reader = None, None
        started = time.monotonic()
        connector = uses_flight_connector(intent)
        activity_type = "mcp_call" if connector else "computer_use_call"
        ready, complete = asyncio.Event(), asyncio.Event()
        terminal, turn_id, activity_ids, handled = None, None, set(), set()
        origin_attempts = {}
        result = {
            "report": "",
            "activity_count": 0,
            "usage": None,
            "session_deleted": False,
            "deletion_readback": False,
            "stop_code": None,
            "turn_completed": False,
            "account_access_authorized": False,
            "stream_reconnections": 0,
        }
        headers = {"Authorization": "Bearer " + self.config.api_key, "OpenAI-Beta": "agents=v1"}
        async with httpx.AsyncClient(
            base_url=API,
            headers=headers,
            transport=self.transport,
            proxy=model_proxy(self.config, self.transport),
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(20, connect=3),
        ) as client:

            async def request(method, path, body=None, *, operation=None):
                response = await client.request(
                    method,
                    path,
                    json=body,
                    headers={"Idempotency-Key": operation} if operation else None,
                )
                response.raise_for_status()
                if len(response.content) > 1_000_000:
                    raise ValueError("Oversized managed response")
                # The official events endpoint normally accepts with an empty 202.
                value = response.json() if response.content else {}
                if not isinstance(value, dict):
                    raise ValueError("Invalid managed response")
                return value

            async def event(value, suffix):
                return await request(
                    "POST",
                    f"/agents/sessions/{sid}/events",
                    {"events": [value]},
                    operation=intent["artifact_id"] + "/" + suffix,
                )

            async def consume():
                nonlocal terminal, turn_id
                async with client.stream(
                    "GET",
                    f"/agents/sessions/{sid}/events",
                    params={"include_obfuscation": "false"},
                    timeout=httpx.Timeout(5, read=self.active_seconds + self.auth_seconds),
                ) as response:
                    response.raise_for_status()
                    ready.set()
                    lines, size, count = [], 0, 0
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            lines.append(line[5:].lstrip())
                            size += len(line)
                            if size > 3_000_000:
                                raise ValueError("Oversized managed event")
                            continue
                        if line or not lines:
                            continue
                        raw, lines, size = "\n".join(lines), [], 0
                        if raw == "[DONE]":
                            continue
                        count += 1
                        if count > 2000:
                            raise ValueError("Managed event limit exceeded")
                        value = json.loads(raw)
                        kind = value.get("type")
                        item = value.get("item") or {}
                        if kind in {
                            "agent.session.turn.item.added",
                            "agent.session.turn.item.done",
                        }:
                            if item.get("type") == activity_type:
                                activity_ids.add(item["id"])
                                result["activity_count"] = len(activity_ids)
                                if len(activity_ids) > intent["max_steps"]:
                                    raise ExecutionRejected("COMPUTER_ACTIVITY_LIMIT", 409)
                        if kind in {
                            "agent.session.turn.completed",
                            "agent.session.turn.failed",
                            "agent.session.turn.cancelled",
                        } and not (value.get("turn") or {}).get("subagent_id"):
                            ident = (value.get("turn") or {}).get("id")
                            if not isinstance(ident, str) or (turn_id and turn_id != ident):
                                raise ValueError("Unexpected managed turn")
                            turn_id = ident
                            terminal = kind
                            complete.set()
                        if kind in {
                            "error",
                            "agent.session.error",
                            "agent.session.failed",
                            "agent.session.environment.failed",
                        }:
                            raise ValueError("Managed session failed")

            async def review_actions(snapshot):
                waiting = False
                for action in snapshot.get("required_actions", []):
                    ident, req = action.get("request_id"), action.get("request", {})
                    if ident in handled:
                        continue
                    if (
                        not isinstance(ident, str)
                        or not 0 < len(ident) <= 256
                        or not turn_id
                        or action.get("turn_id") != turn_id
                        or action.get("type") != "computer_use_approval_request"
                    ):
                        raise ValueError("Unexpected managed approval")
                    checkpoint()
                    if req.get("type") == "browser_origin_access":
                        approved = req.get("origin") in intent["allowed_origins"]
                        answer = {
                            "type": "browser_origin_access",
                            "decision": "approve" if approved else "deny",
                        }
                    elif req.get("type") == "browser_authentication":
                        answer = None
                        if authentication:
                            try:
                                answer = authentication(action)
                            except ExecutionRejected:
                                answer = {"type": "browser_authentication", "action": "cancel"}
                                approved = False
                            else:
                                if answer is None:
                                    waiting = True
                                    continue
                                approved = True
                        else:
                            approved = False
                            answer = {"type": "browser_authentication", "action": "cancel"}
                    else:
                        raise ValueError("Unsupported managed approval")
                    handled.add(ident)
                    if answer.get("action") == "submit":
                        # This is the owner's data-scope grant, not evidence that
                        # login succeeded. Keep it even if the HTTP reply is lost.
                        result["account_access_authorized"] = True
                    payload = {
                        "type": "agent.session.input.computer_use_approval_request_result",
                        "request_id": ident,
                        "response": answer,
                    }
                    origin_attempts[ident] = origin_attempts.get(ident, 0) + 1
                    try:
                        await event(
                            payload, "approval-" + hashlib.sha256(ident.encode()).hexdigest()[:24]
                        )
                    except httpx.TransportError:
                        if (
                            req.get("type") == "browser_origin_access"
                            and approved
                            and origin_attempts[ident] < 2
                        ):
                            # Re-read required_actions before retrying this same
                            # idempotent decision. Never replay task input or credentials.
                            handled.discard(ident)
                            continue
                        raise
                    if not approved:
                        raise ExecutionRejected("COMPUTER_MANAGED_OWNER_REQUIRED", 409)
                if (
                    not any(
                        a.get("request", {}).get("type") == "browser_authentication"
                        for a in snapshot.get("required_actions", [])
                    )
                    and authentication
                ):
                    authentication(None)
                return waiting

            async def history():
                value = await request("GET", f"/agents/sessions/{sid}/items?order=asc&limit=100")
                if value.get("has_more"):
                    raise ValueError("Managed history exceeds its bound")
                for item in value.get("data", []):
                    if item.get("type") == activity_type and item.get("turn_id") == turn_id:
                        activity_ids.add(item["id"])
                result["activity_count"] = len(activity_ids)
                if len(activity_ids) > intent["max_steps"]:
                    raise ExecutionRejected("COMPUTER_ACTIVITY_LIMIT", 409)
                return value

            async def reconcile_turn():
                nonlocal turn_id, terminal
                turns = await request("GET", f"/agents/sessions/{sid}/turns?order=desc&limit=10")
                roots = [t for t in turns.get("data", []) if not t.get("subagent_id")]
                if turns.get("has_more") or len(roots) > 1:
                    raise ValueError("Unexpected managed turn history")
                if not roots:
                    return None
                turn = roots[0]
                if not isinstance(turn.get("id"), str) or (turn_id and turn_id != turn["id"]):
                    raise ValueError("Managed turn changed")
                turn_id = turn["id"]
                result["usage"] = numeric_usage(turn.get("usage")) or result["usage"]
                if self.budget_observation and turn.get("status") not in {"completed", "failed", "cancelled"}:
                    self.budget_observation(result["usage"])
                if turn.get("status") in {"completed", "failed", "cancelled"}:
                    result["terminal_usage"] = numeric_usage(turn.get("usage")) or result.get("terminal_usage")
                    terminal = "agent.session.turn." + turn["status"]
                    complete.set()
                return turn.get("status")

            async def subscribe():
                nonlocal reader
                ready.clear()
                reader = asyncio.create_task(consume())
                while not ready.is_set():
                    checkpoint()
                    if reader.done():
                        await reader
                        raise ValueError("Managed stream ended before subscription")
                    await asyncio.sleep(self.poll_seconds)

            async def work():
                nonlocal sid, reader
                checkpoint()
                body, browser_input = managed_session(intent, self.config.model)
                snapshot = await request("POST", "/agents/sessions", body, operation=intent["artifact_id"] + "/create")
                sid = snapshot.get("id")
                if not isinstance(sid, str) or not SESSION_ID.fullmatch(sid):
                    sid = None
                    raise ValueError("Invalid managed session ID")
                on_session(sid)  # Durable receipt before any input can start a turn.
                environment_config = snapshot.get("environment") or {}
                result["environment_size"] = environment_config.get("container_size")
                await subscribe()
                if browser_input is not None:
                    environment_id = (snapshot.get("environment") or {}).get("id")
                    if not isinstance(environment_id, str) or not re.fullmatch(
                        r"[A-Za-z0-9_-]{1,160}", environment_id
                    ):
                        raise ValueError("Missing managed environment identity")
                    checkpoint()
                    await event({"type": "agent.session.input.message", "input": browser_input}, "input")
                    # The official harness receives one input to start work, including
                    # lazy environment setup. Observe readiness after enqueueing;
                    # waiting before input can leave a valid environment pending.
                    while True:
                        checkpoint()
                        if time.monotonic() - started > self.setup_seconds:
                            raise TimeoutError
                        environment = await request("GET", f"/agents/environments/{environment_id}")
                        if environment.get("status") in {"ready", "connected"}:
                            break
                        if environment.get("status") not in {"pending", "provisioning"}:
                            raise ValueError("Managed environment did not connect")
                        await asyncio.sleep(self.poll_seconds)
                active_started = time.monotonic()
                result["setup_seconds"] = round(active_started - started, 3)
                next_read, auth_wait, last_tick, waiting = 0, 0, time.monotonic(), False
                while not complete.is_set():
                    checkpoint()
                    now = time.monotonic()
                    if waiting:
                        auth_wait += now - last_tick
                    last_tick = now
                    if (
                        auth_wait > self.auth_seconds
                        or now - active_started - auth_wait > self.active_seconds
                    ):
                        raise TimeoutError
                    if reader.done():
                        # SSE has no replay. Re-subscribe first, then restore canonical
                        # state. Never re-send the input or an approval on reconnection.
                        try:
                            await reader
                        except httpx.TransportError:
                            pass
                        if result["stream_reconnections"] >= 2:
                            raise ValueError("Managed stream recovery exhausted")
                        result["stream_reconnections"] += 1
                        await subscribe()
                        await reconcile_turn()
                        await history()
                        next_read = 0
                    if time.monotonic() >= next_read:
                        snapshot = await request("GET", f"/agents/sessions/{sid}")
                        if snapshot.get("status") == "failed":
                            raise ValueError("Managed session failed")
                        result["usage"] = numeric_usage(snapshot.get("usage")) or result["usage"]
                        if self.budget_observation and snapshot.get("status") not in {"idle", "failed"}:
                            self.budget_observation(result["usage"])
                        await reconcile_turn()
                        if not complete.is_set():
                            waiting = await review_actions(snapshot)
                        next_read = time.monotonic() + self.snapshot_seconds
                    await asyncio.sleep(self.poll_seconds)
                await_check = reader.exception() if reader.done() else None
                if await_check:
                    raise await_check
                checkpoint()
                if terminal != "agent.session.turn.completed":
                    raise ExecutionRejected("COMPUTER_PROVIDER_STOPPED", 409)
                # A terminal stream item must also belong to the saved root turn.
                if await reconcile_turn() != "completed":
                    raise ValueError("Managed turn completion not confirmed")
                saved = await history()
                # Listing and stream snapshots can precede token accounting.
                # Read the identified terminal resource once before deletion.
                if self.budget_observation and not result.get("terminal_usage"):
                    with contextlib.suppress(httpx.HTTPError, TimeoutError, ValueError):
                        async with asyncio.timeout(3):
                            for delay in (0, 0.4, 0.8):
                                await asyncio.sleep(delay)
                                detail = await request("GET", f"/agents/sessions/{sid}/turns/{turn_id}")
                                if (detail.get("id") == turn_id and detail.get("status") == "completed"
                                        and not detail.get("subagent_id")):
                                    usage = numeric_usage(detail.get("usage"))
                                    if usage and "input_tokens" in usage and "output_tokens" in usage:
                                        result["terminal_usage"] = result["usage"] = usage
                                        break
                if connector:
                    try:
                        quote = recorded_quote(saved.get("data", []), intent, turn_id)
                    except (KeyError, ValueError, TypeError) as error:
                        raise ExecutionRejected("COMPUTER_QUOTE_UNVERIFIED",409) from error
                    result.update(report=json.dumps(quote, ensure_ascii=False), turn_completed=True,
                                  source="kiwi_mcp", environment="none")
                    return
                finals = [
                    item
                    for item in saved.get("data", [])
                    if item.get("type") == "message"
                    and item.get("turn_id") == turn_id
                    and item.get("role") == "assistant"
                    and item.get("phase") == "final_answer"
                    and item.get("status") == "completed"
                ]
                if len(finals) != 1:
                    raise ValueError("Expected one final managed report")
                report = "\n".join(
                    part["text"]
                    for part in finals[0].get("content", [])
                    if part.get("type") == "output_text"
                )
                if not report.strip() or len(report) > 16000 or not activity_ids:
                    raise ValueError("Missing bounded browser report")
                result.update(report=report, turn_completed=True)

            try:
                await asyncio.wait_for(
                    work(), self.setup_seconds + self.active_seconds + self.auth_seconds
                )
            except TimeoutError:
                result["stop_code"] = "JOB_DEADLINE_EXCEEDED"
            except ExecutionRejected as error:
                result["stop_code"] = error.code
            except Exception as error:
                result["stop_code"] = "COMPUTER_PROVIDER_UNAVAILABLE"
                result["error_type"] = type(error).__name__
            finally:
                if authentication:
                    authentication(None)

                async def cleanup():
                    # Closing SSE alone does not stop managed work. Do not retry
                    # input/create; only cancellation/deletion is safe here.
                    if sid:

                        async def cancel_pending(attempt):
                            # A pending browser approval can survive a turn-cancel
                            # request. Cancel the approval, then stop the turn.
                            with contextlib.suppress(Exception):
                                snapshot = await request("GET", f"/agents/sessions/{sid}")
                                for action in snapshot.get("required_actions", [])[:8]:
                                    ident = action.get("request_id")
                                    kind = (action.get("request") or {}).get("type")
                                    if (
                                        not isinstance(ident, str)
                                        or action.get("type") != "computer_use_approval_request"
                                    ):
                                        continue
                                    answer = (
                                        {"type": kind, "decision": "cancel"}
                                        if kind == "browser_origin_access"
                                        else {"type": kind, "action": "cancel"}
                                        if kind == "browser_authentication"
                                        else None
                                    )
                                    if answer:
                                        with contextlib.suppress(Exception):
                                            await event(
                                                {
                                                    "type": "agent.session.input.computer_use_approval_request_result",
                                                    "request_id": ident,
                                                    "response": answer,
                                                },
                                                "cleanup-approval-"
                                                + hashlib.sha256(ident.encode()).hexdigest()[:24],
                                            )
                            with contextlib.suppress(Exception):
                                await event(
                                    {"type": "agent.session.input.cancel"},
                                    "cleanup-cancel-" + str(attempt),
                                )

                        if not result["turn_completed"]:
                            await cancel_pending(0)
                        # Deletion takes priority over a final usage refresh.
                        # A missing billing receipt must never delay shutdown.
                        accepted = False
                        for attempt in range(8):
                            retryable = True
                            if not accepted:
                                try:
                                    deleted = await client.delete(
                                        f"/agents/sessions/{sid}",
                                        timeout=httpx.Timeout(10, connect=3),
                                    )
                                    if deleted.status_code not in {200, 202, 204, 404, 409}:
                                        return
                                    try:
                                        value = deleted.json() if deleted.content else {}
                                    except ValueError:
                                        value = {}
                                    accepted = (
                                        deleted.status_code in {202, 204, 404}
                                        or value.get("deleted") is True
                                    )
                                    result["session_deleted"] = accepted
                                    retryable = deleted.status_code == 409 or accepted
                                    if deleted.status_code == 409:
                                        await cancel_pending(attempt + 1)
                                except httpx.TransportError:
                                    pass  # Read back before retrying this idempotent cleanup.
                            result["cleanup_attempts"] = attempt + 1
                            try:
                                response = await client.get(f"/agents/sessions/{sid}")
                                if response.status_code == 404:
                                    result["deletion_readback"] = result["session_deleted"] = True
                                    return
                                if response.status_code != 200:
                                    return
                            except httpx.TransportError:
                                pass
                            if not retryable:
                                return
                            await asyncio.sleep(min(4.0, self.poll_seconds * (2**attempt)))

                with contextlib.suppress(Exception):
                    await asyncio.wait_for(cleanup(), self.cleanup_seconds)
                if reader:
                    reader.cancel()
                    with contextlib.suppress(asyncio.CancelledError, Exception):
                        await reader
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        return result

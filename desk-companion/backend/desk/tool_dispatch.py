"""Bounded per-session tool dispatch without blocking realtime receive loops.

Cancelling an asyncio.to_thread waiter does not stop the underlying thread. Each
invocation therefore retains a thread-safe cancellation flag and discards any late
unapproved proposal in the thread itself, including after the socket has closed.
"""

import asyncio
import contextlib
import hashlib
import json
import threading
from dataclasses import dataclass, field

from .store import DomainError, encode


@dataclass
class Invocation:
    event: dict
    signature: str
    cancelled: threading.Event = field(default_factory=threading.Event)
    lock: threading.RLock = field(default_factory=threading.RLock)
    result: dict | None = None
    task: asyncio.Task | None = None
    delivered: bool = False


class ToolDispatcher:
    def __init__(self, runtime, session_id):
        self.runtime, self.session_id = runtime, session_id
        self.calls: dict[str, Invocation] = {}
        self.results = asyncio.Queue(maxsize=64)
        self.slots = asyncio.Semaphore(2)
        self.closed = False
        self.generation = 0

    def _enqueue(self, event, result):
        try:
            self.results.put_nowait((event, result))
        except asyncio.QueueFull:
            raise DomainError("TOOL_LIMIT_REACHED", 429) from None

    def submit(self, event):
        if self.closed:
            return
        # A queued result must keep its interruption fence even if its completed
        # invocation is later recycled. This also covers rejected requests.
        event = {**event, "_dispatch_generation": self.generation}
        call_id = event.get("id")
        if not isinstance(call_id, str) or not 1 <= len(call_id) <= 150:
            raise DomainError("TOOL_ARGUMENTS_INVALID", 422)
        arguments = event.get("arguments", {})
        try:
            arguments = json.loads(arguments) if isinstance(arguments, str) else arguments
            if not isinstance(arguments, dict) or len(encode(arguments)) > 20000:
                raise ValueError()
        except (TypeError, ValueError):
            self._enqueue(event, {"error": "TOOL_ARGUMENTS_INVALID", "saved": False})
            return
        event = {**event, "arguments": arguments}
        signature = encode({"name": event.get("name"), "arguments": arguments})
        old = self.calls.get(call_id)
        if old:
            if old.signature != signature:
                self._enqueue(event, {"error": "TOOL_CALL_CONFLICT", "saved": False})
            elif old.result is not None and old.delivered:
                old.delivered = False
                self._enqueue(event, old.result)
            return  # An in-flight duplicate shares the original response.
        if len(self.calls) >= 32:
            # Retain ordinary calls so interruption can still cancel their
            # drafts. One extra slot is reserved for safety stop, and only a
            # completed stop may be evicted to admit a later stop.
            completed_stop = next(
                (
                    key
                    for key, call in self.calls.items()
                    if call.event["name"] == "stop_physical_outputs"
                    and call.result is not None
                    and call.task is not None
                    and call.task.done()
                    and call.delivered
                ),
                None,
            )
            if event["name"] != "stop_physical_outputs":
                self._enqueue(event, {"error": "TOOL_LIMIT_REACHED", "saved": False})
                return
            if completed_stop is not None:
                del self.calls[completed_stop]
            elif len(self.calls) >= 33:
                self._enqueue(event, {"error": "TOOLS_BUSY", "saved": False})
                return
        pending_limit = 9 if event["name"] == "stop_physical_outputs" else 8
        if sum(call.result is None for call in self.calls.values()) >= pending_limit:
            self._enqueue(event, {"error": "TOOLS_BUSY", "saved": False})
            return
        call = Invocation(event, signature)
        self.calls[call_id] = call
        call.task = asyncio.create_task(self._run(call))

    def _discard(self, result):
        if not result:
            return
        with contextlib.suppress(DomainError):
            if "proposal" in result:
                proposal_id = result["proposal"]["id"]
                self.runtime.assistant.decide(proposal_id, "cancel", "voice-discard/" + proposal_id)
            if "job" in result and result["job"]["state"] == "review":
                job_id = result["job"]["id"]
                self.runtime.jobs.cancel(job_id, "voice-discard/" + job_id, review_only=True)

    def _invoke(self, call):
        if call.cancelled.is_set():
            result = {"error": "TOOL_CANCELLED", "saved": False}
        else:
            try:
                result = self.runtime.assistant.tool(
                    call.event["name"],
                    call.event["arguments"],
                    "voice/"
                    + hashlib.sha256((self.session_id + call.event["id"]).encode()).hexdigest(),
                )
            except DomainError as error:
                result = {"error": error.code, "saved": False}
            except Exception:
                result = {"error": "TOOL_FAILED", "saved": False}
        with call.lock:
            if call.cancelled.is_set():
                self._discard(result)
                result = {"error": "TOOL_CANCELLED", "saved": False}
            call.result = result
        return result

    async def _run(self, call):
        # A hardware stop must not wait behind normal queries or draft preparation.
        if call.event["name"] == "stop_physical_outputs":
            result = await asyncio.to_thread(self._invoke, call)
        else:
            async with self.slots:
                result = await asyncio.to_thread(self._invoke, call)
        if not self.closed:
            await self.results.put((call.event, result))

    def _cancel(self, ids=None, pending_only=False):
        for call_id, call in list(self.calls.items()):
            if (ids is not None and call_id not in ids) or (pending_only and call.delivered):
                continue
            with call.lock:
                call.cancelled.set()
                self._discard(call.result)
                if call.result is not None:
                    call.result = {"error": "TOOL_CANCELLED", "saved": False}

    async def cancel(self, ids=None):
        if ids is None:
            self.generation += 1
        # Fence delivery immediately on the event-loop thread, before waiting
        # for any database cleanup or occupied worker thread.
        for call_id, call in self.calls.items():
            if ids is None or call_id in ids:
                call.cancelled.set()
        await asyncio.to_thread(self._cancel, ids)

    def current_result(self, event, result):
        if event.get("_dispatch_generation", self.generation) != self.generation:
            return {"error": "TOOL_CANCELLED", "saved": False}
        call = self.calls.get(event["id"])
        if call and call.cancelled.is_set() and result.get("error") != "TOOL_CALL_CONFLICT":
            return {"error": "TOOL_CANCELLED", "saved": False}
        return result

    def delivered(self, call_id):
        if call_id in self.calls:
            self.calls[call_id].delivered = True

    def stop_accepting(self):
        self.closed = True
        for call in self.calls.values():
            if not call.delivered:
                call.cancelled.set()

    async def close(self):
        self.stop_accepting()
        await asyncio.to_thread(self._cancel, None, True)
        tasks = [call.task for call in self.calls.values() if call.task]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

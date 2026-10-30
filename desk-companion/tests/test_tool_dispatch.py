import asyncio
import json
import threading
import time

import pytest

from desk.app import create_app
from desk.store import DomainError
from desk.tool_dispatch import ToolDispatcher
from desk.voice import VoiceConfig
from test_voice_google import FakeProvider


def event(call_id="one", name="calendar_create_draft", arguments=None):
    return {
        "id": call_id,
        "name": name,
        "arguments": arguments
        if arguments is not None
        else {
            "event": {
                "title": "Fictional delayed fixture",
                "start_local": "2026-10-07T12:00",
                "end_local": "2026-10-07T13:00",
            }
        },
    }


def test_inflight_duplicates_execute_once_and_changed_arguments_are_rejected(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    original, entered, release, count = (
        runtime.assistant.tool,
        threading.Event(),
        threading.Event(),
        [],
    )

    def slow(*args):
        count.append(args)
        entered.set()
        assert release.wait(5)
        return original(*args)

    runtime.assistant.tool = slow

    async def scenario():
        dispatch = ToolDispatcher(runtime, "session-fixture")
        try:
            dispatch.submit(event())
            assert await asyncio.to_thread(entered.wait, 2)
            dispatch.submit(event())
            dispatch.submit(event(arguments={"changed": True}))
            _, conflict = await asyncio.wait_for(dispatch.results.get(), 1)
            assert conflict["error"] == "TOOL_CALL_CONFLICT"
            release.set()
            _, result = await asyncio.wait_for(dispatch.results.get(), 2)
            assert "proposal" in result and len(count) == 1
            dispatch.delivered("one", result)
            dispatch.submit(event())
            _, duplicate = await asyncio.wait_for(dispatch.results.get(), 1)
            assert duplicate == result and len(count) == 1
        finally:
            release.set()
            await dispatch.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("close", [False, True])
def test_interrupt_or_disconnect_cancels_late_draft_in_underlying_thread(tmp_path, close):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    original, entered, release, returned = (
        runtime.assistant.tool,
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )

    def slow(*args):
        entered.set()
        assert release.wait(5)
        value = original(*args)
        returned.set()
        return value

    runtime.assistant.tool = slow

    async def scenario():
        dispatch = ToolDispatcher(runtime, "cancel-fixture")
        try:
            dispatch.submit(event())
            assert await asyncio.to_thread(entered.wait, 2)
            if close:
                await dispatch.close()
            else:
                await dispatch.cancel(["one"])
            release.set()
            assert await asyncio.to_thread(returned.wait, 2)
            # Wait for the invocation's own post-return cleanup, not just the tool.
            for _ in range(200):
                if dispatch.calls["one"].result is not None:
                    break
                await asyncio.sleep(0.01)
            assert dispatch.calls["one"].result["error"] == "TOOL_CANCELLED"
            assert not runtime.assistant.proposals()
        finally:
            release.set()
            await dispatch.close()

    asyncio.run(scenario())


def test_cancelled_voice_draft_does_not_cancel_owner_approved_job(tmp_path, monkeypatch):
    monkeypatch.setenv("DESK_COMPUTER_ENABLED", "1")
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    from desk.jobs import JobApproval

    async def scenario():
        dispatch = ToolDispatcher(runtime, "approved-fixture")
        dispatch.submit(
            event(
                name="computer_job_draft",
                arguments={"title": "Fixture", "content": "Local fictional note"},
            )
        )
        _, result = await asyncio.wait_for(dispatch.results.get(), 2)
        job = runtime.jobs.detail(result["job"]["id"], review=True)
        runtime.jobs.approve(
            job["id"],
            JobApproval(expected_version=job["version"], intent_hash=job["intent_hash"]),
            "approve",
        )
        await dispatch.cancel()
        assert runtime.jobs.detail(job["id"])["state"] == "queued"
        await dispatch.close()

    asyncio.run(scenario())


def test_pending_capacity_is_bounded_and_stop_bypasses_slow_queries(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    release = threading.Event()

    def slow(name, *_):
        if name != "stop_physical_outputs":
            assert release.wait(5)
        return {"stopped": name == "stop_physical_outputs"}

    runtime.assistant.tool = slow

    async def scenario():
        dispatch = ToolDispatcher(runtime, "bounds-fixture")
        try:
            # Eight ordinary requests cannot consume the reserved stop admission.
            for i in range(8):
                dispatch.submit(event(str(i), "posture_status", {}))
            dispatch.submit(event("stop", "stop_physical_outputs", {}))
            _, result = await asyncio.wait_for(dispatch.results.get(), 1)
            assert result["stopped"]
            for i in range(9, 12):
                dispatch.submit(event(str(i), "posture_status", {}))
            _, result = await asyncio.wait_for(dispatch.results.get(), 1)
            assert result["error"] == "TOOLS_BUSY"
        finally:
            release.set()
            await dispatch.close()

    asyncio.run(scenario())


class FakeSocket:
    def __init__(self):
        self.incoming, self.outgoing = asyncio.Queue(), asyncio.Queue()

    async def send_json(self, value):
        await self.outgoing.put(value)

    async def iter_text(self):
        while True:
            yield json.dumps(await self.incoming.get())

    async def close(self):
        pass


def test_slow_tool_withholds_ungrounded_audio_but_never_blocks_interruption(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    voice = runtime.voice
    voice.config = VoiceConfig("qwen_audio", "wss://fixture.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime", "fixture", "not-a-key")
    original, entered, release = runtime.assistant.tool, threading.Event(), threading.Event()

    def slow(*args):
        entered.set()
        assert release.wait(5)
        return original(*args)

    runtime.assistant.tool = slow

    async def scenario():
        provider, socket = FakeProvider(), FakeSocket()
        voice.connector = lambda *args, **kwargs: provider
        voice.active, voice.started = True, time.monotonic()
        principal = {"kind": "owner", "session": runtime.store.authenticate("owner", "fixture")}
        running = asyncio.create_task(voice.run(socket, principal, "en"))
        try:
            assert (await asyncio.wait_for(socket.outgoing.get(), 2))["type"] == "ready"
            call = event()
            await provider.queue.put(
                {
                    "type": "response.function_call_arguments.done",
                    "call_id": call["id"],
                    "name": call["name"],
                    "arguments": json.dumps(call["arguments"]),
                }
            )
            assert await asyncio.to_thread(entered.wait, 2)
            assert (await asyncio.wait_for(socket.outgoing.get(), 1))["type"] == "turn_waiting"
            await provider.queue.put({"type": "response.audio.delta", "delta": "AAA="})
            # Pre-tool speech must not be presented as a completed business answer.
            # The following interrupt still has to pass the pending tool immediately.
            await provider.queue.put({"type": "input_audio_buffer.speech_started"})
            assert (await asyncio.wait_for(socket.outgoing.get(), 1))["type"] == "proposals_changed"
            assert (await asyncio.wait_for(socket.outgoing.get(), 1))["type"] == "interrupted"
            release.set()
            for _ in range(200):
                if any(
                    m.get("item", {}).get("type") == "function_call_output" for m in provider.sent
                ):
                    break
                await asyncio.sleep(0.01)
            returned = [
                m["item"]
                for m in provider.sent
                if m.get("item", {}).get("type") == "function_call_output"
            ]
            assert json.loads(returned[0]["output"])["error"] == "TOOL_CANCELLED"
            assert not runtime.assistant.proposals()
            await socket.incoming.put({"type": "stop"})
            await asyncio.wait_for(running, 2)
            assert not voice.active and voice.started is None
        finally:
            release.set()
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)

    asyncio.run(scenario())


def test_invalid_arguments_and_bounded_result_queue(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime

    async def scenario():
        dispatch = ToolDispatcher(runtime, "invalid-fixture")
        dispatch.submit(event(arguments=[]))
        _, result = await dispatch.results.get()
        assert result["error"] == "TOOL_ARGUMENTS_INVALID"
        for i in range(64):
            dispatch.submit(event(str(i), arguments=[]))
        with pytest.raises(DomainError, match="TOOL_LIMIT_REACHED"):
            dispatch.submit(event("overflow", arguments=[]))
        await dispatch.close()

    asyncio.run(scenario())


def test_stop_remains_available_after_lifetime_quota_without_growing_history(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    invocations = []

    def tool(name, *_):
        invocations.append(name)
        return {"stopped": name == "stop_physical_outputs"}

    runtime.assistant.tool = tool

    async def scenario():
        dispatch = ToolDispatcher(runtime, "full-session")
        try:
            for i in range(32):
                dispatch.submit(event(str(i), "posture_status", {}))
                _, result = await asyncio.wait_for(dispatch.results.get(), 1)
                dispatch.delivered(str(i), result)
            for i in range(3):
                dispatch.submit(event(f"stop-{i}", "stop_physical_outputs", {}))
                _, result = await asyncio.wait_for(dispatch.results.get(), 1)
                assert result == {"stopped": True}
                dispatch.delivered(f"stop-{i}", result)
                assert len(dispatch.calls) <= 33
            assert invocations.count("stop_physical_outputs") == 3
            dispatch.submit(event("ordinary-overflow", "posture_status", {}))
            _, result = await dispatch.results.get()
            assert result["error"] == "TOOL_LIMIT_REACHED"
        finally:
            await dispatch.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("gate", ["client_proposal", "provider_result"])
def test_interrupt_during_result_delivery_never_revives_cancelled_draft(tmp_path, gate):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    voice = runtime.voice
    voice.config = VoiceConfig("qwen_audio", "wss://fixture.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime", "fixture", "not-a-key")

    async def scenario():
        blocked, release, interrupted = asyncio.Event(), asyncio.Event(), asyncio.Event()

        class GatedSocket(FakeSocket):
            async def send_json(self, value):
                if gate == "client_proposal" and value.get("type") == "proposal":
                    blocked.set()
                    await release.wait()
                if value.get("type") == "interrupted":
                    interrupted.set()
                await super().send_json(value)

        class GatedProvider(FakeProvider):
            async def send(self, value):
                await super().send(value)
                data = json.loads(value)
                if (
                    gate == "provider_result"
                    and data.get("item", {}).get("type") == "function_call_output"
                ):
                    blocked.set()
                    await release.wait()

        provider, socket = GatedProvider(), GatedSocket()
        voice.connector = lambda *args, **kwargs: provider
        voice.active, voice.started = True, time.monotonic()
        principal = {"kind": "owner", "session": runtime.store.authenticate("owner", "fixture")}
        running = asyncio.create_task(voice.run(socket, principal, "en"))
        try:
            await asyncio.wait_for(socket.outgoing.get(), 2)
            call = event()
            await provider.queue.put(
                {
                    "type": "response.function_call_arguments.done",
                    "call_id": call["id"],
                    "name": call["name"],
                    "arguments": json.dumps(call["arguments"]),
                }
            )
            await asyncio.wait_for(blocked.wait(), 2)
            await socket.incoming.put({"type": "interrupt"})
            for _ in range(200):
                if not runtime.assistant.proposals():
                    break
                await asyncio.sleep(0.01)
            assert not runtime.assistant.proposals()
            if gate == "provider_result":
                await asyncio.wait_for(interrupted.wait(), 1)
            release.set()
            for _ in range(200):
                if any(item.get("type") == "response.cancel" for item in provider.sent):
                    break
                await asyncio.sleep(0.01)
            outputs = [
                item["item"]
                for item in provider.sent
                if item.get("item", {}).get("type") == "function_call_output"
            ]
            if gate == "client_proposal":
                assert outputs and json.loads(outputs[0]["output"])["error"] == "TOOL_CANCELLED"
            assert not any(item.get("type") == "response.create" for item in provider.sent)
            await socket.incoming.put({"type": "stop"})
            await asyncio.wait_for(running, 2)
        finally:
            release.set()
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)

    asyncio.run(scenario())


def test_stop_cache_does_not_evict_producer_blocked_by_result_backpressure(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    runtime.assistant.tool = lambda name, *_: {"stopped": name == "stop_physical_outputs"}

    async def scenario():
        dispatch = ToolDispatcher(runtime, "backpressure-fixture")
        try:
            for i in range(32):
                dispatch.submit(event(str(i), "posture_status", {}))
                await asyncio.wait_for(dispatch.results.get(), 1)
            for i in range(64):
                dispatch.submit(event(f"invalid-{i}", arguments=[]))
            dispatch.submit(event("stop", "stop_physical_outputs", {}))
            for _ in range(200):
                if dispatch.calls["stop"].result is not None:
                    break
                await asyncio.sleep(0.01)
            producer = dispatch.calls["stop"].task
            assert dispatch.calls["stop"].result == {"stopped": True}
            assert not producer.done()
            for i in range(5):
                with pytest.raises(DomainError, match="TOOL_LIMIT_REACHED"):
                    dispatch.submit(event(f"extra-stop-{i}", "stop_physical_outputs", {}))
            assert len(dispatch.calls) == 33
            assert dispatch.calls["stop"].task is producer
        finally:
            await dispatch.close()
        assert producer.done()

    asyncio.run(scenario())


def test_cached_and_rejected_results_keep_generation_fence_after_interrupt(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    runtime.assistant.tool = lambda name, *_: {"stopped": name == "stop_physical_outputs"}

    async def scenario():
        dispatch = ToolDispatcher(runtime, "generation-fixture")
        try:
            for i in range(32):
                dispatch.submit(event(str(i), "posture_status", {}))
                _, result = await dispatch.results.get()
                dispatch.delivered(str(i), result)
            dispatch.submit(event("stop-1", "stop_physical_outputs", {}))
            _, result = await dispatch.results.get()
            dispatch.delivered("stop-1", result)
            dispatch.submit(event("stop-1", "stop_physical_outputs", {}))
            dispatch.submit(event("stop-1", "stop_physical_outputs", {}))
            assert dispatch.results.qsize() == 1  # In-flight duplicates share delivery.
            dispatch.submit(event("stop-2", "stop_physical_outputs", {}))
            dispatch.submit(event("invalid", arguments=[]))
            await dispatch.cancel()
            while not dispatch.results.empty():
                queued_event, result = await dispatch.results.get()
                assert dispatch.current_result(queued_event, result)["error"] == "TOOL_CANCELLED"
        finally:
            await dispatch.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("rejected_arguments", [{"changed": True}, []])
def test_rejected_same_id_reply_does_not_abandon_late_draft_on_disconnect(
    tmp_path, rejected_arguments
):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    original, entered, release = runtime.assistant.tool, threading.Event(), threading.Event()

    def slow(*args):
        entered.set()
        assert release.wait(5)
        return original(*args)

    runtime.assistant.tool = slow

    async def scenario():
        dispatch = ToolDispatcher(runtime, "rejected-delivery-fixture")
        try:
            dispatch.submit(event())
            assert await asyncio.to_thread(entered.wait, 2)
            dispatch.submit(event(arguments=rejected_arguments))
            rejected_event, result = await asyncio.wait_for(dispatch.results.get(), 1)
            assert result["error"] in {"TOOL_CALL_CONFLICT", "TOOL_ARGUMENTS_INVALID"}
            # The voice result loop sends this rejection, then the socket closes
            # before the original invocation has returned its own proposal.
            dispatch.delivered(rejected_event["id"], result)
            await dispatch.close()
            release.set()
            for _ in range(200):
                if dispatch.calls["one"].result is not None:
                    break
                await asyncio.sleep(0.01)
            assert dispatch.calls["one"].result["error"] == "TOOL_CANCELLED"
            assert not runtime.assistant.proposals()
        finally:
            release.set()
            await dispatch.close()

    asyncio.run(scenario())

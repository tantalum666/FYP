"""Use a disposable localhost FYP login and the public weather endpoints; no model network access."""

from datetime import UTC, datetime
import json
from pathlib import Path
import socket
import tempfile
from threading import Thread
import time

import httpx
import uvicorn
from websockets.sync.client import connect

from desk.app import create_app
from desk.openai_live import OPENAI_LIVE_ENDPOINT
from desk.voice import VoiceConfig
from desk.weather_conversation import direct_query
from session_protocol_fixture import install_session_protocol
from voice_fixtures import Provider


class WeatherVoiceReplay(Provider):
    def __init__(self):
        super().__init__()
        self.result = None

    async def send(self, packet):
        await super().send(packet)
        v = json.loads(packet)
        if v["type"] == "session.start":
            await self.queue.put({"type": "session.started", "session": {"model": "gpt-live-1.1"}})
            for start, end, text in [(100, 410, "帮我查一下"), (411, 810, "东京的天气")]:
                await self.queue.put(
                    {
                        "type": "session.input_transcript.delta",
                        "delta": text,
                        "start_ms": start,
                        "end_ms": end,
                    }
                )
            for event in [
                {"type": "response.created", "response": {"id": "r"}},
                {
                    "type": "response.function_call_arguments.done",
                    "response_id": "r",
                    "name": "weather_query",
                    "call_id": "wx",
                    "arguments": "{}",
                },
                {
                    "type": "response.completed",
                    "response": {"id": "r", "usage": {"input_tokens": 5, "output_tokens": 3}},
                },
            ]:
                await self.queue.put(
                    {"type": "response.event", "event": event, "delegation_id": "weather_demo"}
                )
        elif v["type"] == "response.item.create":
            assert v["item"]["call_id"] == "wx"
            self.result = json.loads(v["item"]["output"])
            await self.queue.put(
                {
                    "type": "session.output_transcript.delta",
                    "start_ms": 1000,
                    "end_ms": 1900,
                    "delta": self.result["summary"],
                }
            )
        elif v["type"] == "session.close":
            await self.queue.put({"type": "session.closed", "usage": {"seconds": 2}})


def run():
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(Path(directory), password="fixture", scheduler=False)
        runtime = app.state.runtime
        sessions = install_session_protocol(runtime)
        runtime.text_ai.config.model = "gpt-6.2-sol"
        runtime.voice.config = VoiceConfig(
            "openai_live",
            OPENAI_LIVE_ENDPOINT,
            "gpt-live-1.1",
            "fake-only",
            "marin",
            backend_model="gpt-6.2-sol",
        )
        voice = WeatherVoiceReplay()
        runtime.voice.connector = lambda *a, **kw: voice
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
        worker = Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        worker.start()
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.02)
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}",
                headers={"X-Desk-Request": "1"},
                trust_env=False,
                timeout=30,
            ) as desk:
                desk.post(
                    "/api/session", json={"username": "owner", "password": "fixture"}
                ).raise_for_status()
                rows = []
                for idx, prompt in enumerate(
                    (
                        "帮我查一下东京的天气",
                        "帮我看一下香港的天气",
                        "What's the weather like in Cape Town today?",
                        "What's the weather in Reykjavík today?",
                        "What's the weather in Buenos Aires today?",
                        "香港明天的天气怎么样？",
                    )
                ):
                    args = direct_query(prompt)
                    reply = desk.post(
                        "/api/assistant/messages/stream",
                        headers={"X-Operation-Id": f"weather-{idx}"},
                        json={"message": prompt},
                    )
                    reply.raise_for_status()
                    events = [
                        json.loads(line[5:])
                        for line in reply.text.splitlines()
                        if line.startswith("data:")
                    ]
                    final = next(e["reply"]["message"] for e in events if e["type"] == "done")
                    data = desk.post("/api/weather/query", json=args).raise_for_status().json()
                    assert data["available"] and data["summary"] == final, (
                        prompt,
                        data.get("status"),
                        data["summary"],
                        final,
                    )
                    assert [e["phase"] for e in events if e.get("tool") == "weather_query"] == [
                        "started",
                        "finished",
                    ]
                    if args["location"] == "香港" and args.get("start_date") is None:
                        assert data.get("current", {}).get("basis") == "station" and data.get(
                            "local_forecast"
                        ), data["summary"]
                    rows.append(
                        {
                            "question": prompt,
                            "reply": final,
                            **{
                                k: data[k]
                                for k in (
                                    "area",
                                    "local_date",
                                    "timezone",
                                    "source",
                                    "country_code",
                                    "current",
                                    "local_forecast",
                                    "days",
                                    "issued_at",
                                )
                                if k in data
                            },
                        }
                    )
                assert (
                    not sessions.creations
                    and runtime.data.preferences()["weather_location"] == "none"
                )
                sessions.next_calls = [
                    (
                        "weather_query",
                        {
                            "location": "Tokyo",
                            "period": "forecast",
                            "days": 3,
                            "start_date": "tomorrow",
                            "language": "en",
                        },
                    )
                ]

                def answer():
                    if sessions.functions:
                        data = json.loads(sessions.functions[-1][0][0]["output"])
                        sessions.final = json.dumps(
                            {"message": data["summary"], "delivery": "neutral"}
                        )

                sessions.on_check = answer
                response = (
                    desk.post(
                        "/api/assistant/messages",
                        headers={"X-Operation-Id": "session-weather"},
                        json={
                            "message": "I am planning a trip. Could you look up the next three Tokyo forecasts starting tomorrow?"
                        },
                    )
                    .raise_for_status()
                    .json()
                )
                returned = json.loads(sessions.functions[0][0][0]["output"])
                assert response["message"] == returned["summary"] and len(returned["days"]) == 3
                session_tools = sessions.creations[0]["agent"]["tools"]
                fspec = next(t["parameters"] for t in session_tools if t["name"] == "weather_query")
                ticket = (
                    desk.post("/api/voice/tickets", json={}).raise_for_status().json()["ticket"]
                )
                with connect(f"ws://127.0.0.1:{port}/api/voice/ws", proxy=None) as ws:
                    ws.send(json.dumps({"ticket": ticket, "language": "zh"}))
                    while True:
                        e = json.loads(ws.recv(timeout=24))
                        assert e["type"] != "error", e
                        if e["type"] == "transcript" and e["role"] == "assistant":
                            assert (
                                voice.result["country_code"] == "JP"
                                and e["text"] == voice.result["summary"]
                            )
                            ws.send(json.dumps({"type": "stop"}))
                            break
                return {
                    "checked_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                    "public_sources_live": True,
                    "openai_network_calls": 0,
                    "actual_loopback_composer_sse": rows,
                    "preference_after_explicit_lookups": runtime.data.preferences()[
                        "weather_location"
                    ],
                    "ordinary_sessions_protocol_replay": {
                        "model": sessions.creations[0]["agent"]["model"],
                        "required_weather_arguments": fspec["required"],
                        "reply": response["message"],
                        "days": returned["days"],
                    },
                    "actual_loopback_voice_socket_with_replayed_upstream": {
                        "model": "gpt-live-1.1",
                        "delegation": "gpt-6.2-sol",
                        "user_transcript_chunks": 2,
                        "tool_result_bound_to_expected_call": True,
                        "destination": voice.result["country_code"],
                        "caption_echoed_from_public_result": voice.result["summary"],
                        "audio_generated": False,
                    },
                }
        finally:
            server.should_exit = True
            worker.join(timeout=6)
            sock.close()


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, allow_nan=False))

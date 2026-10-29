"""Synthetic speech and an isolated real Desk Companion service fixture."""

import json
import subprocess
import wave
from datetime import datetime, timezone

from desk.assistant import TOOLS
from desk.runtime import Runtime
from desk.schemas import CreateEvents, EventInput
from desk.store import Store
from desk.tool_policy import execute_tool

VOICES = {
    "en": "Samantha (英语（美国）)",
    "zh": "Tingting (中文（中国大陆）)",
    "yue": "Sinji (中文（香港）)",
}
LINES = {
    "calendar-en": (
        "en",
        "Please check tomorrow's meetings. How many are there, and when do they start?",
    ),
    "calendar-zh": ("zh", "请查一下明天有几场会议，分别几点开始？"),
    "calendar-yue": ("yue", "幫我睇吓聽日有幾多個會議，分別幾點開始？"),
    "memory-en": ("en", "Please remember that my fictional project code name is Azure Finch."),
    "memory-zh": ("zh", "请记住，我的虚构项目代号是蓝色云雀。"),
    "interrupt-en": ("en", "Explain a detailed study plan for the next five days."),
    "stop-en": ("en", "Stop. Just say ready, and nothing else."),
}


def speech(name, directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (name + ".wav")
    language, text = LINES[name]
    if not path.exists():
        subprocess.run(
            [
                "say",
                "-v",
                VOICES[language],
                "--file-format=WAVE",
                "--data-format=LEI16@24000",
                "-o",
                str(path),
                text,
            ],
            check=True,
        )
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 24000):
            raise ValueError("INVALID_FIXTURE_AUDIO")
        data = wav.readframes(wav.getnframes())
    if len(data) > 20 * 48000:
        raise ValueError("FIXTURE_TOO_LONG")
    return data


class Fixture:
    def __init__(self, directory, case):
        def clock():
            return datetime(2026, 10, 29, 2, tzinfo=timezone.utc)

        self.runtime = Runtime(Store(directory, clock=clock, password="fictional-evaluation-only"))
        for i, (title, start, end) in enumerate(
            [
                ("Design review", "09:30", "10:00"),
                ("Project check-in", "14:00", "14:30"),
                ("Software demo", "16:00", "16:30"),
            ]
        ):
            self.runtime.store.create(
                CreateEvents(
                    event=EventInput(
                        title=title,
                        start_local=f"2026-10-30T{start}",
                        end_local=f"2026-10-30T{end}",
                        visibility="displayable",
                        reminder_minutes=[],
                    )
                ),
                f"seed-{i}",
            )
        allowed = (
            {"calendar_query"}
            if case.startswith("calendar")
            else {"memory_save_draft", "memory_query"}
            if case.startswith("memory")
            else set()
        )
        self.tools = [{"type": "function", **t} for t in TOOLS if t["name"] in allowed]
        self.allowed = allowed
        self.calls = {}

    def call(self, call_id, name, raw):
        signature = (name, raw)
        if call_id in self.calls:
            old = self.calls[call_id]
            if old["signature"] != signature:
                return {"error": "TOOL_CALL_CONFLICT", "saved": False}
            return old["result"]
        if name not in self.allowed or len(raw) > 5000:
            result = {"error": "TOOL_NOT_ALLOWED", "saved": False}
        else:
            try:
                arguments = json.loads(raw)
            except json.JSONDecodeError:
                arguments = None
            result = execute_tool(
                self.runtime, name, arguments, call_id, scope="openai-evaluation", channel="voice"
            )
        self.calls[call_id] = {"name": name, "signature": signature, "result": result}
        return result

    def evidence(self):
        return {
            "tools": [{"name": c["name"], "result": c["result"]} for c in self.calls.values()],
            "active_memories": self.runtime.memory.for_model(),
            "pending_proposals": self.runtime.assistant.proposals(),
        }

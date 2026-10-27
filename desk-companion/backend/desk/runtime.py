"""Local workspace services and explicit capability state."""

import hashlib
import json
import platform

from .access import AccessService
from .assistant import AssistantService
from .outputs import OutputRequest, OutputService
from .posture_service import PostureService
from .store import DomainError
from .workspace_data import WorkspaceData
from .voice import VoiceService
from .exchange import ExchangeService
from .google_calendar import GoogleCalendar
from .tasks import TaskService
from .text_ai import TextAssistant
from .jobs import JobService
from .memory import MemoryService
from .nudges import NudgeService
from .persona import PersonaService


class Runtime:
    def __init__(self, store, allow_replay=False):
        self.store = store
        self.allow_replay = allow_replay
        self.access = AccessService(store)
        self.posture = PostureService(store)
        self.outputs = OutputService(store)
        self.tasks = TaskService(self)
        self.memory = MemoryService(self)
        self.persona = PersonaService(self)
        self.jobs = JobService(self)
        self.worker_health = {}
        self.assistant = AssistantService(self)
        self.data = WorkspaceData(store)
        self.nudges = NudgeService(self)
        self.voice = VoiceService(self)
        self.exchange = ExchangeService(self)
        self.google = GoogleCalendar(self)
        self.text_ai = TextAssistant(self)
        self.posture.on_prompt = self.on_posture_prompt

    def on_posture_prompt(self, event):
        # Replayed observations must never move connected live hardware.
        state = self.outputs.snapshot()
        if event.get("source") != "live" or state["source"] != "live":
            return
        key = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
        for kind, preset in [("light", "attention"), ("arm", "attention")]:
            try:
                self.outputs.request(
                    OutputRequest(kind=kind, preset=preset), "feedback/" + kind + "/" + key
                )
            except DomainError:
                pass  # Screen feedback remains available when an output cannot execute.

    def snapshot(self, principal):
        result = {
            "computer": self.jobs.capabilities(),
            "workers": dict(self.worker_health),
            "tasks": self.tasks.snapshot(),
            "text_ai": self.text_ai.snapshot(),
            "posture": self.posture.snapshot(),
            "outputs": self.outputs.snapshot(),
            "principal": principal,
            "replay_available": self.allow_replay,
            "runtime": "mac_local" if platform.system() == "Darwin" else "linux_local",
            "voice": self.voice.snapshot(),
            "calendar_extras": self.data.snapshot(),
            "google": self.google.snapshot(),
            "output_history": self.outputs.history(),
        }
        if principal["kind"] == "owner":
            result["pairing"] = self.access.listing()
        return result

    def device_status(self):
        posture, outputs = self.posture.snapshot(), self.outputs.snapshot()
        return {
            "camera": "connected" if posture["connected"] else "not_connected",
            "posture": posture["status"],
            "source": posture["source"] or "none",
            "voice": self.voice.snapshot()["state"],
            "arm": "connected"
            if outputs["connected"] and "arm" in outputs["capabilities"]
            else "not_connected",
            "weather": "not_connected",
            "external_calendar": "connected"
            if self.google.snapshot()["connected"]
            else "not_connected",
            "runtime": "mac_local" if platform.system() == "Darwin" else "linux_local",
        }

    def tick(self):
        self.store.tick()
        self.posture.tick()
        self.tasks.tick()
        self.memory.expire_due()
        self.nudges.tick()
        self.jobs.expire()

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
from .wake_listening import WakeListening
from .exchange import ExchangeService
from .google_calendar import GoogleCalendar
from .tasks import TaskService
from .text_ai import TextAssistant
from .jobs import JobService
from .backups import LocalBackups
from .memory import MemoryService
from .digest import DigestService
from .moments import MomentService
from .goals import GoalService
from .nudges import NudgeService
from .notify import Notifier
from .web_push import HttpPushSender, PushService, push_enabled
from .persona import PersonaService
from .profile import ProfileService
from .permissions import PermissionService

from .retained_chat import RetainedChat
from .personal_context import PersonalContext
from .personal_memory import PersonalMemoryAdapter
from .conversations import ConversationService
from .routines import RoutineService
from .sources import SourceService
from .artifacts import ArtifactService
from .agent_runs import AgentRunService
from .browser_jobs import BrowserService
from .connectors.service import build_connector_service
from .connectors.agent_adapter import connector_adapters
from .application_work import adapters as application_adapters
from .work_search import WorkSearchService
from .responsibilities import ResponsibilityService
from .work_capacity import WorkCapacityService
from .public_capture_schema import SCHEMA_VERSION
from .public_captures import PublicCaptureService


class Runtime:
    def __init__(
        self, store, allow_replay=False, connector_configs=(), *, public_capture_enabled=False
    ):
        if store.schema_version != SCHEMA_VERSION:
            raise DomainError("SCHEMA_MIGRATION_REQUIRED")
        with store.connection() as conn:
            if conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='personal_memories'"
            ).fetchone():
                raise DomainError("PERSONAL_MEMORY_MIGRATION_REQUIRED")
        self.store = store
        self.allow_replay = allow_replay
        self.access = AccessService(store)
        self.posture = PostureService(store)
        self.outputs = OutputService(store)
        self.tasks = TaskService(self)
        self.goals = GoalService(self)
        self.memory = MemoryService(self)
        self.personal_context = PersonalContext(self)
        self.memories = PersonalMemoryAdapter(self)
        self.conversations = ConversationService(self)
        self.responsibilities = ResponsibilityService(self)
        self.routines = RoutineService(self)
        self.profile = ProfileService(self)
        self.persona = PersonaService(self)
        self.jobs = JobService(self)
        self.worker_health = {}
        self.assistant = AssistantService(self)
        self.permissions = PermissionService(self)
        self.data = WorkspaceData(store)
        self.nudges = NudgeService(self)
        self.moments = MomentService(self)
        self.digests = DigestService(self)
        self.notify = Notifier(
            self.store,
            push=PushService(
                self.store, HttpPushSender(), self.store.directory / "vapid-private.pem"
            )
            if push_enabled()
            else None,
        )
        self.voice = VoiceService(self)
        self.wake = WakeListening(self)
        self.exchange = ExchangeService(self)
        self.backups = LocalBackups(self)
        self.google = GoogleCalendar(self)
        self.text_ai = TextAssistant(self)
        self.retained_chat = RetainedChat(self)
        self.sources = SourceService(self)
        self.artifacts = ArtifactService(self)
        self.browser_jobs = BrowserService(self)
        self.connectors = build_connector_service(self, connector_configs)
        self.agent_tool_adapters = {**connector_adapters(self.connectors), **application_adapters()}
        self.agent_runs = AgentRunService(self)
        self.work_search = WorkSearchService(self)
        self.work_capacity = WorkCapacityService(self)
        self.public_captures = PublicCaptureService(self, enabled=public_capture_enabled)
        self.store.operation_guard = self.agent_runs.guard_operation
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
            "personal_context_visible": self.personal_context.visible(principal),
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
            result["permissions"] = self.permissions.snapshot()
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
        self.memories.expire()
        self.nudges.tick()
        self.goals.tick()
        self.jobs.expire()
        self.routines.tick()
        self.voice.work.cleanup()

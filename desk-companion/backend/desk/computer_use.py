"""Native computer preparation executor on the existing approval/job lifecycle."""

import hashlib
import json
import os
import struct

from .application_runtime import read_regular
from .browser_policy import digest
from .computer_use_files import write_file as exclusive_write
from .browser_supervisor import BrowserSupervisor
from .calendar import iso
from .computer import ExecutionRejected
from .computer_use_models import (
    ComputerUseInput,
    ComputerUseReceipt,
    MAX_SCREEN_BYTES,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)
from .computer_use_protocol import OpenAIComputerProtocol
from .computer_use_network import local_browser_proxy
from .store import DomainError, encode


class ComputerSupervisor(BrowserSupervisor):
    worker_module = "desk.computer_use_worker"
    stage_names = {"computer_open", "computer_observe", "computer_action"}
    stage_limit = 180
    protocol_limit = 1_000_000


class ComputerUseExecutor:
    identity = "public_browser_computer_v1"

    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.enabled = os.environ.get("DESK_COMPUTER_USE_ENABLED") == "1"
        self.root = (self.store.directory / "computer-use").absolute()
        self.supervisor = ComputerSupervisor()
        self.browser_proxy = local_browser_proxy(os.environ.get("DESK_BROWSER_PROXY_URL", ""))
        self.scope = "public_browser:" + digest(
            [self.identity, self.supervisor.executable, str(self.root), self.browser_proxy]
        )
        self.protocol_factory = OpenAIComputerProtocol
        self.blocker = self.root / "cleanup-required"
        self.active_job = None

    def status(self):
        config = self.runtime.text_ai.config
        reason = self.supervisor.readiness()
        blocked = self.blocker.exists() and self.active_job is None
        return {
            "enabled": self.enabled,
            "configured": config.provider == "openai"
            and config.valid()
            and config.model == "gpt-6.1-sol"
            and reason is None
            and not blocked,
            "reason": "COMPUTER_CLEANUP_REQUIRED" if blocked else reason,
            "busy": self.active_job is not None,
            "model": config.model,
            "scope": "public_browsing_and_preparation",
            "real_transactions": False,
            "max_steps": 12,
        }

    def provider_revision(self):
        cfg = self.runtime.text_ai.config
        parts = [cfg.provider, cfg.model, cfg.endpoint]
        if cfg.proxy_url:
            parts.append(cfg.proxy_url)
        return digest(parts)

    def prepare_request(self, payload: ComputerUseInput, job_id, principal):
        if not principal or principal.get("kind") != "owner" or not principal.get("session"):
            raise DomainError("OWNER_REQUIRED", 403)
        self.runtime.personal_context.require_visible(principal)
        self.require_ready()
        request = payload.model_dump()
        source_hash = None
        if payload.source_job_id:
            source = self.runtime.jobs.detail(payload.source_job_id, review=True)
            old = source["request"]
            if (
                source["state"] not in {"succeeded", "cancelled", "failed", "unknown"}
                or old.get("action") != "computer_use"
                or any(
                    old.get(k) != request.get(k)
                    for k in ("start_url", "allowed_origins", "task_id")
                )
                or old["scope"] != self.scope
            ):
                raise DomainError("COMPUTER_SOURCE_CHANGED", 409)
            try:
                checked = self.verify(old)
            except (OSError, ValueError, KeyError):
                raise DomainError("COMPUTER_SOURCE_CHANGED", 409) from None
            source_hash = checked["readback"]["state_sha256"]
            if not checked["verified"] or (
                source.get("result") and checked["sha256"] != source["result"]["sha256"]
            ):
                raise DomainError("COMPUTER_SOURCE_CHANGED", 409)
        request.update(
            artifact_id=job_id,
            executor=self.identity,
            scope=self.scope,
            content=payload.goal,
            session_hash=hashlib.sha256(principal["session"].encode()).hexdigest(),
            privacy_revision=digest(self.runtime.personal_context.revision()),
            provider_revision=self.provider_revision(),
            source_state_sha256=source_hash,
        )
        return request

    def require_ready(self):
        state = self.status()
        if not state["enabled"] or not state["configured"]:
            raise DomainError(state["reason"] or "COMPUTER_USE_UNAVAILABLE", 409)

    def current(self, request, conn=None):
        if self.blocker.exists() and self.active_job is None:
            raise DomainError("COMPUTER_CLEANUP_REQUIRED", 409)
        if conn is None:
            with self.store.connection() as owned:
                return self.current(request, owned)
        if not conn.execute(
            "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
            (request["session_hash"], iso(self.store.clock())),
        ).fetchone():
            raise DomainError("RUN_SESSION_EXPIRED", 403)
        if self.store.settings(conn)["hide_private"] or request["privacy_revision"] != digest(
            self.runtime.personal_context.revision()
        ):
            raise DomainError("PROVIDER_CONTEXT_CHANGED", 409)
        if request["provider_revision"] != self.provider_revision():
            raise DomainError("PROVIDER_CONTEXT_CHANGED", 409)

    def execute(self, request, checkpoint):
        self.current(request)
        self.active_job = request["artifact_id"]
        try:
            return self._execute(request, checkpoint)
        finally:
            self.active_job = None

    def _execute(self, request, checkpoint):
        directory = self.root / request["artifact_id"]
        directory.mkdir(parents=True, mode=0o700)
        # An interrupted parent may not know whether browser children exited.
        # New admission stays blocked until cleanup is actually confirmed.
        exclusive_write(self.root, "cleanup-required", request["artifact_id"].encode())
        if request["source_job_id"]:
            state = read_regular(
                self.root / request["source_job_id"] / "browser-state.json", 2_000_000
            )
            if hashlib.sha256(state).hexdigest() != request["source_state_sha256"]:
                self.blocker.unlink()
                raise ExecutionRejected("COMPUTER_SOURCE_CHANGED", 409)
            exclusive_write(directory, "source-state.json", state)
        usages, calls = [], 0
        protocol = self.protocol_factory(
            self.runtime.text_ai.config,
            request["goal"],
            request["allowed_origins"],
            transport=self.runtime.text_ai.transport,
            on_usage=usages.append,
        )

        def fence(_stage=None):
            checkpoint()
            self.current(request)

        def observe(value):
            nonlocal calls
            calls += 1
            if (
                calls > request["max_steps"]
                or value["sequence"] != calls
                or value["screen"] != f"screen-{calls}.png"
            ):
                raise ValueError("Unexpected computer observation")
            image = read_regular(directory / value["screen"], MAX_SCREEN_BYTES)
            if (
                image[:8] != b"\x89PNG\r\n\x1a\n"
                or struct.unpack(">II", image[16:24]) != (SCREEN_WIDTH, SCREEN_HEIGHT)
                or hashlib.sha256(image).hexdigest() != value["sha256"]
            ):
                raise ValueError("Screen bytes or coordinates do not match")
            temporary = directory / ".latest-new"
            with temporary.open("w") as file:
                file.write(encode(value))
                file.flush()
                os.fsync(file.fileno())
            temporary.replace(directory / "latest.json")
            # Reuse the existing provider-attempt ledger; a failed attempt still
            # occupies its call slot and is never automatically re-sent.
            usage_id = self.runtime.text_ai._reserve_usage("computer_use")
            try:
                response = protocol.step(value, image, fence)
            except DomainError:
                raise
            except Exception:
                # Do not replay an uncertain paid request or its possible input.
                # Let the browser save its observed state and close normally.
                return {
                    "finish": True,
                    "outcome": "needs_owner",
                    "reason": "provider_step_unavailable",
                }
            usage = usages[-1] if usages else {}
            numeric = {k: v for k, v in usage.items() if type(v) in (int, float)}
            with self.store.connection(write=True) as conn:
                conn.execute(
                    "UPDATE text_ai_usage SET usage=? WHERE id=?", (encode(numeric), usage_id)
                )
            return response

        outcome = self.supervisor.run(
            {
                "operation": "execute",
                "intent": {key: request[key] for key in ("start_url", "allowed_origins", "max_steps")},
                "resume_state": bool(request["source_job_id"]),
                "browser_proxy": self.browser_proxy,
            },
            directory,
            fence,
            timeout=180,
            on_observation=observe,
        )
        if outcome.cleanup_confirmed:
            self.blocker.unlink(missing_ok=True)
        if not outcome.cleanup_confirmed or not outcome.value:
            raise RuntimeError("Computer execution/cleanup is uncertain; inspect before retry")
        if not outcome.error:
            fence()
        value = outcome.value
        image = read_regular(directory / value["observation"]["screen"], MAX_SCREEN_BYTES)
        if hashlib.sha256(image).hexdigest() != value["observation"]["sha256"]:
            raise ValueError("Final screenshot changed")
        state = read_regular(directory / "browser-state.json", 2_000_000)
        result = {
            "job_id": request["artifact_id"],
            "scope": self.scope,
            "outcome": value["outcome"],
            "reason": value["reason"],
            "observation": value["observation"],
            "state_sha256": hashlib.sha256(state).hexdigest(),
            "calls": calls,
            "browser_close_confirmed": True,
            "quality": "not_goal_completion",
            "demo_submissions": value["demo_submissions"],
            "demo": value["demo"],
            "browser_version": value["browser_version"],
            "network_boundary": value["network_boundary"],
        }
        exclusive_write(directory, "receipt.json", encode(result).encode())
        if outcome.error:
            raise ExecutionRejected(outcome.error, 409)

    def verify(self, request):
        directory = self.root / request["artifact_id"]
        raw = read_regular(directory / "receipt.json", 128000)
        result = json.loads(raw)
        observation = result["observation"]
        screen_name = observation["screen"]
        if (
            not screen_name.startswith("screen-")
            or not screen_name.endswith(".png")
            or "/" in screen_name
        ):
            raise ValueError("Invalid screen reference")
        image = read_regular(directory / screen_name, MAX_SCREEN_BYTES)
        state = read_regular(directory / "browser-state.json", 2_000_000)
        valid = (
            result["job_id"] == request["artifact_id"]
            and result["scope"] == self.scope
            and result["browser_close_confirmed"] is True
            and hashlib.sha256(image).hexdigest() == observation["sha256"]
            and hashlib.sha256(state).hexdigest() == result["state_sha256"]
        )
        return ComputerUseReceipt(
            verified=valid,
            reason="observed_page_readback" if valid else "content_mismatch",
            artifact=request["artifact_id"] + ".json",
            bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            executor=self.identity,
            scope=self.scope,
            outcome=result["outcome"],
            readback=result,
        ).model_dump()

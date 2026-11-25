"""Native computer preparation executor on the existing approval/job lifecycle."""

import hashlib
import json
import os
import queue
import struct

from .application_runtime import read_regular
from .browser_policy import digest
from .computer_use_files import refresh_file, write_file as exclusive_write
from .browser_supervisor import BrowserSupervisor
from .calendar import iso
from .computer import ExecutionRejected
from .computer_use_models import (
    COMPUTER_DEMOS,
    ComputerUseInput,
    ComputerUseReceipt,
    MAX_SCREEN_BYTES,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    classify_owner_wall,
    wall_from_reason,
)
from .computer_use_protocol import OpenAIComputerProtocol
from .provider_policy import OPENAI_BROWSER_MODELS
from .computer_use_network import local_browser_proxy
from .store import DomainError, encode


class OwnerWallPause(Exception):
    """The same job stopped at a wall only the owner can pass. Not a result."""

    def __init__(self, record):
        self.record = record


class PageLost(Exception):
    """The parked page can no longer be read. Do not open another browser."""


class OwnerHoldEnded(Exception):
    """The live page closed. The job must not be queued again."""

    def __init__(self, state, code, cleanup=False):
        self.state, self.code, self.cleanup = state, code, cleanup


class ComputerSupervisor(BrowserSupervisor):
    worker_module = "desk.computer_use_worker"
    stage_names = {"computer_open", "computer_observe", "computer_action"}
    stage_limit = 180
    protocol_limit = 1_000_000

    def __init__(self, executable=None):
        super().__init__(executable)
        self.live_page = None

    @property
    def supports_owner_takeover(self):
        page = self.live_page
        return bool(page is not None and page.alive())


def _safe_observation(observation):
    return {
        key: observation[key]
        for key in ("sequence", "screen", "sha256", "url", "title", "text")
        if isinstance(observation, dict) and key in observation
    }


class LiveOwnerPage:
    """App-mediated control of the one Playwright page already open for this job."""

    def __init__(self, job_id, channel, executor):
        self.job_id, self.channel, self.executor = job_id, channel, executor
        self.commands = queue.Queue()
        self.receipts = {}

    def alive(self):
        return self.channel.alive()

    def peek(self):
        if not self.alive():
            raise PageLost()
        box = queue.Queue(1)
        self.commands.put(("peek", box))
        self._wait(box)

    def owner_input(self, payload, key, principal):
        box = queue.Queue(1)
        self.commands.put(("input", payload, key, principal, box))
        return self._wait(box)

    def hand_back(self, payload, key, principal):
        box = queue.Queue(1)
        self.commands.put(("return", payload, key, principal, box))
        return self._wait(box)

    @staticmethod
    def _wait(box):
        try:
            kind, payload = box.get(timeout=20)
        except queue.Empty as exc:
            raise PageLost() from exc
        if kind == "error":
            raise payload
        return payload

    def serve(self):
        while True:
            if self.executor.supervisor.live_page is not self:
                self._release("unknown", "BROWSER_PAGE_LOST")
            terminal = self._terminal()
            if terminal:
                self._release(*terminal)
            if not self.alive():
                raise OwnerHoldEnded(
                    "unknown", "BROWSER_PAGE_LOST", cleanup=self.channel.cleanup_seen
                )
            try:
                item = self.commands.get(timeout=0.2)
            except queue.Empty:
                continue
            kind = item[0]
            if kind == "peek":
                self._peek(item[1])
            elif kind == "input":
                self._input(*item[1:])
            elif kind == "return":
                if self._hand_back(*item[1:]):
                    return

    def _terminal(self):
        jobs = self.executor.runtime.jobs
        with jobs.store.connection() as conn:
            row = jobs._row(conn, self.job_id)
            if row["cancel_requested"] or row["state"] == "cancelled":
                return "cancelled", "USER_CANCELLED"
            if row["state"] == "expired" or (
                row["deadline"] and row["deadline"] <= iso(jobs.store.clock())
            ):
                return "expired", "JOB_DEADLINE_EXCEEDED"
            if row["state"] not in {"running", "owner_takeover"}:
                return "unknown", "BROWSER_PAGE_LOST"
            if jobs.store.settings(conn)["hide_private"]:
                return "unknown", "PRIVATE_CONTEXT_HIDDEN"
            session_hash = json.loads(row["request"]).get("session_hash")
            if session_hash and not conn.execute(
                "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
                (session_hash, iso(jobs.store.clock())),
            ).fetchone():
                return "unknown", "RUN_SESSION_EXPIRED"
        return None

    def _release(self, state, code):
        if self.alive():
            try:
                self.channel.write({"release": True})
                self.channel.drain(5)
            except (OSError, DomainError):
                pass
        raise OwnerHoldEnded(state, code, cleanup=self.channel.cleanup_seen)

    def _peek(self, box):
        message = self.channel.exchange({"peek": True}, {"peek_result"})
        if message.get("type") != "peek_result":
            self.channel.drain(5)
            box.put(("error", PageLost()))
            raise OwnerHoldEnded("unknown", "BROWSER_PAGE_LOST", cleanup=self.channel.cleanup_seen)
        box.put(("ok", {"closed": False}))

    def _authorize(self, conn, principal):
        jobs = self.executor.runtime.jobs
        jobs.runtime.personal_context.require_owner_transaction(conn, principal)
        jobs._computer_owner(conn, jobs._row(conn, self.job_id), principal, local_takeover=False)

    def _input(self, payload, key, principal, box):
        jobs = self.executor.runtime.jobs
        action = payload.action.model_dump()
        binding = hashlib.sha256(
            encode(
                {
                    "job_id": self.job_id,
                    "version": payload.expected_version,
                    "type": action.get("type"),
                    "x": action.get("x"),
                    "y": action.get("y"),
                    "key": action.get("key"),
                    "text_sha256": hashlib.sha256((action.get("text") or "").encode()).hexdigest(),
                }
            ).encode()
        ).hexdigest()
        try:
            with jobs.store.connection() as conn:
                self._authorize(conn, principal)
                row = jobs._row(conn, self.job_id)
                request = json.loads(row["request"])
                if action["type"] in {"type", "keypress"} and request.get("start_url") not in COMPUTER_DEMOS:
                    # Public-page preparation is read-only. Passwords and payment input
                    # belong in the supported managed-provider authorization flow.
                    raise DomainError("OWNER_PRIVATE_INPUT_UNAVAILABLE", 409)
                if row["state"] != "owner_takeover":
                    raise DomainError("JOB_NOT_IN_TAKEOVER", 409)
                record = json.loads(row["result"]) if row["result"] else {}
                if record.get("phase") != "held":
                    raise DomainError("JOB_NOT_IN_TAKEOVER", 409)
                cached = self.receipts.get(key)
                if cached:
                    if cached["binding"] != binding:
                        raise DomainError("OPERATION_ID_CONFLICT",409)
                    if cached["state"] != "done":
                        box.put(("error",PageLost()))
                        return
                    # Use the current authorized view; a retry never resends input.
                    box.put(("ok", {"applied": True, "job": jobs._view(row,review=True), "operation_id":key}))
                    return
                if row["version"] != payload.expected_version:
                    raise DomainError("VERSION_CONFLICT", 409)
            self.receipts[key] = {"binding": binding, "state": "dispatched"}
            message = self.channel.exchange({"owner_action": action}, {"owner_view"})
            if message.get("type") != "owner_view":
                self.receipts[key]["state"] = "unknown"
                self.channel.drain(5)
                box.put(("error", PageLost()))
                raise OwnerHoldEnded(
                    "unknown", "BROWSER_PAGE_LOST", cleanup=self.channel.cleanup_seen
                )
            safe = _safe_observation(message.get("value") or {})
            directory = self.executor.root / self.job_id
            from .computer_use_files import refresh_file

            refresh_file(directory, "latest.json", encode(safe).encode())
            with jobs.store.connection(write=True) as conn:
                self._authorize(conn, principal)
                row = jobs._row(conn, self.job_id)
                if row["version"] != payload.expected_version:
                    raise DomainError("VERSION_CONFLICT", 409)
                record = json.loads(row["result"]) if row["result"] else {}
                if row["state"] != "owner_takeover" or record.get("phase") != "held":
                    raise DomainError("JOB_NOT_IN_TAKEOVER", 409)
                record["observation"] = safe
                record["takeover_available"] = True
                jobs._state(conn, self.job_id, "owner_takeover", record.get("reason"), record)
                view = jobs._view(jobs._row(conn, self.job_id), review=True)
            public = {"applied": True, "job": view, "operation_id": key}
            self.receipts[key] = {"binding": binding, "state": "done"}
            box.put(("ok", public))
        except DomainError as exc:
            if self.receipts.get(key, {}).get("state") == "dispatched":
                self.receipts[key]["state"] = "unknown"
                box.put(("error", PageLost()))
                self._release("unknown", "BROWSER_PAGE_LOST")
            box.put(("error", exc))

    def _hand_back(self, payload, key, principal, box):
        jobs = self.executor.runtime.jobs
        body = {
            "type": "computer_return",
            "id": self.job_id,
            "expected_version": payload.expected_version,
        }

        def authorize(conn):
            self._authorize(conn, principal)

        try:
            with jobs.store.connection() as conn:
                authorize(conn)
                _, old = jobs.store.operation_receipt(conn, key, body)
                if old is not None:
                    authorize(conn)
                    box.put(("ok", old))
                    return False
                row = jobs._row(conn, self.job_id)
                record = json.loads(row["result"]) if row["result"] else {}
                if row["state"] != "owner_takeover" or record.get("phase") != "held":
                    raise DomainError("JOB_NOT_IN_TAKEOVER", 409)
                if row["version"] != payload.expected_version:
                    raise DomainError("VERSION_CONFLICT", 409)
            message = self.channel.exchange({"snapshot": True}, {"snapshot_result"})
            if message.get("type") != "snapshot_result":
                self.channel.drain(5)
                box.put(("error", PageLost()))
                raise OwnerHoldEnded(
                    "unknown", "BROWSER_PAGE_LOST", cleanup=self.channel.cleanup_seen
                )
            view = message.get("value") or {}
            observation = view.get("observation") or {}
            wall = classify_owner_wall(
                observation.get("text") or "", observation.get("controls") or ()
            )
            paused_url = (record.get("observation") or {}).get("url")
            if paused_url and observation.get("url") != paused_url and wall is None:
                # A different document is not evidence the original wall cleared.
                wall = {"wall": "login", "reason": "login_needs_owner"}
            safe = _safe_observation(observation)

            def apply(conn):
                authorize(conn)
                row = jobs._row(conn, self.job_id)
                record = json.loads(row["result"]) if row["result"] else {}
                if row["version"] != payload.expected_version:
                    raise DomainError("VERSION_CONFLICT", 409)
                if row["state"] != "owner_takeover" or record.get("phase") != "held":
                    raise DomainError("JOB_NOT_IN_TAKEOVER", 409)
                record["observation"] = safe
                record["takeover_available"] = True
                if wall:
                    record["phase"] = "paused"
                    record["verified"] = False
                    jobs._state(
                        conn, self.job_id, "owner_takeover", record.get("reason"), record
                    )
                    resumed = False
                else:
                    record["phase"] = "returning"
                    jobs._state(conn, self.job_id, "running", None, record)
                    resumed = True
                viewed = jobs._view(jobs._row(conn, self.job_id), review=True)
                return {"job": viewed, "held": False, "resumed": resumed, "stayed": not resumed}

            try:
                stored = jobs.store.operation(key, body, apply, authorize=authorize)
            except DomainError:
                self.channel.write({"continue": False})
                raise
            continued = stored.get("resumed") is True and wall is None
            self.channel.write({"continue": continued})
            box.put(("ok", stored))
            return continued
        except DomainError as exc:
            box.put(("error", exc))
            return False


class ComputerUseExecutor:
    identity = "public_browser_computer_v1"

    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.enabled = os.environ.get("DESK_COMPUTER_USE_ENABLED") == "1"
        self.root = (self.store.directory / "computer-use").absolute()
        self.supervisor = ComputerSupervisor()
        self.browser_proxy = local_browser_proxy(os.environ.get("DESK_BROWSER_PROXY_URL", ""))
        self.http1_only = os.environ.get("DESK_BROWSER_HTTP1_ONLY") == "1"
        scope_parts = [
            self.identity,
            self.supervisor.executable,
            str(self.root),
            self.browser_proxy,
        ]
        if self.http1_only:
            scope_parts.append("http1_only")
        self.scope = "public_browser:" + digest(scope_parts)
        self.protocol_factory = OpenAIComputerProtocol
        self.blocker = self.root / "cleanup-required"
        self.active_job = None
        self.launches = 0

    def provider_config(self):
        return self.runtime.text_ai.config

    def status(self):
        config = self.provider_config()
        reason = self.supervisor.readiness()
        blocked = self.blocker.exists() and self.active_job is None
        return {
            "enabled": self.enabled,
            "configured": config.provider == "openai"
            and config.valid()
            and config.model in OPENAI_BROWSER_MODELS
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
        cfg = self.provider_config()
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

    def _park_owner_page(self, value, channel):
        directory = self.root / self.active_job
        wall = wall_from_reason(value.get("reason"))
        if wall is None:
            raise RuntimeError("Computer hold is not an owner wall")
        page = LiveOwnerPage(self.active_job, channel, self)
        self.supervisor.live_page = page
        try:
            record = self._owner_wall(directory, value, wall)
            record["takeover_available"] = True
            self.runtime.jobs.project_hold(self.active_job, record)
            page.serve()
        finally:
            if self.supervisor.live_page is page:
                self.supervisor.live_page = None

    def _execute(self, request, checkpoint):
        self.launches += 1
        directory = self.root / request["artifact_id"]
        same_job = (directory / "owner-wall.json").is_file() and not request["source_job_id"]
        directory.mkdir(parents=True, mode=0o700, exist_ok=same_job)
        # An interrupted parent may not know whether browser children exited.
        # New admission stays blocked until cleanup is actually confirmed.
        exclusive_write(self.root, "cleanup-required", request["artifact_id"].encode())
        if same_job:
            recorded = json.loads(read_regular(directory / "owner-wall.json", 8000))
            saved = read_regular(directory / "browser-state.json", 2_000_000)
            if hashlib.sha256(saved).hexdigest() != recorded.get("state_sha256"):
                self.blocker.unlink(missing_ok=True)
                raise ExecutionRejected("COMPUTER_SOURCE_CHANGED", 409)
        if request["source_job_id"]:
            state = read_regular(
                self.root / request["source_job_id"] / "browser-state.json", 2_000_000
            )
            if hashlib.sha256(state).hexdigest() != request["source_state_sha256"]:
                self.blocker.unlink()
                raise ExecutionRejected("COMPUTER_SOURCE_CHANGED", 409)
            exclusive_write(directory, "source-state.json", state)
        usages, calls = [], 0
        next_sequence = None
        protocol = self.protocol_factory(
            self.provider_config(),
            request["goal"],
            request["allowed_origins"],
            transport=self.runtime.text_ai.transport,
            on_usage=usages.append,
        )
        protocol.spend_budget=self.runtime.openai_spend

        def fence(_stage=None):
            checkpoint()
            self.current(request)

        def observe(value):
            nonlocal calls, next_sequence
            calls += 1
            sequence = value["sequence"]
            wall_open = (directory / "owner-wall.json").is_file()
            if (
                calls > request["max_steps"]
                or not isinstance(sequence, int)
                or value["screen"] != f"screen-{sequence}.png"
                or (next_sequence is None and sequence != 1 and not same_job and not wall_open)
                or (next_sequence is not None and sequence != next_sequence)
            ):
                raise ValueError("Unexpected computer observation")
            next_sequence = sequence + 1
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
            usage_before = len(usages)
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
            finally:
                # A received response still incurred usage when cancellation or
                # action validation stops execution. Never reuse an older receipt.
                usage = usages[-1] if len(usages) > usage_before else {}
                usage = usage if isinstance(usage, dict) else {}
                numeric = {k: v for k, v in usage.items() if type(v) in (int, float)}
                with self.store.connection(write=True) as conn:
                    conn.execute(
                        "UPDATE text_ai_usage SET usage=? WHERE id=?", (encode(numeric), usage_id)
                    )
            return response

        try:
            outcome = self.supervisor.run(
                {
                    "operation": "execute",
                    "intent": {
                        key: request[key] for key in ("start_url", "allowed_origins", "max_steps")
                    },
                    "resume_state": bool(request["source_job_id"]),
                    "resume_same_job": same_job,
                    "interactive_hold": True,
                    "browser_proxy": self.browser_proxy,
                    "http1_only": self.http1_only,
                },
                directory,
                fence,
                timeout=180,
                on_observation=observe,
                on_hold=self._park_owner_page,
            )
        except OwnerHoldEnded as ended:
            if ended.cleanup:
                self.blocker.unlink(missing_ok=True)
            raise
        if outcome.cleanup_confirmed:
            self.blocker.unlink(missing_ok=True)
            if not outcome.value:
                try:
                    navigation = json.loads(read_regular(directory / "navigation.json", 2000))
                except (OSError, ValueError):
                    navigation = None
                if isinstance(navigation, dict) and navigation.get("stage") == "initial_page":
                    # The owned worker writes this before any model observation
                    # or browser action. A closed failed load is a known failure.
                    raise ExecutionRejected("COMPUTER_SITE_UNAVAILABLE", 409)
        if not outcome.cleanup_confirmed or not outcome.value:
            raise RuntimeError("Computer execution/cleanup is uncertain; inspect before retry")
        value = outcome.value
        wall = wall_from_reason(value.get("reason"))
        if value.get("outcome") == "needs_owner" and wall and not outcome.error:
            raise OwnerWallPause(self._owner_wall(directory, value, wall))
        if not outcome.error:
            fence()
        image = read_regular(directory / value["observation"]["screen"], MAX_SCREEN_BYTES)
        if hashlib.sha256(image).hexdigest() != value["observation"]["sha256"]:
            raise ValueError("Final screenshot changed")
        state = read_regular(directory / "browser-state.json", 2_000_000)
        state_sha256 = hashlib.sha256(state).hexdigest()
        evidence_sha256 = self._wall_evidence(directory, state_sha256)
        result = {
            "job_id": request["artifact_id"],
            "scope": self.scope,
            "outcome": value["outcome"],
            "reason": value["reason"],
            "observation": value["observation"],
            "state_sha256": state_sha256,
            "calls": calls,
            "browser_close_confirmed": True,
            "quality": "not_goal_completion",
            "demo_submissions": value["demo_submissions"],
            "demo": value["demo"],
            "browser_version": value["browser_version"],
            "network_boundary": value["network_boundary"],
        }
        if evidence_sha256:
            result["evidence_sha256"] = evidence_sha256
        exclusive_write(directory, "receipt.json", encode(result).encode())
        if outcome.error:
            raise ExecutionRejected(outcome.error, 409)

    def _owner_wall(self, directory, value, wall):
        observation = value.get("observation") or {}
        screen = observation.get("screen")
        if (
            not isinstance(screen, str)
            or not screen.startswith("screen-")
            or not screen.endswith(".png")
            or "/" in screen
        ):
            raise ValueError("Invalid screen reference")
        image = read_regular(directory / screen, MAX_SCREEN_BYTES)
        if hashlib.sha256(image).hexdigest() != observation.get("sha256"):
            raise ValueError("Final screenshot changed")
        state = read_regular(directory / "browser-state.json", 2_000_000)
        state_sha256 = hashlib.sha256(state).hexdigest()
        safe = {
            key: observation[key]
            for key in ("sequence", "screen", "sha256", "url", "title", "text")
            if key in observation
        }
        record = {
            "paused": True,
            "takeover_available": bool(getattr(self.supervisor, "supports_owner_takeover", False)),
            "sample_input": value.get("demo") is True,
            "verified": False,
            "wall": wall["wall"],
            "reason": wall["reason"],
            "needed": wall["needed"],
            "phase": "paused",
            "state_sha256": state_sha256,
            "observation": safe,
            "quality": "not_goal_completion",
            "demo_submissions": value.get("demo_submissions"),
        }
        refresh_file(directory, "latest.json", encode(safe).encode())
        refresh_file(
            directory,
            "owner-wall.json",
            encode(
                {"wall": wall["wall"], "reason": wall["reason"], "state_sha256": state_sha256}
            ).encode(),
        )
        return record

    def _wall_evidence(self, directory, state_sha256):
        """A resumed job is not successful until the driver recorded a cleared wall."""
        if not (directory / "owner-wall.json").is_file():
            return None
        try:
            raw = read_regular(directory / "wall-evidence.json", 8000)
            evidence = json.loads(raw)
        except (OSError, ValueError):
            raise RuntimeError(
                "Computer execution/cleanup is uncertain; inspect before retry"
            ) from None
        observed = evidence.get("observed_text")
        if (
            evidence.get("cleared") is not True
            or evidence.get("state_sha256") != state_sha256
            or not isinstance(observed, str)
            or not observed.strip()
            or not isinstance(evidence.get("url"), str)
            or not evidence["url"]
            or not isinstance(evidence.get("screen_sha256"), str)
        ):
            raise RuntimeError("Computer execution/cleanup is uncertain; inspect before retry")
        return hashlib.sha256(raw).hexdigest()

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
        if valid and (directory / "owner-wall.json").is_file():
            try:
                evidence_raw = read_regular(directory / "wall-evidence.json", 8000)
                evidence = json.loads(evidence_raw)
            except (OSError, ValueError):
                valid = False
                evidence = {}
                evidence_raw = b""
            observed = evidence.get("observed_text")
            valid = valid and (
                evidence.get("cleared") is True
                and evidence.get("state_sha256") == result["state_sha256"]
                and isinstance(observed, str)
                and bool(observed.strip())
                and evidence.get("url") == observation.get("url")
                and evidence.get("screen_sha256") == observation.get("sha256")
                and hashlib.sha256(evidence_raw).hexdigest() == result.get("evidence_sha256")
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

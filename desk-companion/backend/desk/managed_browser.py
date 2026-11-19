"""Primary managed browser execution on the existing durable job lifecycle."""

import asyncio
import hashlib
import json
import os
from dataclasses import replace

from .application_runtime import read_regular
from .browser_policy import digest
from .calendar import iso
from .commerce_quotes import read_quote
from .computer import ExecutionRejected
from .computer_use import ComputerUseExecutor
from .computer_use_files import write_file
from .computer_use_models import ComputerUseReceipt
from .managed_browser_client import ManagedBrowserClient
from .provider_policy import OPENAI_BROWSER_MODELS
from .openai_spend import HOSTED_BROWSER, token_estimate
from .managed_browser_auth import ManagedBrowserAuth
from .store import DomainError, encode


class ManagedBrowserExecutor(ComputerUseExecutor):
    """Reuse owner/privacy/provider admission, not the local browser implementation."""

    identity = "managed_public_browser_v1"
    supervisor = None  # Official registered forms, not a local browser process.

    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        self.enabled = os.environ.get("DESK_MANAGED_BROWSER_ENABLED", "1") == "1"
        self.model_override = os.environ.get("DESK_MANAGED_BROWSER_MODEL")
        self.root = (self.store.directory / "managed-browser").absolute()
        self.scope = "public_browser:" + digest(
            [
                self.identity,
                str(self.root),
                "small",
                ManagedBrowserClient.setup_seconds,
                ManagedBrowserClient.active_seconds,
            ]
        )
        self.blocker = self.root / "cleanup-required"
        self.active_job = None
        self.client_factory = ManagedBrowserClient
        self.auth = ManagedBrowserAuth()

    def provider_config(self):
        config = self.runtime.text_ai.config
        return config if self.model_override is None else replace(config, model=self.model_override)

    def status(self):
        config = self.provider_config()
        blocked = self.blocker.exists() and self.active_job is None
        return {
            "enabled": self.enabled,
            "model": config.model,
            "configured": config.provider == "openai"
            and config.valid()
            and config.model in OPENAI_BROWSER_MODELS
            and not blocked,
            "reason": "COMPUTER_CLEANUP_REQUIRED" if blocked else None,
            "busy": self.active_job is not None,
            "scope": "public_research_only",
            "real_transactions": False,
            "resumable": False,
            "max_active_seconds": ManagedBrowserClient.active_seconds,
            "max_setup_seconds": ManagedBrowserClient.setup_seconds,
            "owner_authentication": True,
            "max_auth_seconds": 90,
        }

    def prepare_request(self, payload, job_id, principal):
        if payload.engine != "managed" or payload.source_job_id:
            raise DomainError("COMPUTER_SOURCE_CHANGED", 409)
        return super().prepare_request(payload, job_id, principal)

    def _execute(self, request, checkpoint):
        directory = self.root / request["artifact_id"]
        directory.mkdir(parents=True, mode=0o700, exist_ok=False)

        def fence():
            checkpoint()
            self.current(request)

        fence()
        # Keep the existing daily attempt limit. One managed session may contain
        # many internal model calls, so this is not a dollar or token ceiling.
        try:
            usage_id = self.runtime.text_ai._reserve_usage(
                "computer_use",
                reservation=(
                    "hosted_browser",
                    HOSTED_BROWSER,
                    ManagedBrowserClient.setup_seconds
                    + ManagedBrowserClient.active_seconds
                    + ManagedBrowserClient.auth_seconds
                    + ManagedBrowserClient.cleanup_seconds
                    + 15,
                ),
            )
        except DomainError as error:
            # No request or cleanup marker exists before admission.
            raise ExecutionRejected(error.code, error.status) from error
        write_file(self.root, "cleanup-required", request["artifact_id"].encode())

        def created(session_id):
            write_file(
                directory,
                "managed-session.json",
                encode(
                    {
                        "session_id": session_id,
                        "job_id": request["artifact_id"],
                    }
                ).encode(),
            )

        client = self.client_factory(
            self.provider_config(),
            transport=self.runtime.text_ai.transport,
        )

        def budget_observation(usage):
            try:
                self.runtime.openai_spend.active(usage_id)
                self.runtime.openai_spend.usage([usage_id], token_estimate(usage))
            except DomainError as error:
                raise ExecutionRejected(error.code, error.status) from error

        client.budget_observation = budget_observation

        def authentication(action):
            job_id = request["artifact_id"]
            if action is None:
                self.auth.clear(job_id)
                self.runtime.jobs.managed_auth_state(job_id, None)
                return None
            fence()
            try:
                self.auth.present(job_id, action, request["allowed_origins"])
            except DomainError as error:
                raise ExecutionRejected(error.code, error.status) from None
            answer = self.auth.take(job_id, action)
            form = self.auth.form(job_id)
            self.runtime.jobs.managed_auth_state(
                job_id, {k: form[k] for k in ("nonce", "origin", "phase")}
            )
            return answer

        spec = request.get("quote_request")
        result = asyncio.run(client.run(request, fence, created, authentication=None if spec else authentication))
        if spec:
            result["observed_at"] = iso(self.store.clock())
        # Save bounded evidence even when cancellation/provider failure interrupts
        # work. A missing usage receipt remains unknown, never a zero-cost claim.
        write_file(directory, "managed-result.json", encode(result).encode())
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE text_ai_usage SET usage=? WHERE id=?",
                (
                    encode(result.get("usage") or {}),
                    usage_id,
                ),
            )
        if result["session_deleted"] and result["deletion_readback"]:
            # Token usage does not itemize the environment. Keep the full hosted reservation.
            self.runtime.openai_spend.usage(
                [usage_id], token_estimate(result.get("usage")), final=True, retain=True
            )
        if not result["session_deleted"] or not result["deletion_readback"]:
            raise RuntimeError("Managed cleanup is uncertain; inspect before retry")
        self.blocker.unlink()
        if result["stop_code"]:
            raise ExecutionRejected(result["stop_code"], 409)
        fence()
        result_raw = read_regular(directory / "managed-result.json", 128000)
        receipt = {
            "job_id": request["artifact_id"],
            "scope": self.scope,
            "outcome": "review_ready",
            "quality": "not_goal_completion",
            "report": result["report"],
            "reason": "managed_report_readback",
            "evidence_sha256": hashlib.sha256(result_raw).hexdigest(),
            "session_deletion_confirmed": True,
            "physical_resource_cleanup": "provider_managed",
            "usage": result["usage"],
            "cost_receipt": "usage_available" if result["usage"] else "unknown",
            "resumable": False,
            "activity_count": result["activity_count"],
            "data_scope": "owner_authorized_account"
            if result["account_access_authorized"]
            else "public_pages",
        }
        if spec:
            try:
                receipt["quote"] = read_quote(request, result["report"], result["observed_at"])
            except ValueError as exc:
                raise ExecutionRejected("COMPUTER_QUOTE_UNVERIFIED", 409) from exc
            receipt["report"] = receipt["quote"]["note"]
        write_file(directory, "receipt.json", encode(receipt).encode())

    def verify(self, request):
        directory = self.root / request["artifact_id"]
        raw = read_regular(directory / "receipt.json", 128000)
        result = json.loads(raw)
        evidence_raw = read_regular(directory / "managed-result.json", 128000)
        evidence = json.loads(evidence_raw)
        quote = None
        if request.get("quote_request"):
            quote = read_quote(request, evidence["report"], evidence["observed_at"])
        valid = (
            result["job_id"] == request["artifact_id"]
            and result["scope"] == self.scope
            and result["evidence_sha256"] == hashlib.sha256(evidence_raw).hexdigest()
            and result.get("quote") == quote
            and result["report"] == (quote["note"] if quote else evidence["report"])
            and bool(result["report"].strip())
            and evidence["session_deleted"] is True
            and evidence["deletion_readback"] is True
            and evidence["turn_completed"] is True
            and evidence["stop_code"] is None
            and result.get("data_scope", "public_pages")
            == (
                "owner_authorized_account"
                if evidence.get("account_access_authorized")
                else "public_pages"
            )
        )
        return ComputerUseReceipt(
            verified=valid,
            reason="managed_report_readback" if valid else "content_mismatch",
            artifact=request["artifact_id"] + ".json",
            bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            executor=self.identity,
            scope=self.scope,
            outcome="review_ready",
            readback=result,
        ).model_dump()

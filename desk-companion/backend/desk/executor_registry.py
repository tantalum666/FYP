"""Typed, code-owned action registry. Model data cannot register an executor."""

import hashlib

from .application_executor import ApplicationReceipt, ApplicationRecordsExecutor
from .computer import ExecutionRejected, VerificationReceipt

NOTE_ACTIONS = {"save_note", "verify_note"}
RECORD_ACTIONS = {"create_record", "verify_record"}


class ExecutorRegistry:
    def __init__(self, notes, application=None):
        # Callable preserves the established JobService.executor test/integration seam.
        self.notes = notes
        self.application = application

    def resolve(self, action):
        if action in NOTE_ACTIONS:
            return self.notes()
        if action in RECORD_ACTIONS and self.application is not None:
            return self.application
        raise ExecutionRejected("COMPUTER_ACTION_UNAVAILABLE", 409)

    def actions(self):
        return ["save_note", "verify_note"] + (
            ["create_record", "verify_record"] if self.application is not None else []
        )

    def bind(self, request):
        executor = self.resolve(request["action"])
        request.update(executor=executor.identity, scope=executor.scope)
        if request["action"] in RECORD_ACTIONS:
            request.update(executor.metadata())
            request.update(
                record_title=request["title"],
                content_sha256=hashlib.sha256(request["content"].encode()).hexdigest(),
            )
        return executor

    def validate(self, request):
        executor = self.resolve(request["action"])
        if request["executor"] != executor.identity or request["scope"] != executor.scope:
            raise ExecutionRejected("COMPUTER_SCOPE_CHANGED", 409)
        if request["action"] in RECORD_ACTIONS:
            executor.validate(request)
        return executor

    def verify(self, request):
        executor = self.validate(request)
        application = request["action"] in RECORD_ACTIONS
        schema = ApplicationReceipt if application else VerificationReceipt
        receipt = schema.model_validate(executor.verify(request)).model_dump(exclude_none=True)
        if receipt["verified"]:
            body = request["content"].encode("utf-8")
            expected = {
                "artifact": request["artifact_id"] + (".json" if application else ".txt"),
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
                "executor": request["executor"],
                "scope": request["scope"],
            }
            if application:
                expected.update(
                    {
                        key: request[key]
                        for key in (
                            "target_origin",
                            "app_instance_id",
                            "adapter_version",
                            "schema_version",
                        )
                    }
                )
                expected["title_sha256"] = hashlib.sha256(
                    request["record_title"].encode()
                ).hexdigest()
                expected["record_intent_hash"] = ApplicationRecordsExecutor.record_intent_hash(
                    request
                )
            if any(receipt.get(key) != value for key, value in expected.items()):
                raise ValueError("Receipt does not match the authorized intent")
        return receipt

"""Transient owner-only form exchange for an existing official browser job.

Values never enter the task, operations table, model messages or disk. The
worker consumes a submission once; an HTTP retry only returns its receipt.
The broker is not a worker or a second job queue.
"""

import hashlib
import hmac
import threading
from typing import Literal
from uuid import uuid4

from pydantic import Field, SecretStr

from .schemas import StrictModel
from .store import DomainError, encode


class AuthValue(StrictModel):
    field_id: str = Field(min_length=1, max_length=256)
    value: SecretStr = Field(max_length=4096)


class BrowserAuthInput(StrictModel):
    nonce: str = Field(pattern=r"^[a-f0-9]{32}$")
    expected_version: int = Field(ge=1, strict=True)
    action: Literal["submit", "cancel"]
    fields: list[AuthValue] = Field(default_factory=list, max_length=6)
    selected_option: str | None = Field(default=None, min_length=1, max_length=256)
    allow_account_access: bool = Field(default=False, strict=True)


def registered_form(action, allowed_origins):
    """Validate the provider's registered form, not arbitrary model HTML."""
    req = action.get("request", {})
    origin = req.get("credential_origin")
    fields, options = req.get("fields"), req.get("options")
    if (
        req.get("type") != "browser_authentication"
        or origin not in allowed_origins
        or not isinstance(fields, list)
        or not isinstance(options, list)
        or len(fields) > 6
        or len(options) > 6
        or not (fields or options)
    ):
        raise DomainError("COMPUTER_MANAGED_OWNER_REQUIRED", 409)

    def label(value):
        if not isinstance(value, str) or not 0 < len(value) <= 256:
            raise DomainError("COMPUTER_AUTH_UNSUPPORTED", 409)
        return value

    clean_fields = []
    for field in fields:
        if (
            not isinstance(field, dict)
            or field.get("type") not in {"email", "password", "text", "tel", "number"}
            or type(field.get("required")) is not bool
        ):
            raise DomainError("COMPUTER_AUTH_UNSUPPORTED", 409)
        clean_fields.append(
            {
                "id": label(field.get("id")),
                "label": label(field.get("label")),
                "required": field["required"],
                "type": field["type"],
            }
        )
    ids = {field["id"] for field in clean_fields}
    if len(ids) != len(clean_fields):
        raise DomainError("COMPUTER_AUTH_UNSUPPORTED", 409)
    clean_options = []
    for option in options:
        if not isinstance(option, dict):
            raise DomainError("COMPUTER_AUTH_UNSUPPORTED", 409)
        selected = option.get("field_ids")
        if (
            not isinstance(selected, list)
            or any(not isinstance(i, str) or i not in ids for i in selected)
            or len(set(selected)) != len(selected)
        ):
            raise DomainError("COMPUTER_AUTH_UNSUPPORTED", 409)
        clean_options.append(
            {
                "id": label(option.get("id")),
                "label": label(option.get("label")),
                "field_ids": selected,
            }
        )
    if len({option["id"] for option in clean_options}) != len(clean_options):
        raise DomainError("COMPUTER_AUTH_UNSUPPORTED", 409)
    return {"origin": origin, "fields": clean_fields, "options": clean_options}


class ManagedBrowserAuth:
    def __init__(self):
        self.lock = threading.RLock()
        self.pending = {}

    def present(self, job_id, action, allowed_origins):
        form = registered_form(action, allowed_origins)
        fingerprint = hashlib.sha256(encode(action).encode()).hexdigest()
        with self.lock:
            current = self.pending.get(job_id)
            if current and current["fingerprint"] == fingerprint:
                return current["nonce"]
            nonce = uuid4().hex
            self.pending[job_id] = {
                **form,
                "nonce": nonce,
                "fingerprint": fingerprint,
                "phase": "waiting",
                "response": None,
                "digest": None,
                "salt": uuid4().bytes,
            }
            return nonce

    def form(self, job_id):
        with self.lock:
            current = self.pending.get(job_id)
            if not current:
                return None
            return {k: current[k] for k in ("nonce", "origin", "fields", "options", "phase")}

    def submit(self, job_id, payload):
        with self.lock:
            current = self.pending.get(job_id)
            if not current or current["nonce"] != payload.nonce:
                raise DomainError("COMPUTER_AUTH_CHANGED", 409)
            response = {"type": "browser_authentication", "action": payload.action}
            if payload.action == "cancel":
                if payload.fields or payload.selected_option or payload.allow_account_access:
                    raise DomainError("VALIDATION_FAILED", 422)
            else:
                if not payload.allow_account_access:
                    raise DomainError("COMPUTER_ACCOUNT_CONSENT_REQUIRED", 409)
                options = current["options"]
                selected = next((o for o in options if o["id"] == payload.selected_option), None)
                if (options and selected is None) or (not options and payload.selected_option):
                    raise DomainError("VALIDATION_FAILED", 422)
                allowed = (
                    set(selected["field_ids"])
                    if selected
                    else {field["id"] for field in current["fields"]}
                )
                values = {
                    field.field_id: field.value.get_secret_value() for field in payload.fields
                }
                if len(values) != len(payload.fields) or not set(values) <= allowed:
                    raise DomainError("VALIDATION_FAILED", 422)
                required = {
                    f["id"] for f in current["fields"] if f["required"] and f["id"] in allowed
                }
                if any(not values.get(i, "").strip() for i in required) or (allowed and not values):
                    raise DomainError("VALIDATION_FAILED", 422)
                response["fields"] = [{"field_id": i, "value": v} for i, v in values.items()]
                if selected:
                    response["selected_option"] = selected["id"]
            fingerprint = hmac.new(current["salt"], encode(response).encode(), "sha256").hexdigest()
            if current["digest"]:
                if not hmac.compare_digest(current["digest"], fingerprint):
                    raise DomainError("COMPUTER_AUTH_ALREADY_SUBMITTED", 409)
            else:
                current.update(response=response, digest=fingerprint, phase="received")
            return {"received": True, "phase": current["phase"]}

    def take(self, job_id, action):
        with self.lock:
            current = self.pending.get(job_id)
            if (
                not current
                or current["fingerprint"] != hashlib.sha256(encode(action).encode()).hexdigest()
            ):
                return None
            response, current["response"] = current["response"], None
            if response:
                current["phase"] = "submitted"
            return response

    def clear(self, job_id):
        with self.lock:
            self.pending.pop(job_id, None)

"""Owner-connected outbound mail with existing review and durable no-resend state."""

import threading
import json
from uuid import uuid4
from fastapi import APIRouter, Depends
from .calendar import iso
from .gmail_api import GmailAPI, MailTransportError
from .google_oauth import GoogleOAuth
from .microsoft_apps import OutlookSender
from .outbound_mail_models import MailDraft
from .store import DomainError


class OutboundMail:
    def __init__(self, runtime, transport=None):
        self.runtime, self.store = runtime, runtime.store
        self.transport = transport or GmailAPI()
        self.auth = GoogleOAuth(runtime, resource="gmail")
        self.outlook = OutlookSender()
        self.lock = threading.RLock()
        with self.store.connection(write=True) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS outgoing_mail_attempts(proposal_id TEXT PRIMARY KEY, message_id TEXT NOT NULL, state TEXT NOT NULL, attempts INTEGER NOT NULL, updated_at TEXT NOT NULL, error TEXT, receipt TEXT)"
            )
            if "receipt" not in {
                r[1] for r in conn.execute("PRAGMA table_info(outgoing_mail_attempts)")
            }:
                conn.execute("ALTER TABLE outgoing_mail_attempts ADD COLUMN receipt TEXT")
            conn.execute(
                "UPDATE outgoing_mail_attempts SET state='unknown',error='EMAIL_SEND_UNKNOWN' WHERE state='sending'"
            )

    def auth_for(self, provider):
        return self.auth if provider == "gmail" else self.runtime.microsoft.auth["microsoft365"]

    def snapshot(self, provider="auto"):
        accounts = [
            {**self.auth_for(name).account(), "provider": name} for name in ("gmail", "outlook")
        ]
        if provider != "auto":
            return next(item for item in accounts if item["provider"] == provider)
        available = [item for item in accounts if item["connected"]]
        return {
            **(available[0] if len(available) == 1 else self.auth.account()),
            "connected": bool(available),
            "accounts": accounts,
            "sender_choice_required": len(available) > 1,
            "send_requires_review": True,
        }

    def disconnect(self, expected_version, provider="gmail"):
        auth = self.auth_for(provider)
        with self.lock, auth.lock:
            if self.snapshot(provider)["version"] != expected_version:
                raise DomainError("VERSION_CONFLICT", 409)
            result = auth.disconnect()
            with self.store.connection(write=True) as conn:
                conn.execute(
                    "UPDATE assistant_proposals SET state='cancelled' WHERE kind='email_send' AND state='pending' AND COALESCE(json_extract(data,'$.provider'),'gmail')=?",
                    (provider,),
                )
                self.store.bump(conn)
            return {**self.snapshot(provider), **result}

    def draft(self, request, key):
        state = self.snapshot(request.provider)
        if not state["connected"]:
            return {
                "connected": False,
                "sent": False,
                "next_step": "Connect Gmail or Microsoft 365 in More > Connections > Apps first. No message can be sent until the owner authorizes an account.",
            }
        if state.get("sender_choice_required"):
            return {
                "sent": False,
                "sender_choice_required": True,
                "accounts": state["accounts"],
                "next_step": "Ask which connected email account to send from.",
            }
        provider = state.get("provider", "gmail")
        mail = request.model_dump()
        mail["provider"] = provider
        if mail["to"] == "me":
            mail["to"] = state["email"]
        return {
            **self.runtime.assistant.propose(
                "email_send",
                {**mail, "from": state["email"], "account_version": state["version"]},
                key,
            ),
            "sent": False,
        }

    def send(self, proposal_id, payload, operation_key):
        # Called only by AssistantService.decide after owner/current draft checks.
        # No network I/O happens inside Store.operation's SQLite transaction.
        provider = payload.get("provider", "gmail")
        if provider not in {"gmail", "outlook"}:
            raise DomainError("EMAIL_DRAFT_INVALID", 422)
        auth = self.auth_for(provider)
        with self.lock, auth.lock:
            with self.store.connection() as conn:
                attempt = conn.execute(
                    "SELECT * FROM outgoing_mail_attempts WHERE proposal_id=?", (proposal_id,)
                ).fetchone()
            account = self.snapshot(provider)
            if attempt and attempt["state"] in {"unknown", "sending"}:
                raise DomainError("EMAIL_SEND_UNKNOWN", 409)
            if attempt and attempt["state"] == "accepted":
                return self._receipt(proposal_id, attempt["message_id"], operation_key)
            if not account["connected"]:
                raise DomainError("EMAIL_NOT_CONNECTED", 409)
            if account["version"] != payload.get("account_version") or account[
                "email"
            ] != payload.get("from"):
                raise DomainError("EMAIL_CONNECTION_CHANGED", 409)
            draft = MailDraft.model_validate(
                {k: payload[k] for k in ("to", "subject", "body")}
            ).model_dump()
            if draft["to"] == "me":
                raise DomainError("EMAIL_DRAFT_INVALID", 422)
            # Refresh before reserving a possible send; auth failure cannot have sent mail.
            access_token = auth.access_token()
            message_id = (
                attempt["message_id"] if attempt else f"<fyp-{uuid4().hex}@desk-companion.local>"
            )
            with self.store.connection(write=True) as conn:
                conn.execute(
                    "INSERT INTO outgoing_mail_attempts(proposal_id,message_id,state,attempts,updated_at,error) VALUES(?,?,'sending',1,?,NULL) ON CONFLICT(proposal_id) DO UPDATE SET state='sending',attempts=attempts+1,updated_at=excluded.updated_at,error=NULL",
                    (proposal_id, message_id, iso(self.store.clock())),
                )
            try:
                result = (self.transport if provider == "gmail" else self.outlook).send(
                    account["email"],
                    access_token,
                    draft,
                    message_id,
                )
                if result.get("accepted") is not True or (
                    provider == "gmail" and not isinstance(result.get("provider_id"), str)
                ):
                    raise MailTransportError("EMAIL_SEND_UNKNOWN", unknown=True)
            except MailTransportError as error:
                state = "unknown" if error.unknown else "failed"
                self._outcome(proposal_id, state, error.code)
                raise DomainError(error.code, 409 if error.unknown else 422) from None
            except Exception:
                self._outcome(proposal_id, "unknown", "EMAIL_SEND_UNKNOWN")
                raise DomainError("EMAIL_SEND_UNKNOWN", 409) from None
            self._outcome(proposal_id, "accepted", None, {**result, "provider": provider})
            return self._receipt(proposal_id, message_id, operation_key)

    def _outcome(self, proposal_id, state, error, receipt=None):
        with self.store.connection(write=True) as conn:
            conn.execute(
                "UPDATE outgoing_mail_attempts SET state=?,error=?,updated_at=?,receipt=? WHERE proposal_id=?",
                (
                    state,
                    error,
                    iso(self.store.clock()),
                    json.dumps(receipt) if receipt else None,
                    proposal_id,
                ),
            )
            self.store.record(
                conn, "email_" + state, details={"proposal_id": proposal_id, "error": error}
            )
            self.store.bump(conn)

    def _receipt(self, proposal_id, message_id, key):
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT receipt FROM outgoing_mail_attempts WHERE proposal_id=?", (proposal_id,)
            ).fetchone()
        receipt = json.loads(row[0]) if row and row[0] else {}
        return self.store.operation(
            key,
            {"type": "email_send", "proposal_id": proposal_id},
            lambda conn: {
                "sent": True,
                "state": "accepted_by_provider",
                "provider": receipt.get("provider", "gmail"),
                "receipt_kind": receipt.get("receipt_kind", "message_id"),
                "message_id": message_id,
                "provider_receipt_id": receipt.get("provider_id"),
                "delivery_confirmed": False,
            },
        )

    def recover_accepted(self, proposal_id, key):
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT state,message_id FROM outgoing_mail_attempts WHERE proposal_id=?",
                (proposal_id,),
            ).fetchone()
        return (
            self._receipt(proposal_id, row["message_id"], key)
            if row and row["state"] == "accepted"
            else None
        )

    def require_cancellable(self, proposal_id):
        with self.store.connection() as conn:
            row = conn.execute(
                "SELECT state FROM outgoing_mail_attempts WHERE proposal_id=?", (proposal_id,)
            ).fetchone()
        if row and row["state"] in {"sending", "unknown"}:
            raise DomainError("EMAIL_SEND_UNKNOWN", 409)


def outbound_mail_routes(runtime, owner, operation_id):
    router = APIRouter(prefix="/api/email", dependencies=[Depends(owner)])

    @router.post("/drafts")
    def draft(request: MailDraft, key=Depends(operation_id)):
        return runtime.outbound_mail.draft(request, key)

    return router

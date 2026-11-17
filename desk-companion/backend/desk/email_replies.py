"""Bind a reviewed reply to the exact existing provider message and recipient."""

import hashlib
import re

from .mail_threads import MailThreadReader
from .outbound_mail_models import MailDraft, address
from .store import DomainError, encode


def binding(message, account):
    if message["excluded"] or not message["reply_address"]:
        raise DomainError("EMAIL_REPLY_UNAVAILABLE", 409)
    try:
        recipient = address(message["reply_address"])
    except ValueError:
        raise DomainError("EMAIL_REPLY_UNAVAILABLE", 409) from None
    # Keep the subject identical for Gmail's documented thread matching rule.
    subject = message["subject"]
    if not subject:
        raise DomainError("EMAIL_REPLY_UNAVAILABLE", 409)
    values = {
        "message_id": message["id"],
        "thread_id": message["thread_id"],
        "rfc_message_id": message["rfc_message_id"],
        "to": recipient,
        "subject": subject,
        "account_version": account["version"],
    }
    return values, hashlib.sha256(encode(values).encode()).hexdigest()


def read_reply_source(runtime, provider, message_id, account):
    privacy = runtime.microsoft._visible()
    reader = MailThreadReader(runtime)

    def current():
        if runtime.microsoft._visible() != privacy:
            raise DomainError("PROVIDER_CONTEXT_CHANGED", 409)
        latest = reader.auth(provider).account()
        if (
            not latest["connected"]
            or latest["version"] != account["version"]
            or latest["email"] != account["email"]
        ):
            raise DomainError("EMAIL_CONNECTION_CHANGED", 409)

    current()
    message = reader.message(provider, message_id, account["email"], current, for_reply=True)
    if provider == "gmail" and not re.fullmatch(
        r"<[^<>\s@]+@[^<>\s@]+>", message["rfc_message_id"]
    ):
        raise DomainError("EMAIL_REPLY_UNAVAILABLE", 409)
    values, digest = binding(message, account)
    current()
    return {**values, "source_sha256": digest}


def prepare_reply(runtime, request, key):
    account = runtime.outbound_mail.snapshot(request.provider)
    if not account["connected"]:
        raise DomainError("EMAIL_NOT_CONNECTED", 409)
    reply = read_reply_source(runtime, request.provider, request.message_id, account)
    with runtime.store.connection() as conn:
        unknown = conn.execute(
            "SELECT 1 FROM outgoing_mail_attempts a JOIN assistant_proposals p ON p.id=a.proposal_id "
            "WHERE a.state IN ('sending','unknown') AND p.kind='email_send' "
            "AND json_extract(p.data,'$.provider')=? AND json_extract(p.data,'$.from')=? "
            "AND json_extract(p.data,'$.reply.message_id')=? LIMIT 1",
            (request.provider, account["email"], reply["message_id"]),
        ).fetchone()
    if unknown:
        raise DomainError("EMAIL_SEND_UNKNOWN", 409)
    return runtime.outbound_mail.draft(
        MailDraft(
            provider=request.provider, to=reply["to"], subject=reply["subject"], body=request.body
        ),
        key,
        reply=reply,
    )


def verify_reply(runtime, provider, reply, account, draft):
    if not isinstance(reply, dict) or not isinstance(reply.get("message_id"), str):
        raise DomainError("EMAIL_DRAFT_INVALID", 422)
    fresh = read_reply_source(runtime, provider, reply["message_id"], account)
    if fresh != reply or draft["to"] != fresh["to"] or draft["subject"] != fresh["subject"]:
        raise DomainError("EMAIL_REPLY_CHANGED", 409)
    return fresh

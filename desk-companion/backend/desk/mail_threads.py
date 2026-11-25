"""Bounded metadata reads from a selected Gmail/Outlook thread, never mail actions."""

from datetime import datetime, timezone
from email.utils import parseaddr, getaddresses
from email.header import decode_header, make_header
from email.errors import HeaderParseError
import re
from urllib.parse import quote

import httpx

from .store import DomainError

MAX_MESSAGES = 50
ID = re.compile(r"[A-Za-z0-9_+=/.-]{1,512}")
HEADERS = ["From", "Subject", "Date"]
GRAPH_FIELDS = "id,conversationId,subject,from,receivedDateTime,sentDateTime,isDraft"


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise DomainError("MAIL_THREAD_INVALID", 422)
    return value


def text(value, limit):
    if not isinstance(value, str):
        raise DomainError("MAIL_THREAD_INVALID", 502)
    return " ".join(value.split())[:limit]


def mail_header(value, *, decode=False):
    if not isinstance(value, str) or len(value) > 4096:
        raise DomainError("MAIL_THREAD_INVALID", 502)
    value = re.sub(r"\r?\n[ \t]+", " ", value).strip()
    if decode:
        try:
            value = str(make_header(decode_header(value)))
        except (HeaderParseError, LookupError, UnicodeError, ValueError):
            raise DomainError("MAIL_THREAD_INVALID", 502) from None
    if any(ord(c) < 32 and c != "\t" or ord(c) == 127 for c in value):
        raise DomainError("MAIL_THREAD_INVALID", 502)
    return value.replace("\t", " ")


class MailThreadReader:
    def __init__(self, runtime):
        self.runtime = runtime

    def auth(self, provider):
        if provider not in {"gmail", "outlook"}:
            raise DomainError("MAIL_THREAD_INVALID", 422)
        return self.runtime.outbound_mail.auth_for(provider)

    def get(self, provider, path, params, checkpoint):
        auth = self.auth(provider)
        checkpoint()
        token = auth.access_token()
        checkpoint()
        transport = auth.transport if provider == "gmail" else self.runtime.microsoft.transport
        root = (
            "https://gmail.googleapis.com/gmail/v1/users/me"
            if provider == "gmail"
            else "https://graph.microsoft.com/v1.0/me"
        )
        try:
            with httpx.Client(
                timeout=8, transport=transport, trust_env=False, follow_redirects=False
            ) as client:
                response = client.get(
                    root + path,
                    params=params,
                    headers={
                        "Authorization": "Bearer " + token,
                        **({"Prefer": 'IdType="ImmutableId"'} if provider == "outlook" else {}),
                    },
                )
            if response.status_code == 401:
                raise DomainError("APP_RECONNECT_REQUIRED", 409)
            if response.status_code == 403:
                raise DomainError("APP_PERMISSION_REQUIRED", 403)
            if response.status_code == 404:
                raise DomainError("APP_ITEM_UNAVAILABLE", 404)
            if response.status_code == 429:
                raise DomainError("APP_RATE_LIMIT", 429)
            response.raise_for_status()
            if len(response.content) > 192000:
                raise DomainError("MAIL_THREAD_TOO_LARGE", 422)
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError()
        except (httpx.HTTPError, ValueError):
            raise DomainError("APP_CONNECTION_FAILED", 502) from None
        checkpoint()
        return data

    def message(self, provider, message_id, account_email, checkpoint, *, for_reply=False):
        data = self.get(
            provider,
            "/messages/" + quote(identifier(message_id), safe=""),
            {
                "format": "metadata",
                "metadataHeaders": HEADERS
                + (["To", "Reply-To", "Message-ID"] if for_reply else []),
                "fields": "id,threadId,labelIds,internalDate,payload/headers",
            }
            if provider == "gmail"
            else {
                "$select": GRAPH_FIELDS
                + (",replyTo,toRecipients,internetMessageId" if for_reply else "")
            },
            checkpoint,
        )
        return self.normalize(provider, data, account_email, for_reply=for_reply)

    def original_text(self, provider, message_id, account_email, checkpoint):
        """Owner-requested reread. The caller must not store the returned text."""
        if provider == "gmail":
            data = self.get(
                provider,
                "/messages/" + quote(identifier(message_id), safe=""),
                {
                    "format": "full",
                    "fields": "id,threadId,snippet,labelIds,internalDate,payload/headers",
                },
                checkpoint,
            )
            message = self.normalize(provider, data, account_email)
            snippet = data.get("snippet")
            body = text(snippet, 1000) if isinstance(snippet, str) else ""
            message.pop("excluded", None)
            return {**message, "body": body, "body_status": "snippet" if body else "metadata_only"}
        message = self.message(provider, message_id, account_email, checkpoint)
        message.pop("excluded", None)
        return {**message, "body": "", "body_status": "metadata_only"}

    def thread(self, provider, thread_id, account_email, checkpoint):
        ident = identifier(thread_id)
        if provider == "gmail":
            data = self.get(
                provider,
                "/threads/" + quote(ident, safe=""),
                {
                    "format": "metadata",
                    "metadataHeaders": HEADERS,
                    "fields": "id,historyId,messages(id,threadId,labelIds,internalDate,payload/headers)",
                },
                checkpoint,
            )
            if data.get("id") != ident:
                raise DomainError("MAIL_THREAD_INVALID", 502)
            rows = data.get("messages", [])
        else:
            # IDs are validated before entering the fixed OData expression. No
            # provider pagination URL, email URL or model-selected host is used.
            data = self.get(
                provider,
                "/messages",
                {
                    "$filter": "conversationId eq '" + ident + "'",
                    "$select": GRAPH_FIELDS,
                    "$top": MAX_MESSAGES + 1,
                },
                checkpoint,
            )
            if data.get("@odata.nextLink"):
                raise DomainError("MAIL_THREAD_TOO_LARGE", 422)
            rows = data.get("value", [])
        if not isinstance(rows, list) or len(rows) > MAX_MESSAGES:
            raise DomainError("MAIL_THREAD_TOO_LARGE", 422)
        messages = [self.normalize(provider, row, account_email) for row in rows]
        if any(message["thread_id"] != ident for message in messages):
            raise DomainError("MAIL_THREAD_INVALID", 502)
        if len({message["id"] for message in messages}) != len(messages):
            raise DomainError("MAIL_THREAD_INVALID", 502)
        # Drafts (and Gmail trash/spam) are excluded from incoming-reply evidence.
        return sorted(
            [m for m in messages if not m.pop("excluded")], key=lambda m: (m["at"], m["id"])
        )

    @staticmethod
    def normalize(provider, data, account_email, *, for_reply=False):
        try:
            if provider == "gmail":
                headers = data.get("payload", {}).get("headers", [])
                if not isinstance(headers, list) or len(headers) > 30:
                    raise ValueError()
                fields = {}
                for header in headers:
                    name = text(header["name"], 60).lower()
                    if name in fields:
                        raise ValueError()
                    fields[name] = mail_header(header["value"])
                raw_sender = fields.get("from", "")
                sender = mail_header(raw_sender, decode=True)
                subject = mail_header(fields.get("subject", ""), decode=True)
                sender_address = parseaddr(raw_sender)[1]
                reply_addresses = getaddresses([fields.get("reply-to") or raw_sender])
                rfc_id = fields.get("message-id", "")
                labels = data.get("labelIds", [])
                if not isinstance(labels, list) or any(not isinstance(v, str) for v in labels):
                    raise ValueError()
                millis = str(data["internalDate"])
                if not re.fullmatch(r"[0-9]{1,16}", millis):
                    raise ValueError()
                at = datetime.fromtimestamp(int(millis) / 1000, timezone.utc)
                thread = data["threadId"]
                outgoing = "SENT" in labels
                excluded = bool({"DRAFT", "TRASH", "SPAM"}.intersection(labels))
                if outgoing and for_reply:
                    reply_addresses = getaddresses([fields.get("to", "")])
            else:
                address = data.get("from", {}).get("emailAddress", {})
                sender = text(address.get("address", ""), 254)
                sender_address = sender
                subject = mail_header(data.get("subject", ""))
                reply_to = data.get("replyTo") or []
                if not isinstance(reply_to, list) or len(reply_to) > 20:
                    raise ValueError()
                reply_addresses = [("", r["emailAddress"]["address"]) for r in reply_to] or [
                    ("", sender)
                ]
                rfc_id = data.get("internetMessageId") or ""
                at = datetime.fromisoformat(data.get("receivedDateTime") or data["sentDateTime"])
                if at.tzinfo is None or type(data.get("isDraft")) is not bool:
                    raise ValueError()
                thread = data["conversationId"]
                # Header identity is presentation only, never action authority.
                # For Graph, this is an owner-address classification, not proof
                # that another participant actually received or read a message.
                outgoing = sender.casefold() == account_email.casefold()
                excluded = data["isDraft"]
                if outgoing and for_reply:
                    recipients = data.get("toRecipients") or []
                    if not isinstance(recipients, list) or len(recipients) > 20:
                        raise ValueError()
                    reply_addresses = [("", r["emailAddress"]["address"]) for r in recipients]
            if not 2000 <= at.year <= 2100:
                raise ValueError()
            if for_reply and len(subject) > 200:
                raise DomainError("EMAIL_REPLY_UNAVAILABLE", 409)
            reply_address = reply_addresses[0][1] if len(reply_addresses) == 1 else ""
            if for_reply and (
                not isinstance(reply_address, str)
                or len(reply_address) > 254
                or not isinstance(rfc_id, str)
                or len(rfc_id) > 400
            ):
                raise DomainError("EMAIL_REPLY_UNAVAILABLE", 409)
            return {
                "id": identifier(data["id"]),
                "thread_id": identifier(thread),
                "subject": subject if for_reply else text(subject, 200),
                "sender": text(sender, 254),
                "sender_address": text(sender_address, 254),
                **(
                    {
                        "reply_address": reply_address,
                        "rfc_message_id": rfc_id,
                    }
                    if for_reply
                    else {}
                ),
                "at": at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "outgoing": outgoing,
                "excluded": excluded,
            }
        except (TypeError, KeyError, ValueError, OverflowError, OSError, AttributeError):
            raise DomainError("MAIL_THREAD_INVALID", 502) from None

import base64
import json
from urllib.parse import parse_qs, urlsplit
import httpx
from email import message_from_bytes
import pytest
from pydantic import ValidationError
from desk.app import create_app
from desk.gmail_api import GmailAPI, MailTransportError
from desk.microsoft_apps import OutlookSender
from desk.app_specs import SCOPES
from desk.outbound_mail import OutboundMail
from desk.outbound_mail_models import MailDraft
from desk.store import DomainError


class FakeMail:
    def __init__(self):
        self.sent = []
        self.failure = None

    def send(self, email, password, draft, message_id):
        if self.failure:
            raise self.failure
        self.sent.append((email, draft, message_id))
        return {"accepted": True, "provider_id": "fixture-message"}


@pytest.fixture
def mail(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    transport = FakeMail()
    runtime.outbound_mail.transport = transport
    return runtime, transport


def connect(runtime, provider="gmail"):
    auth = runtime.outbound_mail.auth_for(provider)
    auth.config = {
        "client_id": "fixture",
        "client_secret": "fixture-secret" if provider == "gmail" else "",
        "redirect_uri": "http://127.0.0.1:8831/api/apps/"
        + ("gmail" if provider == "gmail" else "microsoft")
        + "/callback",
    }

    def oauth(request):
        if request.url.path.endswith("/token"):
            return httpx.Response(
                200,
                json={
                    "access_token": "fixture-access",
                    "refresh_token": "fixture-refresh",
                    "expires_in": 3600,
                    "scope": " ".join(SCOPES[auth.resource]),
                },
            )
        if request.url.path == "/revoke":
            return httpx.Response(200, json={})
        return httpx.Response(
            200,
            json={
                "email": "owner@gmail.com",
                "email_verified": True,
                "mail": "owner@outlook.com",
                "userPrincipalName": "owner@outlook.com",
            },
        )

    auth.transport = httpx.MockTransport(oauth)
    token = runtime.store.authenticate("owner", "fixture")
    issued = auth.begin(token)
    auth.callback(parse_qs(urlsplit(issued["url"]).query)["state"][0], "fixture-code")
    return auth.account()


def draft(runtime, key="draft"):
    return runtime.assistant.tool(
        "email_send_draft", {"to": "me", "subject": "FYP email test", "body": "Test"}, key
    )["proposal"]


def test_connected_owner_draft_sends_once_and_recovers_after_restart(mail):
    runtime, transport = mail
    assert runtime.assistant.tool("email_status", {}, "status")["connected"] is False
    connect(runtime)
    proposal = draft(runtime)
    assert proposal["data"]["to"] == "owner@gmail.com" and not transport.sent
    first = runtime.assistant.decide(proposal["id"], "confirm", "click")
    assert first["result"]["sent"] and not first["result"]["delivery_confirmed"]
    runtime.outbound_mail = OutboundMail(runtime, transport)
    again = runtime.assistant.decide(proposal["id"], "confirm", "new-click")
    assert again["result"]["message_id"] == first["result"]["message_id"]
    assert len(transport.sent) == 1
    with runtime.store.connection() as db:
        secret = db.execute("select encrypted_tokens from gmail_connection").fetchone()[0]
        assert "fixture-refresh" not in secret
        assert all(
            "fixture-access" not in str(tuple(row))
            for row in db.execute("select * from operations")
        )


def test_unknown_send_is_never_retried_even_with_new_click_or_restart(mail):
    runtime, transport = mail
    connect(runtime)
    proposal = draft(runtime)
    transport.failure = MailTransportError("EMAIL_SEND_UNKNOWN", unknown=True)
    with pytest.raises(DomainError, match="EMAIL_SEND_UNKNOWN"):
        runtime.assistant.decide(proposal["id"], "confirm", "click")
    transport.failure = None
    runtime.outbound_mail = OutboundMail(runtime, transport)
    with pytest.raises(DomainError, match="EMAIL_SEND_UNKNOWN"):
        runtime.assistant.decide(proposal["id"], "confirm", "retry")
    with pytest.raises(DomainError, match="EMAIL_SEND_UNKNOWN"):
        runtime.assistant.decide(proposal["id"], "cancel", "cancel-unknown")
    assert not transport.sent


def test_known_pre_send_failure_can_be_explicitly_retried(mail):
    runtime, transport = mail
    connect(runtime)
    proposal = draft(runtime)
    transport.failure = MailTransportError("EMAIL_AUTH_FAILED")
    with pytest.raises(DomainError):
        runtime.assistant.decide(proposal["id"], "confirm", "click")
    transport.failure = None
    assert runtime.assistant.decide(proposal["id"], "confirm", "retry")["result"]["sent"]
    assert len(transport.sent) == 1


def test_disconnect_changed_account_expiry_and_nonowner_cannot_send(mail):
    runtime, transport = mail
    connect(runtime)
    proposal = draft(runtime)
    with pytest.raises(DomainError):
        runtime.assistant.decide(proposal["id"], "confirm", "paired", allow_memory=False)
    assert not runtime.assistant.proposals(allow_memory=False)
    connect(runtime)
    with pytest.raises(DomainError, match="EMAIL_CONNECTION_CHANGED"):
        runtime.assistant.decide(proposal["id"], "confirm", "stale")
    current = draft(runtime, "new-draft")
    runtime.outbound_mail.disconnect(runtime.outbound_mail.snapshot()["version"])
    with pytest.raises(DomainError):
        runtime.assistant.decide(current["id"], "confirm", "disconnected")
    connect(runtime)
    expired = draft(runtime, "expired")
    with runtime.store.connection(write=True) as db:
        db.execute(
            "update assistant_proposals set expires_at='2000-01-01T00:00:00Z' where id=?",
            (expired["id"],),
        )
    with pytest.raises(DomainError):
        runtime.assistant.decide(expired["id"], "confirm", "late")
    assert not transport.sent


def test_acceptance_without_http_receipt_recovers_without_resending_after_expiry(mail):
    runtime, transport = mail
    connect(runtime)
    proposal = draft(runtime)
    runtime.assistant.decide(proposal["id"], "confirm", "first")
    with runtime.store.connection(write=True) as db:
        db.execute("delete from operations where id=?", ("assistant-confirm/" + proposal["id"],))
        db.execute(
            "update assistant_proposals set state='pending',result=NULL,expires_at='2000-01-01T00:00:00Z' where id=?",
            (proposal["id"],),
        )
    assert runtime.assistant.decide(proposal["id"], "confirm", "recover")["result"]["sent"]
    assert len(transport.sent) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("to", "me\r\nBcc:other@example.com"),
        ("subject", "Hi\r\nBcc:other@example.com"),
        ("body", "\x00"),
    ],
)
def test_mail_headers_and_message_content_are_bounded(field, value):
    data = {"to": "me", "subject": "Test", "body": "Test", field: value}
    with pytest.raises(ValidationError):
        MailDraft.model_validate(data)


@pytest.mark.parametrize("provider", ["gmail", "outlook"])
def test_oauth_mail_transport_preserves_content_and_records_provider_acceptance(provider):
    seen = []

    def handler(request):
        seen.append(request)
        assert request.headers["authorization"] == "Bearer fixture-access"
        if provider == "gmail":
            encoded = json.loads(request.content)["raw"]
            raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            assert request.url.host == "gmail.googleapis.com"
            response = httpx.Response(200, json={"id": "provider-message"})
        else:
            raw = base64.b64decode(request.content)
            assert request.url.path == "/v1.0/me/sendMail"
            response = httpx.Response(202, headers={"request-id": "provider-request"})
        message = message_from_bytes(raw)
        assert message["To"] == "recipient@example.com"
        assert message["Message-ID"] == "<test@example.com>"
        assert message.get_payload(decode=True).decode().strip() == "你好 Test"
        return response

    sender = (GmailAPI if provider == "gmail" else OutlookSender)(httpx.MockTransport(handler))
    result = sender.send(
        "owner@example.com",
        "fixture-access",
        {"to": "recipient@example.com", "subject": "Test", "body": "你好 Test"},
        "<test@example.com>",
    )
    assert result["accepted"] and result["provider_id"]
    assert len(seen) == 1


@pytest.mark.parametrize("failure,unknown", [("connect", False), ("read", True), ("server", True)])
def test_gmail_failures_never_automatically_reissue_a_send(failure, unknown):
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "connect":
            raise httpx.ConnectTimeout("fixture")
        if failure == "read":
            raise httpx.ReadTimeout("fixture")
        return httpx.Response(500, json={"error": "fixture"})

    with pytest.raises(MailTransportError) as error:
        GmailAPI(httpx.MockTransport(handler)).send(
            "owner@example.com",
            "fixture-access",
            {"to": "recipient@example.com", "subject": "Test", "body": "Test"},
            "<test@example.com>",
        )
    assert error.value.unknown is unknown
    assert len(calls) == 1


def test_multiple_connected_senders_require_a_choice_and_outlook_uses_same_review(mail):
    runtime, gmail = mail
    connect(runtime)
    connect(runtime, "outlook")
    outlook = FakeMail()
    runtime.outbound_mail.outlook = outlook
    choice = runtime.outbound_mail.draft(
        MailDraft(to="me", subject="Test", body="Test"), "ambiguous"
    )
    assert choice["sender_choice_required"] and "proposal" not in choice
    proposal = runtime.outbound_mail.draft(
        MailDraft(provider="outlook", to="me", subject="Test", body="Test"), "outlook"
    )["proposal"]
    assert proposal["data"]["to"] == "owner@outlook.com"
    result = runtime.assistant.decide(proposal["id"], "confirm", "send-outlook")
    assert result["result"]["provider"] == "outlook" and len(outlook.sent) == 1 and not gmail.sent

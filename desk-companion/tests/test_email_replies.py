import base64
from email import policy
from email.parser import BytesParser
import json

import httpx
import pytest

from desk.email_replies import prepare_reply
from desk.gmail_api import GmailAPI
from desk.microsoft_apps import OutlookSender
from desk.outbound_mail_models import MailReplyDraft
from desk.store import DomainError
import test_mail_followups as followed


@pytest.fixture
def world(tmp_path):
    return followed.world.__wrapped__(tmp_path)


def draft(world, *, key="reply", body="I can attend at 3 pm."):
    return prepare_reply(
        world[0], MailReplyDraft(provider="gmail", message_id="m1", body=body), key
    )["proposal"]


def send(world, proposal):
    return world[0].assistant.decide(proposal["id"], "confirm", "confirm-" + proposal["id"])


def test_reply_review_binds_recipient_subject_thread_and_sends_once(world):
    r, _, _, provider, _, _ = world
    provider.messages[0]["payload"]["headers"].append(
        {"name": "Reply-To", "value": "Team <team@example.com>"}
    )
    writes = []

    def accept(request):
        writes.append(request)
        return httpx.Response(200, json={"id": "sent-1", "threadId": "thread-1"})

    r.outbound_mail.transport = GmailAPI(transport=httpx.MockTransport(accept))
    proposal = draft(world)
    assert not writes
    assert proposal["kind"] == "email_send"
    assert proposal["data"]["to"] == "team@example.com"
    assert proposal["data"]["subject"] == "Meeting reply"
    receipt = send(world, proposal)["result"]
    assert receipt["sent"] and not receipt["delivery_confirmed"]
    assert receipt["thread_binding_confirmed"] and receipt["reply_target_id"] == "m1"
    assert len(writes) == 1
    payload = json.loads(writes[0].content)
    assert payload["threadId"] == "thread-1"
    message = BytesParser(policy=policy.default).parsebytes(
        base64.urlsafe_b64decode(payload["raw"] + "==")
    )
    assert message["To"] == "team@example.com"
    assert message["Subject"] == "Meeting reply"
    assert message["In-Reply-To"] == message["References"] == "<m1@example.com>"
    assert "I can attend at 3 pm." in message.get_content()
    send(world, proposal)
    assert len(writes) == 1


@pytest.mark.parametrize("change", ["recipient", "subject", "message_id"])
def test_changed_reply_target_blocks_send_before_reservation(world, change):
    r, _, _, provider, _, _ = world
    proposal = draft(world)
    target = {"recipient": "From", "subject": "Subject", "message_id": "Message-ID"}[change]
    for header in provider.messages[0]["payload"]["headers"]:
        if header["name"] == target:
            header["value"] = {
                "recipient": "other@example.com",
                "subject": "Changed subject",
                "message_id": "<changed@example.com>",
            }[change]
    with pytest.raises(DomainError, match="EMAIL_REPLY_CHANGED"):
        send(world, proposal)
    with r.store.connection() as conn:
        assert conn.execute("SELECT count(*) FROM outgoing_mail_attempts").fetchone()[0] == 0


def test_unknown_reply_cannot_be_resent_by_confirmation_or_new_draft(world):
    r, _, _, _, _, _ = world
    writes = []

    def lost(request):
        writes.append(request)
        raise httpx.ReadTimeout("Fixture unknown reply", request=request)

    r.outbound_mail.transport = GmailAPI(transport=httpx.MockTransport(lost))
    proposal = draft(world)
    for _ in range(2):
        with pytest.raises(DomainError, match="EMAIL_SEND_UNKNOWN"):
            send(world, proposal)
    with pytest.raises(DomainError, match="EMAIL_SEND_UNKNOWN"):
        draft(world, key="new-key", body="Try the same reply again")
    assert len(writes) == 1


def test_correction_supersedes_unsent_reply_only(world):
    r = world[0]
    first = draft(world)
    second = draft(world, key="corrected", body="I can attend at 4 pm.")
    with r.store.connection() as conn:
        assert (
            conn.execute(
                "SELECT state FROM assistant_proposals WHERE id=?", (first["id"],)
            ).fetchone()[0]
            == "cancelled"
        )
    with pytest.raises(DomainError, match="DRAFT_EXPIRED"):
        send(world, first)
    assert second["data"]["body"] == "I can attend at 4 pm."


def test_encoded_subject_and_whitespace_are_preserved_for_thread_match(world):
    provider = world[3]
    for header in provider.messages[0]["payload"]["headers"]:
        if header["name"] == "Subject":
            header["value"] = "=?utf-8?b?5Lya6K6u56Gu6K6k?=  two spaces"
    proposal = draft(world)
    assert proposal["data"]["subject"] == "会议确认  two spaces"


def test_reply_to_sent_mail_uses_the_original_recipient(world):
    provider = world[3]
    provider.messages[0] = followed.gmail_message("m1", sender="owner@example.com", sent=True)
    provider.messages[0]["payload"]["headers"].append(
        {"name": "To", "value": "Alex <alex@example.com>"}
    )
    assert draft(world)["data"]["to"] == "alex@example.com"


@pytest.mark.parametrize("value", ["a@example.com, b@example.com", "invalid address"])
def test_ambiguous_reply_address_is_not_guessed(world, value):
    world[3].messages[0]["payload"]["headers"].append({"name": "Reply-To", "value": value})
    with pytest.raises(DomainError, match="EMAIL_REPLY_UNAVAILABLE"):
        draft(world)


def test_outlook_reply_uses_official_reply_endpoint_and_keeps_acceptance_boundary():
    writes = []

    def accepted(request):
        writes.append(request)
        return httpx.Response(202, headers={"request-id": "provider-receipt"})

    sender = OutlookSender(transport=httpx.MockTransport(accepted))
    receipt = sender.send(
        "owner@example.com",
        "synthetic-token",
        {
            "to": "alex@example.com",
            "subject": "Meeting",
            "body": "See you then.",
            "reply": {"message_id": "immutable-id=="},
        },
        "<local@example.com>",
    )
    request = writes[0]
    assert request.url.path.endswith("/messages/immutable-id==/reply")
    assert request.headers["Prefer"] == 'IdType="ImmutableId"'
    body = json.loads(request.content)
    assert body["message"]["toRecipients"] == [{"emailAddress": {"address": "alex@example.com"}}]
    assert body["message"]["body"] == {"contentType": "Text", "content": "See you then."}
    assert "comment" not in body
    assert receipt["accepted"] and receipt["http_status"] == 202
    assert not receipt["thread_binding_confirmed"]


def test_mismatched_gmail_thread_receipt_stays_accepted_without_claiming_binding(world):
    r = world[0]
    r.outbound_mail.transport = GmailAPI(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"id": "sent-1", "threadId": "different-thread"}
            )
        )
    )
    receipt = send(world, draft(world))["result"]
    assert receipt["sent"] and not receipt["thread_binding_confirmed"]
    assert not receipt["delivery_confirmed"]


@pytest.mark.parametrize(
    "name,value",
    [
        ("Reply-To", "a" * 250 + "@example.com"),
        ("Message-ID", "<" + "a" * 400 + "@example.com>"),
        ("Subject", "a" * 201),
    ],
)
def test_reply_identity_fields_are_never_silently_truncated(world, name, value):
    provider = world[3]
    headers = provider.messages[0]["payload"]["headers"]
    provider.messages[0]["payload"]["headers"] = [h for h in headers if h["name"] != name] + [
        {"name": name, "value": value}
    ]
    with pytest.raises(DomainError, match="EMAIL_REPLY_UNAVAILABLE"):
        draft(world)

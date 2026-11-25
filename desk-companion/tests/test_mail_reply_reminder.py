"""Followed-thread reply: one reminder, then an owner decision to draft.

The mailbox is a local sample or a synthetic provider. Neither is a live account.
"""

from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.store import DomainError
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences


BODY = "Friday after 3 still works for me."
INVOICE = "Here is the copy you asked to review."


def post(client, path, body, key):
    return client.post(
        path,
        json=body,
        headers={"X-Desk-Request": "1", "X-Operation-Id": key},
    )


@pytest.fixture
def desk(tmp_path):
    now = [datetime(2026, 11, 25, 4, tzinfo=timezone.utc)]
    app = create_app(tmp_path, password="fixture", clock=lambda: now[0], scheduler=False)
    client = TestClient(app)
    assert post(client, "/api/session", {"username": "owner", "password": "fixture"}, "login").status_code == 200
    actor = {"kind": "owner", "session": client.cookies.get("desk_companion_session")}
    return app.state.runtime, client, actor, now


def follow(desk, thread, key):
    result = post(desk[1], "/api/mail-followups/sample/follow", {"thread_id": thread}, key)
    assert result.status_code == 200, result.text
    return result.json()


def simulate(desk, key="reply"):
    result = post(desk[1], "/api/mail-followups/sample/replies", {}, key)
    assert result.status_code == 200, result.text
    return result.json()


def reminders(desk):
    result = desk[1].get("/api/mail-followups/reminders", headers={"X-Desk-Request": "1"})
    assert result.status_code == 200, result.text
    return result.json()["reminders"]


def quiet(desk, enabled):
    runtime = desk[0]
    prefs = runtime.data.preferences()
    runtime.data.update(
        PreferencesUpdate(
            expected_version=prefs["version"],
            preferences=WorkspacePreferences(
                quiet_enabled=enabled,
                quiet_start="00:00",
                quiet_end="23:59",
            ),
        ),
        "quiet-" + str(enabled),
    )


def test_one_reminder_for_a_followed_reply_and_none_for_an_unfollowed_thread(desk):
    runtime, client, actor, _now = desk
    before = follow(desk, "sample-venue", "follow-venue")
    assert reminders(desk) == []
    simulate(desk)
    rows = reminders(desk)
    assert len(rows) == 1
    assert rows[0]["task_id"] == before["task_id"]
    note = next(n for n in runtime.notify.listing(open_only=True)["notices"] if n["kind"] == "mail_followup")
    assert note["task_id"] == before["task_id"]
    assert "task_id" not in note["push"]
    assert rows[0]["live_mailbox"] is False
    assert rows[0]["source_label"].startswith("Local mail sample")
    assert rows[0]["count"] == 1
    assert "sample-invoice" not in json.dumps(rows)
    assert INVOICE not in json.dumps(rows)
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM mail_followups").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM owner_memories").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM text_ai_usage").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM outgoing_mail_attempts").fetchone()[0] == 0
    assert client.get("/api/mail-followups/sample", headers={"X-Desk-Request": "1"}).json()["live_mailbox"] is False
    assert actor["kind"] == "owner"


def test_replay_restart_and_the_same_event_do_not_notify_twice(desk):
    from desk.mail_followups import MailFollowups
    from desk.mail_reply_reminder import MailReplyReminders

    runtime, client, _actor, _now = desk
    first = follow(desk, "sample-venue", "follow-once")
    again = follow(desk, "sample-venue", "follow-once")
    other = follow(desk, "sample-venue", "follow-again")
    assert again["followup_id"] == first["followup_id"]
    assert other["already_following"] is True
    assert other["followup_id"] == first["followup_id"]
    simulate(desk, "release-once")
    simulate(desk, "release-once")
    notice = runtime.notify.listing()["notices"]
    assert len(notice) == 1
    runtime.mail_followups = MailFollowups(runtime)
    runtime.mail_replies = MailReplyReminders(runtime)
    runtime.mail_followups.poll_source_once()
    assert [item["id"] for item in runtime.notify.listing()["notices"]] == [notice[0]["id"]]
    assert len(reminders(desk)) == 1
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1


def test_quiet_hours_hold_the_reminder_until_they_end(desk):
    runtime, _client, _actor, _now = desk
    follow(desk, "sample-venue", "follow-quiet")
    quiet(desk, True)
    simulate(desk, "quiet-reply")
    assert reminders(desk) == []
    assert runtime.notify.listing()["notices"] == []
    quiet(desk, False)
    runtime.mail_followups.poll_source_once()
    runtime.mail_followups.poll_source_once()
    assert len(reminders(desk)) == 1
    assert len(runtime.notify.listing()["notices"]) == 1


def test_failed_read_is_not_a_confirmed_reply_and_reread_does_not_send(desk):
    runtime, client, _actor, _now = desk
    follow(desk, "sample-venue", "follow-fail")
    with runtime.store.connection(write=True) as conn:
        conn.execute("UPDATE local_mail_sample SET fail=1")
    runtime.mail_replies.reload()
    simulate(desk, "failed-release")
    assert reminders(desk) == []
    with runtime.store.connection() as conn:
        row = conn.execute("SELECT unread_count, error FROM mail_followups").fetchone()
    assert row["unread_count"] == 0 and row["error"] == "APP_CONNECTION_FAILED"
    with runtime.store.connection(write=True) as conn:
        conn.execute("UPDATE local_mail_sample SET fail=0")
    runtime.mail_replies.reload()
    desk[3][0] += timedelta(minutes=16)
    runtime.mail_followups.poll_source_once()
    row = reminders(desk)[0]
    with runtime.store.connection(write=True) as conn:
        conn.execute("UPDATE local_mail_sample SET fail=1")
    runtime.mail_replies.reload()
    failed = post(client, f"/api/mail-followups/{row['id']}/reread", {}, "reread-broken")
    assert failed.status_code == 200
    assert failed.json()["confirmed_reply"] is False
    assert failed.json()["sent"] is False
    assert failed.json()["state"] == "failed"
    opened = post(
        client,
        f"/api/mail-followups/{row['id']}/reads",
        {"message_id": row["message_ids"][0]},
        "read-broken",
    )
    assert opened.status_code == 200
    assert opened.json()["confirmed_reply"] is False
    assert "message" not in opened.json()
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM outgoing_mail_attempts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM owner_memories").fetchone()[0] == 0


def test_owner_can_read_the_original_without_making_it_memory(desk):
    runtime, client, _actor, _now = desk
    follow(desk, "sample-venue", "follow-read")
    simulate(desk, "read-release")
    row = reminders(desk)[0]
    opened = post(
        client,
        f"/api/mail-followups/{row['id']}/reads",
        {"message_id": row["message_ids"][0]},
        "read-once",
    )
    assert opened.status_code == 200
    assert opened.json()["message"]["body"] == BODY
    assert opened.json()["stored_body"] is False
    assert opened.json()["sent"] is False
    again = post(
        client,
        f"/api/mail-followups/{row['id']}/reads",
        {"message_id": row["message_ids"][0]},
        "read-once",
    )
    assert again.json()["message"]["body"] == BODY
    with runtime.store.connection() as conn:
        stored = " ".join(item["response"] for item in conn.execute("SELECT response FROM operations"))
        notes = " ".join(item["note"] for item in conn.execute("SELECT note FROM task_evidence"))
    assert BODY not in stored
    assert BODY not in notes
    assert BODY not in json.dumps(runtime.initiative.sources.collect(refresh=False))
    checked = post(client, f"/api/mail-followups/{row['id']}/reread", {}, "check-once")
    assert checked.json()["reply_present"] is True
    assert checked.json()["sent"] is False
    assert checked.json()["confirmed_reply"] is False
    post(client, f"/api/mail-followups/{row['id']}/reread", {}, "check-once")
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM outgoing_mail_attempts").fetchone()[0] == 0


def test_draft_is_offered_only_after_the_owner_chooses_it_and_does_not_send(desk):
    runtime, client, _actor, _now = desk
    follow(desk, "sample-venue", "follow-draft")
    simulate(desk, "draft-release")
    row = reminders(desk)[0]
    assert row["draft"] is None
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM assistant_proposals").fetchone()[0] == 0
    draft = post(
        client,
        f"/api/mail-followups/{row['id']}/reply-drafts",
        {
            "message_id": row["message_ids"][0],
            "fingerprint": row["fingerprint"],
            "observation_revision": row["observation_revision"],
            "summary": row["summary"],
            "body": "Thanks for the update. I have not sent this reply.",
        },
        "draft-once",
    )
    assert draft.status_code == 200, draft.text
    proposal = draft.json()["proposal"]
    assert proposal["data"]["send"] is False
    assert proposal["data"]["body"].startswith("Thanks")
    saved = post(
        client,
        f"/api/assistant/proposals/{proposal['id']}/decisions",
        {"action": "confirm"},
        "save-draft",
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["result"]["sent"] is False
    post(client, f"/api/assistant/proposals/{proposal['id']}/decisions", {"action": "confirm"}, "save-draft")
    with runtime.store.connection() as conn:
        notes = [item["note"] for item in conn.execute("SELECT note FROM task_evidence")]
        assert conn.execute("SELECT COUNT(*) FROM outgoing_mail_attempts").fetchone()[0] == 0
        assert sum("Nothing was sent" in note for note in notes) == 1
        assert all(BODY not in note for note in notes)


def test_dismissing_one_reminder_keeps_the_other(desk):
    runtime, client, _actor, _now = desk
    venue = follow(desk, "sample-venue", "follow-both-venue")
    invoice = follow(desk, "sample-invoice", "follow-both-invoice")
    simulate(desk, "both-replies")
    rows = reminders(desk)
    assert {row["task_id"] for row in rows} == {venue["task_id"], invoice["task_id"]}
    venue_row = next(row for row in rows if row["task_id"] == venue["task_id"])
    dismissed = post(
        client,
        f"/api/mail-followups/{venue_row['id']}/acknowledge",
        {"observed_revision": venue_row["observation_revision"]},
        "dismiss-venue",
    )
    assert dismissed.status_code == 200, dismissed.text
    post(
        client,
        f"/api/mail-followups/{venue_row['id']}/acknowledge",
        {"observed_revision": venue_row["observation_revision"]},
        "dismiss-venue",
    )
    left = reminders(desk)
    assert len(left) == 1 and left[0]["task_id"] == invoice["task_id"]
    with runtime.store.connection() as conn:
        open_notices = conn.execute(
            "SELECT id FROM notice_inbox WHERE state='open'"
        ).fetchall()
    assert len(open_notices) == 1


def test_wrong_thread_cannot_take_another_tasks_reply(desk):
    runtime, client, _actor, _now = desk
    venue = follow(desk, "sample-venue", "follow-wrong-venue")
    invoice = follow(desk, "sample-invoice", "follow-wrong-invoice")
    simulate(desk, "wrong-release")
    rows = {row["task_id"]: row for row in reminders(desk)}
    foreign = post(
        client,
        f"/api/mail-followups/{rows[venue['task_id']]['id']}/reads",
        {"message_id": "sample-invoice-2"},
        "wrong-read",
    )
    assert foreign.status_code == 409
    assert foreign.json()["error"]["code"] == "MAIL_REPLY_UNRELATED"
    draft = post(
        client,
        f"/api/mail-followups/{rows[venue['task_id']]['id']}/reply-drafts",
        {
            "message_id": rows[invoice["task_id"]]["message_ids"][0],
            "fingerprint": rows[venue["task_id"]]["fingerprint"],
            "observation_revision": rows[venue["task_id"]]["observation_revision"],
            "summary": rows[venue["task_id"]]["summary"],
            "body": "Wrong task",
        },
        "wrong-draft",
    )
    assert draft.status_code == 409
    with runtime.store.connection() as conn:
        notes = " ".join(item["note"] for item in conn.execute("SELECT note FROM task_evidence WHERE task_id=?", (invoice["task_id"],)))
    assert "Wrong task" not in notes
    assert INVOICE not in notes


def test_stale_approval_cannot_send_or_escape_its_summary(desk):
    runtime, client, _actor, _now = desk
    follow(desk, "sample-venue", "follow-stale")
    simulate(desk, "stale-release")
    row = reminders(desk)[0]
    draft = post(
        client,
        f"/api/mail-followups/{row['id']}/reply-drafts",
        {
            "message_id": row["message_ids"][0],
            "fingerprint": row["fingerprint"],
            "observation_revision": row["observation_revision"],
            "summary": row["summary"],
            "body": "Thanks for the update. I have not sent this reply.",
        },
        "stale-draft",
    ).json()["proposal"]
    with runtime.store.connection(write=True) as conn:
        conn.execute(
            "UPDATE mail_followups SET observation_revision=observation_revision+1 WHERE id=?",
            (row["id"],),
        )
        data = json.loads(conn.execute("SELECT data FROM assistant_proposals WHERE id=?", (draft["id"],)).fetchone()[0])
        data["send"] = True
        conn.execute("UPDATE assistant_proposals SET data=? WHERE id=?", (json.dumps(data), draft["id"]))
    denied = post(client, f"/api/assistant/proposals/{draft['id']}/decisions", {"action": "confirm"}, "stale-save")
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] in {"MAIL_REPLY_CHANGED", "MAIL_REPLY_SEND_FORBIDDEN"}
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM outgoing_mail_attempts").fetchone()[0] == 0
        assert conn.execute("SELECT state FROM assistant_proposals WHERE id=?", (draft["id"],)).fetchone()[0] == "pending"


def test_unknown_send_is_not_retried_by_check_or_a_new_draft(desk):
    runtime, client, _actor, now = desk
    follow(desk, "sample-venue", "follow-unknown")
    simulate(desk, "unknown-release")
    row = reminders(desk)[0]
    message_id = row["message_ids"][0]
    with runtime.store.connection(write=True) as conn:
        conn.execute(
            "INSERT INTO assistant_proposals VALUES(?,?,?,'confirmed',?,?,NULL)",
            (
                "a" * 32,
                "email_send",
                json.dumps({"reply": {"message_id": message_id}, "provider": "gmail"}),
                "2026-11-25T05:00:00Z",
                "2026-11-25T04:00:00Z",
            ),
        )
        conn.execute(
            "INSERT INTO outgoing_mail_attempts VALUES(?,?,?,?,?,?,NULL)",
            ("a" * 32, "provider-message", "unknown", 1, "2026-11-25T04:00:00Z", None),
        )
    checked = post(client, f"/api/mail-followups/{row['id']}/reread", {}, "unknown-check")
    assert checked.json()["state"] == "unknown"
    assert checked.json()["sent"] is False
    assert checked.json()["confirmed_reply"] is False
    denied = post(
        client,
        f"/api/mail-followups/{row['id']}/reply-drafts",
        {
            "message_id": message_id,
            "fingerprint": row["fingerprint"],
            "observation_revision": row["observation_revision"],
            "summary": row["summary"],
            "body": "Do not send this",
        },
        "unknown-draft",
    )
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "EMAIL_SEND_UNKNOWN"
    post(client, f"/api/mail-followups/{row['id']}/reread", {}, "unknown-check")
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM outgoing_mail_attempts").fetchone()[0] == 1
        assert conn.execute("SELECT state FROM outgoing_mail_attempts").fetchone()[0] == "unknown"
    del now


def test_paired_revoked_and_hidden_sessions_cannot_read_or_act(desk):
    runtime, client, actor, _now = desk
    followed = follow(desk, "sample-venue", "follow-private")
    simulate(desk, "private-release")
    row = reminders(desk)[0]
    with pytest.raises(DomainError) as display:
        runtime.mail_replies.reminders({"kind": "display", "id": "screen", "session": actor["session"]})
    assert display.value.code == "OWNER_SIGN_IN_REQUIRED"
    client.delete("/api/session", headers={"X-Desk-Request": "1"})
    assert client.get("/api/mail-followups/reminders", headers={"X-Desk-Request": "1"}).status_code == 403
    assert post(client, "/api/mail-followups/sample/follow", {"thread_id": "sample-invoice"}, "after-logout").status_code == 403
    assert post(client, "/api/session", {"username": "owner", "password": "fixture"}, "login-again").status_code == 200
    hidden = post(
        client,
        "/api/settings",
        {"expected_version": 1, "timezone": "Asia/Hong_Kong", "hide_private": True},
        "hide",
    )
    assert hidden.status_code == 200, hidden.text
    assert client.get("/api/mail-followups/reminders", headers={"X-Desk-Request": "1"}).status_code == 403
    draft = post(
        client,
        f"/api/mail-followups/{row['id']}/reads",
        {"message_id": row["message_ids"][0]},
        "hidden-read",
    )
    assert draft.status_code == 403
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM mail_reply_reads").fetchone()[0] == 0
    post(
        client,
        "/api/settings",
        {"expected_version": 2, "timezone": "Asia/Hong_Kong", "hide_private": False},
        "show",
    )
    opened = post(
        client,
        f"/api/mail-followups/{row['id']}/reads",
        {"message_id": row["message_ids"][0]},
        "visible-read",
    )
    assert opened.json()["message"]["body"] == BODY
    forgotten = post(client, f"/api/mail-followups/{followed['followup_id']}/forget", {}, "forget-one")
    assert forgotten.status_code == 200
    assert reminders(desk) == []
    with runtime.store.connection() as conn:
        stored = " ".join(item["response"] for item in conn.execute("SELECT response FROM operations"))
    assert BODY not in stored
    assert followed["task_id"]


def test_connected_mailbox_reply_uses_the_same_reminder_without_a_live_account(tmp_path):
    now = [datetime(2026, 11, 25, 4, tzinfo=timezone.utc)]
    app = create_app(tmp_path, password="fixture", clock=lambda: now[0], scheduler=False)
    runtime = app.state.runtime
    provider = Gmail()
    account = {"connected": True, "configured": True, "email": "owner@example.com", "version": "connection-1"}
    runtime.outbound_mail.auth.account = lambda: dict(account)
    runtime.outbound_mail.auth.access_token = lambda: "synthetic-mail-token"
    runtime.outbound_mail.auth.transport = httpx.MockTransport(provider)
    client = TestClient(app)
    assert post(client, "/api/session", {"username": "owner", "password": "fixture"}, "login").status_code == 200
    draft = runtime.mail_followups.draft({"provider": "gmail", "message_id": "m1"}, "preview")["proposal"]
    confirmed = post(
        client,
        f"/api/assistant/proposals/{draft['id']}/decisions",
        {"action": "confirm", "follow_mail_thread": True},
        "confirm-follow",
    )
    assert confirmed.status_code == 200, confirmed.text
    runtime.mail_followups.poll_source_once()
    provider.messages.append(message("m2", "Synthetic snippet only"))
    provider.status = 500
    now[0] += timedelta(minutes=16)
    runtime.mail_followups.poll_source_once()
    assert client.get("/api/mail-followups/reminders", headers={"X-Desk-Request": "1"}).json()["reminders"] == []
    provider.status = 200
    now[0] += timedelta(minutes=16)
    runtime.mail_followups.poll_source_once()
    rows = client.get("/api/mail-followups/reminders", headers={"X-Desk-Request": "1"}).json()["reminders"]
    assert len(rows) == 1
    assert rows[0]["source_label"] == "Connected mailbox"
    assert "Synthetic snippet only" not in json.dumps(rows)
    opened = post(client, f"/api/mail-followups/{rows[0]['id']}/reads", {"message_id": "m2"}, "gmail-read")
    assert opened.status_code == 200, opened.text
    assert opened.json()["message"]["body"] == "Synthetic snippet only"
    assert opened.json()["stored_body"] is False
    with runtime.store.connection() as conn:
        stored = " ".join(item["response"] for item in conn.execute("SELECT response FROM operations"))
    assert "Synthetic snippet only" not in stored


def message(ident, snippet):
    return {
        "id": ident,
        "threadId": "thread-1",
        "snippet": snippet,
        "internalDate": "1794888000000",
        "labelIds": ["INBOX"],
        "payload": {"headers": [
            {"name": "From", "value": "Alex <alex@example.com>"},
            {"name": "Subject", "value": "Meeting reply"},
            {"name": "Message-ID", "value": f"<{ident}@example.com>"},
        ]},
    }


class Gmail:
    def __init__(self):
        self.messages = [message("m1", "Original")]
        self.status = 200

    def __call__(self, request):
        assert request.url.host == "gmail.googleapis.com"
        if "/messages/" in request.url.path:
            ident = request.url.path.rsplit("/", 1)[-1]
            found = next(item for item in self.messages if item["id"] == ident)
            return httpx.Response(200, json=found)
        if self.status != 200:
            return httpx.Response(self.status, json={"error": "fixture failure"})
        return httpx.Response(200, json={"id": "thread-1", "messages": self.messages})

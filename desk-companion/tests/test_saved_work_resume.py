"""Local HTTP journeys for continuing retained Work without a previous chat report."""

import hashlib
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier, Event

import pytest
from fastapi.testclient import TestClient

from desk import commerce_chat
from desk.app import create_app
from desk.calendar import iso
from desk.conversation_work import parse_work_continue
from desk.outbound_mail import OutboundMail
from desk.store import DomainError
from desk.stream_contract import parse_sse
from desk.text_ai import TextAssistant, TextConfig
from desk.voice import VoiceConfig

NOW = datetime(2026, 11, 23, 8, tzinfo=UTC)
ASK = "Continue the task from before."
ZH = "继续刚才那个任务。"
RUNS = "/api/agent-runs"
MESSAGES = "/api/assistant/messages"


def session(app, label="synthetic-owner"):
    # Preinstalled fixture sessions exercise route authorization without a login.
    digest = hashlib.sha256(label.encode()).hexdigest()
    with app.state.runtime.store.connection(write=True) as db:
        db.execute(
            "INSERT OR IGNORE INTO sessions VALUES(?,?)", (digest, iso(NOW + timedelta(days=7)))
        )
    client = TestClient(app, headers={"X-Desk-Request": "1"})
    client.cookies.set("desk_companion_session", label)
    return client


@pytest.fixture
def launch(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("A local Work continuation attempted external dispatch")

    def commerce(runtime, payload, principal, chat):
        assert not (parse_work_continue(payload.message) or {}).get("saved_work")
        return None

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(
        TextConfig, "environment", lambda: TextConfig(provider="fake", endpoint="local:fixture")
    )
    monkeypatch.setattr(VoiceConfig, "environment", lambda: VoiceConfig())
    monkeypatch.setattr(TextAssistant, "generate", forbidden)
    monkeypatch.setattr(TextAssistant, "_message", forbidden)
    monkeypatch.setattr(OutboundMail, "send", forbidden)
    monkeypatch.setattr(commerce_chat, "turn", commerce)

    def restart():
        app = create_app(
            tmp_path, clock=lambda: NOW, password="fixture", scheduler=False, connector_configs=()
        )
        return session(app)

    return restart


def post(client, path, key, **fields):
    return client.post(path, json=fields, headers={"X-Operation-Id": key})


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def chat(client, key, message=ASK, **scope):
    return post(client, MESSAGES, key, message=message, **scope)


def stream(client, key, **body):
    response = post(client, MESSAGES + "/stream", key, **body)
    assert response.status_code == 200 and response.headers["content-type"].startswith(
        "text/event-stream"
    )
    events = parse_sse(response.text)
    assert events[-1]["type"] == "done", events
    return events[-1]["reply"]


def task(client, name="Selected inventory"):
    return ok(post(client, "/api/tasks", name, title=name, follow_up_enabled=False))["task"]["id"]


def start(client, task_id, goal="Read the selected inventory", **fields):
    scope = ok(client.get(RUNS + "/scope"))
    return ok(
        post(
            client,
            RUNS,
            "start-" + goal,
            goal=goal,
            retain=True,
            task_ids=[task_id],
            scope_revision=scope["scope_revision"],
            **fields,
        )
    )["run"]


def detail(client, run):
    return ok(client.get(f"{RUNS}/{run['id']}"))


def action(client, run, name, **fields):
    path = f"{RUNS}/{run['id']}/actions"
    version = detail(client, run)["run"]["version"]
    return ok(post(client, path, name, action=name, expected_version=version, **fields))["run"]


def test_restart_before_first_report_and_again_with_the_same_chat(launch):
    with launch() as client:
        selected = task(client)
        run = start(client, selected)
        assert detail(client, run)["steps"] == []
        # The older, report-specific command still requires a shown report.
        assert ok(chat(client, "legacy", "Continue this work."))["kind"] == "clarify"

    with launch() as client:
        assert detail(client, run)["run"]["state_reason"] == "RUN_RUNTIME_STOPPED"
        first = stream(client, "first-read", message=ZH, language="zh", task_id=selected)
        found = detail(client, run)
        assert first["work_run_id"] == run["id"] and "已读取" in first["message"]
        assert first["work_version"] == found["run"]["version"]
        assert [(s["kind"], s["id"], s["result"]["evidence_id"]) for s in found["steps"]] == [
            ("read", first["step_id"], "task:" + selected)
        ]
        assert found["steps"][0]["result"]["sha256"] == found["run"]["evidence"][0]["sha256"]
        assert found["artifacts"] == []

    client = launch()
    second = stream(
        client, "compose", message=ASK, task_id=selected, conversation_id=first["conversation_id"]
    )
    assert second["conversation_id"] == first["conversation_id"]
    assert [s["kind"] for s in detail(client, run)["steps"]] == ["read", "compose"]


def test_lost_reply_reuses_checkpoint_and_survives_forget(launch, monkeypatch):
    client = launch()
    selected = task(client)
    run = start(client, selected)
    prior = ok(chat(client, "prior", "Continue this work.", task_id=selected))
    scope = {"task_id": selected, "conversation_id": prior["conversation_id"]}

    def lose_reply(*args):
        raise DomainError("CONVERSATION_WORK_RESULT_UNKNOWN")

    saved = client.app.state.runtime.conversation_work.saved
    monkeypatch.setattr(saved, "_result", lose_reply)
    interrupted = chat(client, "lost", **scope)
    assert interrupted.status_code == 409
    (checkpoint,) = detail(client, run)["steps"]
    assert checkpoint["kind"] == "read"
    conflict = chat(client, "lost", "Continue this work.", **scope)
    assert conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"

    # Simulate a process loss. No in-memory chat or assistant receipt survives.
    client = launch()
    replay = stream(client, "lost", message=ASK, **scope)
    assert (
        replay["step_id"] == checkpoint["id"]
        and replay["conversation_id"] == scope["conversation_id"]
    )
    assert detail(client, run)["steps"] == [checkpoint]
    ok(client.delete("/api/voice/conversations/" + scope["conversation_id"]))
    client = launch()
    assert chat(client, "lost", **scope).status_code == 404
    assert "work_run_id" not in ok(chat(client, "fresh", task_id=selected))
    assert detail(client, run)["steps"] == [checkpoint]


def simultaneous_chat(client, monkeypatch, keys, **scope):
    work = client.app.state.runtime.conversation_work
    prepare = work.prepare_resume
    barrier = Barrier(2)

    def both_read_one_version(*args):
        snapshot = prepare(*args)
        barrier.wait(timeout=10)
        return snapshot

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(work, "prepare_resume", both_read_one_version)
        return list(pool.map(lambda key: chat(client, key, **scope), keys))


@pytest.mark.parametrize("keys", [("same", "same"), ("earlier", "later")])
def test_concurrent_requests_consume_exactly_one_revision(launch, monkeypatch, keys):
    client = launch()
    run = start(client, task(client))
    responses = simultaneous_chat(client, monkeypatch, keys)
    (step,) = detail(client, run)["steps"]
    if keys[0] == keys[1]:
        assert [ok(r)["step_id"] for r in responses] == [step["id"], step["id"]]
        chat_id = ok(responses[0])["conversation_id"]
        assert ok(responses[1])["conversation_id"] == chat_id
        other = start(client, task(client, "Another task"), "Leave this one queued")
        client = launch()
        assert ok(chat(client, "next", conversation_id=chat_id))["work_run_id"] == run["id"]
        assert detail(client, other)["steps"] == []
    else:
        assert sorted(r.status_code for r in responses) == [200, 409]
        loser = next(
            key
            for key, response in zip(keys, responses, strict=True)
            if response.status_code == 409
        )
        assert chat(client, loser).json()["error"]["code"] == "VERSION_CONFLICT"
        assert detail(client, run)["steps"] == [step]


def test_busy_retry_and_cancellation_during_checkpoint(launch, monkeypatch):
    client = launch()
    run = start(client, task(client))
    service = client.app.state.runtime.agent_runs
    with service.worker_lock:
        assert (
            chat(client, "busy").json()["error"]["code"] == "CONVERSATION_WORK_RESULT_INTERRUPTED"
        )
    assert detail(client, run)["steps"] == []
    first = ok(chat(client, "busy"))
    scope = {"conversation_id": first["conversation_id"]}
    composing, release = Event(), Event()
    checkpoint = service._checkpoint

    def stop_before_commit(value, kind, result=None):
        assert kind == "compose"
        composing.set()
        assert release.wait(10)
        return checkpoint(value, kind, result)

    monkeypatch.setattr(service, "_checkpoint", stop_before_commit)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(chat, client, "stop-in-flight", **scope)
        assert composing.wait(10)
        action(client, run, "cancel")
        release.set()
        assert "step_id" not in ok(pending.result(timeout=10))
    assert "step_id" not in ok(chat(client, "stop-in-flight", **scope))
    result = detail(client, run)
    assert result["run"]["state"] == "cancelled"
    assert [s["id"] for s in result["steps"]] == [first["step_id"]]


def test_goal_changed_during_claim_requires_fresh_acknowledgement(launch, monkeypatch):
    client = launch()
    run = start(client, task(client))
    first = ok(chat(client, "original"))
    scope = {"conversation_id": first["conversation_id"]}
    service = client.app.state.runtime.agent_runs
    advance = service.advance_one
    selected, proceed = Event(), Event()

    def wait_before_claim(*args, **kwargs):
        selected.set()
        assert proceed.wait(10)
        return advance(*args, **kwargs)

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=1) as pool:
        patch.setattr(service, "advance_one", wait_before_claim)
        stale = pool.submit(chat, client, "delayed", **scope)
        assert selected.wait(10)
        revised = action(client, run, "steer", goal="Count only the spare parts")
        proceed.set()
        assert stale.result(timeout=10).json()["error"]["code"] == "VERSION_CONFLICT"
    notice = ok(chat(client, "show-goal", **scope))
    assert revised["goal"] in notice["message"] and "step_id" not in notice
    assert detail(client, run)["run"]["version"] == revised["version"]
    assert ok(chat(client, "original"))["plan_revision"] == 2  # replay only
    assert chat(client, "delayed", **scope).json()["error"]["code"] == "VERSION_CONFLICT"
    accepted = ok(chat(client, "accept-revised", **scope))
    steps = detail(client, run)["steps"]
    assert [(s["plan_revision"], s["kind"]) for s in steps] == [(1, "read"), (2, "read")]
    assert accepted["step_id"] == steps[-1]["id"]


def test_simultaneous_asks_cannot_acknowledge_an_unseen_goal(launch, monkeypatch):
    client = launch()
    run = start(client, task(client))
    first = ok(chat(client, "read"))
    scope = {"conversation_id": first["conversation_id"]}
    revised = action(client, run, "steer", goal="Count the sealed crates")
    replies = simultaneous_chat(client, monkeypatch, ("first-notice", "second-notice"), **scope)
    for response in replies:
        notice = ok(response)
        assert revised["goal"] in notice["message"] and "step_id" not in notice
    assert ok(chat(client, "first-notice", **scope)) == ok(replies[0])
    # The revised goal has only been shown in the first chat.
    fresh = ok(chat(client, "different-chat"))
    assert revised["goal"] in fresh["message"] and "step_id" not in fresh
    assert detail(client, run)["run"]["version"] == revised["version"]
    accepted = ok(chat(client, "accept", conversation_id=fresh["conversation_id"]))
    assert [s["id"] for s in detail(client, run)["steps"]] == [
        first["step_id"],
        accepted["step_id"],
    ]


def test_pending_review_uses_original_draft_and_confirmation_even_with_full_access(launch):
    client = launch()
    selected = task(client)
    run = start(
        client,
        selected,
        mutation_requests=[
            {
                "tool": "task_create_draft",
                "arguments": {"title": "Inspect sample B"},
                "required": True,
            }
        ],
    )
    policy = ok(client.get("/api/permissions"))
    ok(post(client, "/api/permissions", "policy", mode="full", expected_version=policy["version"]))
    service = client.app.state.runtime.agent_runs
    for _ in range(3):
        assert service.advance_one(run["id"])
    first = stream(client, "prepare", message=ASK)
    proposal = first["proposal"]
    assert proposal["data"]["task"]["title"] == "Inspect sample B"
    assert proposal["state"] == "pending"
    pending = detail(client, run)
    assert pending["steps"][-1]["id"] == first["step_id"]
    assert pending["run"]["proposal_ids"] == [proposal["id"]]
    assert pending["run"]["state"] == "waiting_review"
    assert len(ok(client.get("/api/tasks"))["tasks"]) == 1
    with client.app.state.runtime.store.connection() as db:
        original_drafts = db.execute(
            """SELECT o.response->>'$.proposal.id' FROM agent_run_effect_intents i
               JOIN operations o ON o.id=i.operation_key WHERE i.run_id=?""",
            (run["id"],),
        ).fetchall()
        assert [r[0] for r in original_drafts] == [proposal["id"]]

    client = launch()  # Reopen the SQLite store while the decision is pending.
    scope = {"conversation_id": first["conversation_id"]}
    again = stream(client, "waiting", message=ZH, **scope)
    assert again["proposal"] == proposal
    assert ok(client.get("/api/assistant/proposals"))["proposals"] == [proposal]
    assert detail(client, run)["steps"] == pending["steps"]

    decision = f"/api/assistant/proposals/{proposal['id']}/decisions"
    ok(post(client, decision, "owner-decision", action="confirm"))
    assert "proposal" not in stream(client, "waiting", message=ZH, **scope)
    assert "proposal" not in ok(chat(client, "prepare"))
    assert detail(client, run)["steps"] == pending["steps"]
    observed = ok(chat(client, "observe", **scope))
    assert ok(chat(client, "observe", **scope))["step_id"] == observed["step_id"]
    final = detail(client, run)
    assert final["steps"][-1]["kind"] == "review_observed"
    assert final["steps"][-1]["result"] == {"states": ["verified"]}
    assert final["run"]["proposal_ids"] == [proposal["id"]]
    with client.app.state.runtime.store.connection() as db:
        receipt = db.execute(
            "SELECT response->>'$.task.id' FROM operations WHERE id=?",
            ("assistant-confirm/" + proposal["id"],),
        ).fetchone()
        assert receipt[0] == final["run"]["effects"][0]["record_id"]
    assert sorted(t["title"] for t in ok(client.get("/api/tasks"))["tasks"]) == [
        "Inspect sample B",
        "Selected inventory",
    ]


def test_multiple_runs_require_a_choice_and_respect_task_and_login(launch):
    client = launch()
    first_task, second_task = task(client, "Samples"), task(client, "Crates")
    first = start(client, first_task, "Count samples")
    second = start(client, second_task, "Count crates")
    choices = ok(chat(client, "which"))
    for run in (first, second):
        assert f"Continue work {run['id']} v{run['version']}" in choices["message"]
        assert detail(client, run)["steps"] == []
    discarded = ok(chat(client, "other-choices"))
    ok(client.delete("/api/voice/conversations/" + discarded["conversation_id"]))
    client = launch()  # A returned choice still works after loss of RAM chat.
    other = session(client.app, "another-synthetic-session")
    assert "Count" not in ok(chat(other, "which"))["message"]
    command = f"Continue work {second['id']} v{second['version']}"
    assert (
        chat(client, "discarded", command, conversation_id=discarded["conversation_id"]).status_code
        == 404
    )
    assert (
        chat(other, "other-choice", command, conversation_id=choices["conversation_id"]).status_code
        == 404
    )
    assert "work_run_id" not in ok(chat(client, "wrong-task", command, task_id=first_task))
    assert "work_run_id" not in ok(chat(other, "wrong-login", command))
    choice = ok(chat(client, "selected", command, conversation_id=choices["conversation_id"]))
    assert choice["work_run_id"] == second["id"]
    next_step = ok(chat(client, "linked", conversation_id=choices["conversation_id"]))
    assert next_step["work_run_id"] == second["id"]
    assert detail(client, first)["steps"] == []
    assert (
        other.post(
            MESSAGES,
            json={"message": ASK, "conversation_id": choice["conversation_id"]},
            headers={"X-Operation-Id": "wrong-chat"},
        ).status_code
        == 404
    )


@pytest.mark.parametrize("stop", ["pause", "cancel", "expire", "privacy"])
def test_closed_or_revoked_runs_stay_closed(launch, stop):
    client = launch()
    run = start(client, task(client))
    first = ok(chat(client, "step"))
    if stop in {"pause", "cancel"}:
        action(client, run, stop)
    elif stop == "expire":
        client.app.state.runtime.store.clock = lambda: NOW + timedelta(hours=25)
    else:
        settings = ok(client.get("/api/assistant/context-settings"))
        ok(
            post(
                client,
                "/api/assistant/context-settings",
                "revoked",
                expected_version=settings["version"],
                save_text_history=False,
                use_text_history_in_ai=False,
                use_memory_in_ai=False,
            )
        )
    stopped = detail(client, run)
    for key, scope in [("step", {}), ("again", {"conversation_id": first["conversation_id"]})]:
        reply = ok(chat(client, key, **scope))
        assert "step_id" not in reply and "proposal" not in reply
        if stop == "privacy":
            assert run["goal"] not in reply["message"] and "work_run_id" not in reply
    assert detail(client, run)["run"]["version"] == stopped["run"]["version"]
    assert detail(client, run)["steps"] == stopped["steps"]


def test_model_run_requires_work_and_vague_chat_never_dispatches(launch):
    client = launch()
    settings = ok(client.get("/api/assistant/context-settings"))
    (destination,) = settings["destinations"]
    ok(
        post(
            client,
            "/api/assistant/context-settings",
            "select-local-fixture",
            expected_version=settings["version"],
            approved_destinations=[destination["id"]],
            save_text_history=False,
            use_text_history_in_ai=False,
            use_memory_in_ai=False,
            share_business_context=True,
        )
    )
    run = start(
        client,
        task(client),
        "Book travel then email the receipt",
        mode="model",
        provider_destination_id=destination["id"],
    )
    reply = ok(
        chat(client, "continue", flight_review={"id": "ab" * 16, "version": 1, "amount_minor": 500})
    )
    assert "Work" in reply["message"] and reply["work_run_id"] == run["id"]
    saved = detail(client, run)
    assert saved["steps"] == [] and saved["run"]["model_calls"] == 0


def test_only_owner_instruction_selects_saved_work():
    assert parse_work_continue(ZH)["saved_work"]
    for text in [f"> {ASK}", f"Subject: notes\n{ASK}", f"“{ZH}”", "Continue the task from before?"]:
        assert parse_work_continue(text) is None

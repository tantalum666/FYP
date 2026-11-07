"""Ordinary Alice turns that change the goal of an existing Work run.

Scripted local conversation only. No provider call, live account, payment, or device.
"""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from desk.agent_run_schemas import RunAction, RunCreate
from desk.conversation_work import parse_changed_goal, parse_work_followup
from desk.assistant import TOOLS
from desk.app import create_app
from desk.store import DomainError
from desk.permissions import PermissionChange
from desk.sources import SourceInput
from desk.stream_contract import parse_sse
from desk.tasks import TaskInput
from desk.voice import VoiceConfig
from desk.voice_work import VoiceDraftFreeze

HEADERS = {"X-Desk-Request": "1"}
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "conversation-work" / "changed-goal.json"
UNSEEN = Path(__file__).resolve().parents[1] / "fixtures" / "conversation-work" / "unseen-variants.json"
FOLLOWUP = Path(__file__).resolve().parents[1] / "fixtures" / "conversation-work" / "follow-up.json"
ORIGINAL = "Compare fictional suppliers; quantity 36, budget 900 HKD."


def case(name):
    data = json.loads(FIXTURE.read_text())
    assert data["schema"] == "desk-conversation-work-fixture-v1"
    found = next(item for item in data["cases"] if item["id"] == name)
    return found


def phrase(name, **fields):
    item = case(name)
    return item["message"].format(**fields), item.get("language", "en")


def owner_client(app):
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture"},
            headers=HEADERS,
        ).status_code
        == 200
    )
    return client


def principal_of(client):
    token = client.cookies.get("desk_companion_session")
    return {"kind": "owner", "id": "owner", "name": "Owner", "session": token}


def send(
    client,
    message,
    *,
    key,
    task_id=None,
    conversation_id=None,
    language="en",
    voice_origin_ref=None,
    voice_steer=False,
    steer_run_id=None,
):
    body = {"message": message, "language": language}
    if task_id:
        body["task_id"] = task_id
    if conversation_id:
        body["conversation_id"] = conversation_id
    if voice_origin_ref:
        body["voice_origin_ref"] = voice_origin_ref
    if voice_steer:
        body["voice_steer"] = True
    if steer_run_id:
        body["steer_run_id"] = steer_run_id
    return client.post(
        "/api/assistant/messages",
        json=body,
        headers={**HEADERS, "X-Operation-Id": key},
    )


def counts(runtime):
    with runtime.store.connection() as conn:
        return {
            "runs": conn.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0],
            "jobs": conn.execute("SELECT COUNT(*) FROM computer_jobs").fetchone()[0],
            "proposals": conn.execute("SELECT COUNT(*) FROM assistant_proposals").fetchone()[0],
            "usage": conn.execute("SELECT COUNT(*) FROM text_ai_usage").fetchone()[0],
            "tasks": conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
        }


def steers(runtime, run_id):
    with runtime.store.connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM agent_events WHERE run_id=? AND kind='steer'",
            (run_id,),
        ).fetchone()[0]


def step_count(runtime, run_id):
    with runtime.store.connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM agent_steps WHERE run_id=?",
            (run_id,),
        ).fetchone()[0]


def follow_up_cases():
    data = json.loads(FOLLOWUP.read_text())
    assert data["schema"] == "desk-conversation-work-follow-up-v1"
    return data


def owner_conversation(runtime, principal):
    owner = hashlib.sha256(principal["session"].encode()).hexdigest()
    found = [
        entry for entry in runtime.voice.conversations.entries.values() if entry.owner == owner
    ]
    assert len(found) == 1
    return found[0]


def watch_advance(runtime):
    seen = []
    original = runtime.agent_runs.advance_one

    def wrapped(*args, **kwargs):
        seen.append(args)
        return original(*args, **kwargs)

    wrapped.original = original
    runtime.agent_runs.advance_one = wrapped
    return seen


def goal_of(runtime, principal, run_id):
    return runtime.agent_runs.detail(run_id, principal)["run"]


def reports(runtime, principal, run_id):
    session = hashlib.sha256(principal["session"].encode()).hexdigest()
    rows = runtime.artifacts.listing(session_hash=session, run_id=run_id)["artifacts"]
    return [row["id"] for row in rows if row.get("format") == "markdown"]


def verified_turns(runtime, conversation_id):
    entry = runtime.voice.conversations.entries[conversation_id]
    return [
        item
        for item in entry.items
        if "Report file verified:" in item["text"] or "报告文件已核验：" in item["text"]
    ]


def advance(runtime, run_id, principal, *, limit=20):
    for _ in range(limit):
        runtime.agent_runs.advance_one()
        current = goal_of(runtime, principal, run_id)
        if current["state"] in {"succeeded", "partial", "blocked", "failed"}:
            return current
    raise AssertionError(goal_of(runtime, principal, run_id)["state"])


def workspace(tmp_path, *, companion="separate"):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    client = owner_client(app)
    runtime = app.state.runtime
    principal = principal_of(client)
    session = hashlib.sha256(principal["session"].encode()).hexdigest()
    task = runtime.tasks.create(
        TaskInput(
            title="Supplier comparison",
            next_step="Keep the supplier note",
            follow_up_enabled=False,
        ),
        "fixture-task",
    )["task"]
    other_task = task
    if companion == "separate":
        other_task = runtime.tasks.create(
            TaskInput(title="Leave alone", follow_up_enabled=False),
            "other-task",
        )["task"]
    source = runtime.sources.ingest(
        SourceInput(name="requirements.csv", format="csv"),
        b"item,hours\nread,2\nwrite,3\n",
        "fixture-source",
        session_hash=session,
    )["source"]

    def start(goal, task_id, key, *, paused=False):
        return runtime.agent_runs.create(
            RunCreate(
                goal=goal,
                retain=True,
                task_ids=[task_id],
                source_ids=[source["id"]],
                scope_revision=runtime.agent_runs.scope(principal)["scope_revision"],
            ),
            key,
            principal,
            start_paused=paused,
        )["run"]

    run = start(ORIGINAL, task["id"], "fixture-work")
    other = None
    if companion in {"separate", "shared"}:
        # A paused companion is not the run advance_one will pick up.
        other = start(
            "Leave this work alone",
            other_task["id"],
            "other-work",
            paused=companion == "separate",
        )
    return {
        "app": app,
        "client": client,
        "runtime": runtime,
        "principal": principal,
        "task": task,
        "run": goal_of(runtime, principal, run["id"]),
        "other": other,
    }


@pytest.fixture
def box(tmp_path):
    built = workspace(tmp_path, companion="separate")
    runtime, principal = built["runtime"], built["principal"]
    started = runtime.agent_runs.advance_one()
    assert started is True
    current = goal_of(runtime, principal, built["run"]["id"])
    assert current["state"] not in {"succeeded", "partial", "failed", "cancelled"}
    built["run"] = current
    built["executed"] = []
    original = runtime.jobs.applications.execute

    def forbidden(*args, **kwargs):
        built["executed"].append("execute")
        raise AssertionError("application executor ran during conversation admission")

    runtime.jobs.applications.execute = forbidden
    built["restore_execute"] = lambda: setattr(runtime.jobs.applications, "execute", original)
    return built


def test_fixture_covers_the_changed_goal_cases():
    data = json.loads(FIXTURE.read_text())
    assert {item["id"] for item in data["cases"]} >= {
        "ordinary-turn",
        "mid-flow-change",
        "explicit-change",
        "interrupt-before-commit",
        "unknown-after-commit",
        "stream-change",
    }


def test_mid_flow_change_admits_into_the_same_work_and_keeps_going(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    before = counts(runtime)
    ordinary, _ = phrase("ordinary-turn")
    first = send(client, ordinary, key="ordinary", task_id=task_id)
    assert first.status_code == 200, first.text
    assert first.json().get("admitted") is not True
    assert goal_of(runtime, principal, run_id)["goal"] == ORIGINAL
    assert box["task"]["next_step"] == runtime.tasks.detail(task_id)["task"]["next_step"]
    same, _ = phrase("unchanged", goal=ORIGINAL)
    untouched = send(client, same, key="unchanged", task_id=task_id)
    assert untouched.status_code == 200, untouched.text
    assert untouched.json()["admitted"] is False
    assert steers(runtime, run_id) == 0
    change, _ = phrase("mid-flow-change")
    calls = []

    def generate(*args, **kwargs):
        calls.append(args)
        raise AssertionError("provider called")

    runtime.text_ai.config.provider = "fake"
    runtime.text_ai.generate = generate
    admitted = send(
        client,
        change,
        key="change",
        task_id=task_id,
        conversation_id=first.json()["conversation_id"],
    )
    assert admitted.status_code == 200, admitted.text
    body = admitted.json()
    assert body["admitted"] is True and body["recovered"] is False
    assert body["saved"] is False
    assert body["work_run_id"] == run_id
    assert body["goal"] == "quantity 48, budget 950 HKD."
    assert body["plan_revision"] == 2
    assert "Nothing was sent or bought." in body["message"]
    assert body["result"]["verified"] is True
    assert body["result"]["verification"] == "byte_readback"
    assert body["result"]["goal"] == body["goal"]
    assert f"Report file verified: Goal: {body['goal']}" in body["message"]
    assert ORIGINAL not in body["message"]
    shown = verified_turns(runtime, body["conversation_id"])
    assert len(shown) == 1
    assert calls == [] and box["executed"] == []
    after = counts(runtime)
    assert after["runs"] == before["runs"]
    assert after["jobs"] == before["jobs"]
    assert after["tasks"] == before["tasks"]
    assert after["usage"] == 0
    assert after["proposals"] == before["proposals"] + 1
    current = goal_of(runtime, principal, run_id)
    assert current["goal"] == body["goal"] and current["model_calls"] == 0
    assert steers(runtime, run_id) == 1
    other = goal_of(runtime, principal, box["other"]["id"])
    assert other["goal"] == "Leave this work alone" and other["plan_revision"] == 1
    box["restore_execute"]()
    finished = advance(runtime, run_id, principal)
    assert finished["state"] == "succeeded"
    assert finished["goal"] == body["goal"]
    assert finished["model_calls"] == 0 and finished["reads"] == 2
    published = reports(runtime, principal, run_id)
    again = send(
        client,
        change,
        key="change",
        task_id=task_id,
        conversation_id=body["conversation_id"],
    )
    assert again.status_code == 200, again.text
    assert again.json()["work_run_id"] == run_id
    assert again.json()["result"]["artifact_id"] == body["result"]["artifact_id"]
    assert steers(runtime, run_id) == 1
    assert reports(runtime, principal, run_id) == published
    assert len(verified_turns(runtime, body["conversation_id"])) == 1
    names = {tool["name"] for tool in TOOLS}
    assert {"steer", "approve", "work_goal"}.isdisjoint(names)


def test_ambiguous_explicit_unchanged_and_draft_phrases(tmp_path):
    box = workspace(tmp_path, companion="shared")
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    task_id = box["task"]["id"]
    first, second = box["run"], box["other"]
    change, _ = phrase("mid-flow-change")
    ambiguous = send(client, change, key="ambiguous", task_id=task_id)
    assert ambiguous.status_code == 200, ambiguous.text
    assert ambiguous.json()["admitted"] is False
    assert "Name the work" in ambiguous.json()["message"]
    assert goal_of(runtime, principal, first["id"])["goal"] == ORIGINAL
    assert goal_of(runtime, principal, second["id"])["goal"] == "Leave this work alone"
    explicit, _ = phrase("explicit-change", run_id=second["id"])
    chosen = send(client, explicit, key="explicit", task_id=task_id)
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["work_run_id"] == second["id"]
    assert chosen.json()["result"]["goal"] == "Keep only the Birch quote."
    assert goal_of(runtime, principal, second["id"])["goal"] == "Keep only the Birch quote."
    assert goal_of(runtime, principal, second["id"])["reads"] > 0
    assert goal_of(runtime, principal, first["id"])["goal"] == ORIGINAL
    assert goal_of(runtime, principal, first["id"])["reads"] == 0
    assert steers(runtime, second["id"]) == 1
    bare, _ = phrase("bare-prefix")
    assert send(client, bare, key="bare", task_id=task_id).json().get("admitted") is not True
    assert goal_of(runtime, principal, first["id"])["goal"] == ORIGINAL
    draft, _ = phrase("new-goal-draft")
    drafted = send(client, draft, key="draft-goal")
    assert drafted.status_code == 200, drafted.text
    assert drafted.json().get("admitted") is not True
    assert drafted.json()["kind"] == "draft"
    assert counts(runtime)["runs"] == 2
    third = runtime.tasks.create(
        TaskInput(title="Other task", follow_up_enabled=False),
        "third-task",
    )["task"]
    wrong = send(
        client,
        f"Change work {first['id']}: A different task's work",
        key="wrong-task",
        task_id=third["id"],
    )
    assert wrong.status_code == 200, wrong.text
    assert wrong.json()["admitted"] is False
    assert goal_of(runtime, principal, first["id"])["goal"] == ORIGINAL
    missing = send(client, "Change work " + "ab" * 16 + ": Nowhere", key="missing")
    assert missing.status_code == 200, missing.text
    assert missing.json()["admitted"] is False
    chinese, language = phrase("chinese-change")
    # The first run is still the only unchanged one on the original task.
    revised = send(client, chinese, key="zh", task_id=task_id, language=language)
    assert revised.status_code == 200, revised.text
    assert revised.json()["admitted"] is True
    assert revised.json()["goal"] == "数量改为48，预算950港元。"
    assert "没有发送或购买" in revised.json()["message"]
    assert goal_of(runtime, principal, second["id"])["goal"] == "Keep only the Birch quote."


def test_interruption_before_commit_is_not_success_and_retries_once(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    message, _ = phrase("interrupt-before-commit")
    runtime.conversation_work.offline_interrupt = "before_commit"
    refused = send(client, message, key="interrupt", task_id=task_id)
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "CONVERSATION_WORK_INTERRUPTED"
    assert "admitted" not in refused.json()
    assert goal_of(runtime, principal, run_id)["goal"] == ORIGINAL
    assert steers(runtime, run_id) == 0
    runtime.conversation_work.offline_interrupt = None
    admitted = send(client, message, key="interrupt", task_id=task_id)
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["admitted"] is True and admitted.json()["recovered"] is False
    assert steers(runtime, run_id) == 1
    assert goal_of(runtime, principal, run_id)["plan_revision"] == 2


def test_unknown_result_recovers_without_a_second_steer(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    message, _ = phrase("unknown-after-commit")
    runtime.conversation_work.offline_interrupt = "after_commit"
    unknown = send(client, message, key="unknown", task_id=task_id)
    assert unknown.status_code == 409, unknown.text
    assert unknown.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_UNKNOWN"
    assert goal_of(runtime, principal, run_id)["goal"] == "quantity 48, budget 950 HKD."
    assert steers(runtime, run_id) == 1
    conflict, _ = phrase("unknown-conflict")
    refused = send(client, conflict, key="unknown", task_id=task_id)
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    assert steers(runtime, run_id) == 1
    recovered = send(client, message, key="unknown", task_id=task_id)
    assert recovered.status_code == 200, recovered.text
    body = recovered.json()
    assert body["admitted"] is True and body["recovered"] is True
    assert body["plan_revision"] == 2
    assert steers(runtime, run_id) == 1
    cached = send(client, message, key="unknown", task_id=task_id)
    assert cached.status_code == 200, cached.text
    assert cached.json()["recovered"] is True
    assert steers(runtime, run_id) == 1
    later, _ = phrase("interrupt-before-commit")
    blocked = send(client, later, key="second-change", task_id=task_id)
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["admitted"] is False
    assert goal_of(runtime, principal, run_id)["goal"] == "quantity 48, budget 950 HKD."
    assert steers(runtime, run_id) == 1


def test_stream_close_is_not_the_success_receipt(box):
    client, runtime, principal = box["client"], box["runtime"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    message, _ = phrase("stream-change")
    headers = {**HEADERS, "X-Operation-Id": "stream-goal"}
    body = {"message": message, "task_id": task_id}
    with client.stream("POST", "/api/assistant/messages/stream", json=body, headers=headers) as first:
        assert first.status_code == 200
        chunk = next(first.iter_bytes())
        assert chunk
        with pytest.raises(json.JSONDecodeError):
            json.loads(chunk)
    recovered = client.post("/api/assistant/messages/stream", json=body, headers=headers)
    assert recovered.status_code == 200, recovered.text
    assert recovered.headers["content-type"].startswith("text/event-stream")
    with pytest.raises(json.JSONDecodeError):
        json.loads(recovered.text)
    events = parse_sse(recovered.text)
    assert events[-1]["type"] == "done"
    assert events[-1]["reply"]["admitted"] is True
    assert events[-1]["reply"]["work_run_id"] == run_id
    assert steers(runtime, run_id) == 1
    repeated = client.post("/api/assistant/messages/stream", json=body, headers=headers)
    assert repeated.status_code == 200, repeated.text
    assert steers(runtime, run_id) == 1
    assert goal_of(runtime, principal, run_id)["plan_revision"] == 2


def test_cancelled_work_and_paired_device_do_not_change_the_goal(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id = box["run"]["id"]
    current = goal_of(runtime, principal, run_id)
    runtime.agent_runs.action(
        run_id,
        RunAction(action="cancel", expected_version=current["version"]),
        "cancel-work",
        principal,
    )
    message, _ = phrase("mid-flow-change")
    refused = send(client, message, key="cancelled", task_id=box["task"]["id"])
    assert refused.status_code == 200, refused.text
    assert refused.json()["admitted"] is False
    assert goal_of(runtime, principal, run_id)["goal"] == ORIGINAL
    assert steers(runtime, run_id) == 0
    assert (
        client.post(
            "/api/devices/enrol-display",
            json={"name": "Fixture screen"},
            headers={**HEADERS, "X-Operation-Id": "enrol"},
        ).status_code
        == 200
    )
    paired = TestClient(box["app"])
    paired.headers.update(
        {**HEADERS, "Authorization": "Bearer " + client.cookies.get("desk_companion_device")}
    )
    denied = paired.post(
        "/api/assistant/messages",
        json={"message": f"Change work {run_id}: Paired device edit"},
        headers={**HEADERS, "X-Operation-Id": "paired"},
    )
    assert denied.status_code == 403, denied.text
    assert goal_of(runtime, principal, run_id)["goal"] == ORIGINAL


def test_full_access_does_not_turn_the_goal_change_into_a_job(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    policy = runtime.permissions.snapshot()
    runtime.permissions.change(
        PermissionChange(mode="full", expected_version=policy["version"]),
        "full-access",
    )
    before = counts(runtime)
    message, _ = phrase("mid-flow-change")
    admitted = send(client, message, key="full", task_id=box["task"]["id"])
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["admitted"] is True
    assert admitted.json()["result"]["verified"] is True
    assert admitted.json()["result"]["goal"] == "quantity 48, budget 950 HKD."
    assert admitted.json().get("proposal") is None
    assert admitted.json().get("job") is None
    after = counts(runtime)
    assert after["jobs"] == before["jobs"] and after["proposals"] == before["proposals"]
    assert runtime.tasks.detail(box["task"]["id"])["task"]["next_step"] == "Keep the supplier note"
    assert goal_of(runtime, principal, box["other"]["id"])["goal"] == "Leave this work alone"
    assert goal_of(runtime, principal, box["run"]["id"])["model_calls"] == 0


def unseen_cases():
    data = json.loads(UNSEEN.read_text())
    assert data["schema"] == "desk-conversation-work-unseen-v1"
    return data["cases"]


def test_unseen_fixture_is_outside_the_changed_goal_fixture():
    original = {item["message"] for item in json.loads(FIXTURE.read_text())["cases"]}
    cases = unseen_cases()
    assert {item["message"] for item in cases}.isdisjoint(original)
    assert {item["expect"] for item in cases} == {"steer", "no_steer"}
    assert any(item["language"] == "zh" for item in cases if "language" in item)
    assert any(item["expect"] == "no_steer" and item.get("draft") for item in cases)
    assert any(item["expect"] == "no_steer" and item.get("runs") == 2 for item in cases)


@pytest.mark.parametrize("item", unseen_cases(), ids=lambda item: item["id"])
def test_unseen_variant_steers_only_an_explicit_owner_line(item, tmp_path):
    shared = item.get("runs") == 2
    box = workspace(tmp_path, companion="shared" if shared else "separate")
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    current, other = box["run"], box["other"]
    target = other if item.get("target") == "other" else current
    message = item["message"].format(run_id=target["id"])
    language = item.get("language", "en")
    before = counts(runtime)
    response = send(
        client, message, key=item["id"], task_id=box["task"]["id"], language=language
    )
    assert response.status_code == 200, response.text
    body = response.json()
    if item.get("says"):
        assert item["says"] in body["message"]
    if item["expect"] == "steer":
        assert body["admitted"] is True and body["recovered"] is False
        assert body["goal"] == item["goal"]
        assert body["work_run_id"] == target["id"]
        saved = goal_of(runtime, principal, target["id"])
        assert saved["goal"] == item["goal"] and saved["plan_revision"] == 2
        assert steers(runtime, target["id"]) == 1
        if item.get("absent"):
            assert item["absent"] not in saved["goal"]
        untouched = current if target["id"] == other["id"] else other
        assert goal_of(runtime, principal, untouched["id"])["goal"] == untouched["goal"]
        assert steers(runtime, untouched["id"]) == 0
    else:
        assert body.get("admitted") is not True
        assert goal_of(runtime, principal, current["id"])["goal"] == current["goal"]
        assert goal_of(runtime, principal, other["id"])["goal"] == other["goal"]
        assert steers(runtime, current["id"]) == 0
        assert steers(runtime, other["id"]) == 0
        if item.get("draft"):
            assert body["kind"] == "draft"
    after = counts(runtime)
    assert after["runs"] == before["runs"]
    assert after["jobs"] == before["jobs"]
    assert after["tasks"] == before["tasks"]
    assert after["usage"] == 0
    assert runtime.tasks.detail(box["task"]["id"])["task"]["next_step"] == "Keep the supplier note"


def review_snapshots(box, texts):
    runtime = box["runtime"]
    runtime.voice.config = VoiceConfig(
        provider="gemini", endpoint="", model="protocol-fixture", api_key="fake-only"
    )
    ledger = runtime.voice.work
    session = ledger.begin(box["principal"])
    assert session
    drafts = []
    for index, text in enumerate(texts, start=1):
        event = ledger.observe(
            session,
            {
                "type": "transcript",
                "role": "user",
                "text": text,
                "input_key": f"snap-{index}",
                "input_sequence": index,
                "boundary": "provider_final",
                "input_operation": "replace",
            },
        )
        assert event and event["eligible"] and event["text"] == text
        draft = ledger.freeze(
            VoiceDraftFreeze(
                voice_session_ref=session,
                input_segment_id=event["input_segment_id"],
                expected_revision=event["revision"],
            ),
            box["principal"],
        )
        assert draft["snapshot_kind"] == "owner_snapshot" and draft["text"] == text
        drafts.append(draft)
    return drafts


def test_voice_snapshot_interrupt_retries_once(box):
    text = "Change the goal: keep only Birch."
    draft = review_snapshots(box, [text])[0]
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    ref = draft["voice_origin_ref"]
    forged = send(
        client,
        text,
        key="forged",
        task_id=task_id,
        voice_origin_ref="ab" * 16,
    )
    assert forged.status_code == 410, forged.text
    assert forged.json()["error"]["code"] == "VOICE_DRAFT_EXPIRED"
    mismatch = send(
        client,
        "Change the goal: quantity 70 only.",
        key="mismatch",
        task_id=task_id,
        voice_origin_ref=ref,
    )
    assert mismatch.status_code == 409, mismatch.text
    assert mismatch.json()["error"]["code"] == "VOICE_INPUT_CHANGED"
    assert goal_of(runtime, principal, run_id)["goal"] == ORIGINAL
    assert steers(runtime, run_id) == 0
    runtime.conversation_work.offline_interrupt = "before_commit"
    refused = send(client, text, key="voice-interrupt", task_id=task_id, voice_origin_ref=ref)
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "CONVERSATION_WORK_INTERRUPTED"
    assert goal_of(runtime, principal, run_id)["goal"] == ORIGINAL
    assert steers(runtime, run_id) == 0
    runtime.conversation_work.offline_interrupt = None
    before = counts(runtime)
    calls = []

    def generate(*args, **kwargs):
        calls.append(args)
        raise AssertionError("provider called")

    runtime.text_ai.generate = generate
    admitted = send(client, text, key="voice-interrupt", task_id=task_id, voice_origin_ref=ref)
    assert admitted.status_code == 200, admitted.text
    body = admitted.json()
    assert body["admitted"] is True and body["recovered"] is False
    assert body["work_run_id"] == run_id and body["goal"] == "keep only Birch."
    assert calls == [] and box["executed"] == []
    after = counts(runtime)
    assert after["runs"] == before["runs"] and after["jobs"] == before["jobs"]
    assert after["tasks"] == before["tasks"] and after["usage"] == 0
    assert after["proposals"] == before["proposals"]
    assert steers(runtime, run_id) == 1
    again = send(client, text, key="voice-interrupt", task_id=task_id, voice_origin_ref=ref)
    assert again.status_code == 200, again.text
    assert again.json()["work_run_id"] == run_id
    assert steers(runtime, run_id) == 1
    assert goal_of(runtime, principal, box["other"]["id"])["goal"] == "Leave this work alone"


def test_voice_snapshot_unknown_result_recovers_without_a_second_steer(box):
    text = "Change the goal: quantity 60 only."
    draft = review_snapshots(box, [text])[0]
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    ref = draft["voice_origin_ref"]
    runtime.conversation_work.offline_interrupt = "after_commit"
    unknown = send(client, text, key="voice-unknown", task_id=task_id, voice_origin_ref=ref)
    assert unknown.status_code == 409, unknown.text
    assert unknown.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_UNKNOWN"
    assert goal_of(runtime, principal, run_id)["goal"] == "quantity 60 only."
    assert steers(runtime, run_id) == 1
    runtime.conversation_work.offline_interrupt = None
    changed = send(
        client,
        "Change the goal: quantity 70 only.",
        key="voice-unknown",
        task_id=task_id,
        voice_origin_ref=ref,
    )
    assert changed.status_code == 409, changed.text
    assert changed.json()["error"]["code"] == "VOICE_INPUT_CHANGED"
    assert steers(runtime, run_id) == 1
    runtime.voice.work.drafts.pop(ref)
    conflict = send(
        client,
        "Change the goal: quantity 70 only.",
        key="voice-unknown",
        task_id=task_id,
        voice_origin_ref=ref,
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    assert steers(runtime, run_id) == 1
    recovered = send(client, text, key="voice-unknown", task_id=task_id, voice_origin_ref=ref)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["admitted"] is True and recovered.json()["recovered"] is True
    assert steers(runtime, run_id) == 1
    cached = send(client, text, key="voice-unknown", task_id=task_id, voice_origin_ref=ref)
    assert cached.status_code == 200, cached.text
    assert cached.json()["recovered"] is True
    assert steers(runtime, run_id) == 1
    blocked = send(
        client,
        "Change the goal: quantity 80 only.",
        key="voice-later",
        task_id=task_id,
    )
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["admitted"] is False
    assert goal_of(runtime, principal, run_id)["goal"] == "quantity 60 only."
    assert steers(runtime, run_id) == 1


def test_voice_snapshot_stream_close_is_not_the_success_receipt(box):
    text = "Change the goal: keep the Cedar note."
    draft = review_snapshots(box, [text])[0]
    client, runtime, principal = box["client"], box["runtime"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    headers = {**HEADERS, "X-Operation-Id": "voice-stream"}
    body = {"message": text, "task_id": task_id, "voice_origin_ref": draft["voice_origin_ref"]}
    with client.stream("POST", "/api/assistant/messages/stream", json=body, headers=headers) as first:
        assert first.status_code == 200
        chunk = next(first.iter_bytes())
        assert chunk
        with pytest.raises(json.JSONDecodeError):
            json.loads(chunk)
    recovered = client.post("/api/assistant/messages/stream", json=body, headers=headers)
    assert recovered.status_code == 200, recovered.text
    assert recovered.headers["content-type"].startswith("text/event-stream")
    with pytest.raises(json.JSONDecodeError):
        json.loads(recovered.text)
    events = parse_sse(recovered.text)
    assert events[-1]["type"] == "done"
    assert events[-1]["reply"]["admitted"] is True
    assert events[-1]["reply"]["work_run_id"] == run_id
    assert events[-1]["reply"]["goal"] == "keep the Cedar note."
    assert steers(runtime, run_id) == 1
    repeated = client.post("/api/assistant/messages/stream", json=body, headers=headers)
    assert repeated.status_code == 200, repeated.text
    assert steers(runtime, run_id) == 1
    assert goal_of(runtime, principal, run_id)["plan_revision"] == 2


def test_voice_snapshot_near_miss_does_not_steer_and_chinese_uses_the_same_turn(box):
    quote = "> Change the goal: keep only Birch."
    draft_goal = "Goal: write the unseen voice note"
    question = "What is the goal of this work?"
    chinese = "调整目标：只保留白桦报价。"
    drafts = review_snapshots(box, [quote, draft_goal, question, chinese])
    runtime, client = box["runtime"], box["client"]
    task_id = box["task"]["id"]
    before = counts(runtime)

    def snap(text, draft, key, language="en"):
        return send(
            client,
            text,
            key=key,
            task_id=task_id,
            language=language,
            voice_origin_ref=draft["voice_origin_ref"],
        )

    quoted = snap(quote, drafts[0], "voice-quote")
    assert quoted.status_code == 200, quoted.text
    assert quoted.json()["admitted"] is False
    assert quoted.json()["kind"] == "clarify"
    assert "does not change this work" in quoted.json()["message"]
    drafted = snap(draft_goal, drafts[1], "voice-draft")
    assert drafted.status_code == 200, drafted.text
    assert drafted.json()["kind"] == "clarify"
    assert drafted.json().get("admitted") is not True
    asked = snap(question, drafts[2], "voice-question")
    assert asked.status_code == 200, asked.text
    assert asked.json().get("admitted") is not True
    assert counts(runtime) == before
    assert steers(runtime, box["run"]["id"]) == 0
    admitted = snap(chinese, drafts[3], "voice-zh", "zh")
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["admitted"] is True
    assert admitted.json()["goal"] == "只保留白桦报价。"
    assert "没有发送或购买" in admitted.json()["message"]
    assert steers(runtime, box["run"]["id"]) == 1
    assert counts(runtime)["runs"] == before["runs"]
    assert counts(runtime)["jobs"] == before["jobs"]
    assert counts(runtime)["proposals"] == before["proposals"]


def test_voice_snapshot_ambiguous_without_a_run_id_does_not_steer(tmp_path):
    box = workspace(tmp_path, companion="shared")
    text = "Change the goal: keep only Birch."
    draft = review_snapshots(box, [text])[0]
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    response = send(
        client,
        text,
        key="voice-ambiguous",
        task_id=box["task"]["id"],
        voice_origin_ref=draft["voice_origin_ref"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["admitted"] is False
    assert "Name the work" in response.json()["message"]
    assert goal_of(runtime, principal, box["run"]["id"])["goal"] == ORIGINAL
    assert goal_of(runtime, principal, box["other"]["id"])["goal"] == "Leave this work alone"
    assert steers(runtime, box["run"]["id"]) == 0
    assert steers(runtime, box["other"]["id"]) == 0


def test_voice_snapshot_paired_device_is_refused_and_full_access_creates_no_job(box):
    text = "Change the goal: keep only Birch."
    draft = review_snapshots(box, [text])[0]
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id = box["run"]["id"]
    assert (
        client.post(
            "/api/devices/enrol-display",
            json={"name": "Fixture screen"},
            headers={**HEADERS, "X-Operation-Id": "enrol-voice"},
        ).status_code
        == 200
    )
    paired = TestClient(box["app"])
    paired.headers.update(
        {**HEADERS, "Authorization": "Bearer " + client.cookies.get("desk_companion_device")}
    )
    denied = paired.post(
        "/api/assistant/messages",
        json={
            "message": text,
            "voice_origin_ref": draft["voice_origin_ref"],
            "task_id": box["task"]["id"],
        },
        headers={**HEADERS, "X-Operation-Id": "paired-voice"},
    )
    assert denied.status_code == 403, denied.text
    assert goal_of(runtime, principal, run_id)["goal"] == ORIGINAL
    policy = runtime.permissions.snapshot()
    runtime.permissions.change(
        PermissionChange(mode="full", expected_version=policy["version"]),
        "full-voice",
    )
    before = counts(runtime)
    admitted = send(
        client,
        text,
        key="full-voice",
        task_id=box["task"]["id"],
        voice_origin_ref=draft["voice_origin_ref"],
    )
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["admitted"] is True
    assert admitted.json().get("proposal") is None
    assert admitted.json().get("job") is None
    after = counts(runtime)
    assert after["jobs"] == before["jobs"] and after["proposals"] == before["proposals"]
    assert runtime.tasks.detail(box["task"]["id"])["task"]["next_step"] == "Keep the supplier note"
    assert steers(runtime, run_id) == 1


def test_review_screen_one_current_run_is_the_steer_target(box):
    text = "Keep only Birch."
    draft = review_snapshots(box, [text])[0]
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    ref = draft["voice_origin_ref"]
    calls = []

    def generate(*args, **kwargs):
        calls.append(args)
        raise AssertionError("provider called")

    runtime.text_ai.generate = generate
    plain = send(client, text, key="plain-snapshot", task_id=task_id, voice_origin_ref=ref)
    assert plain.status_code == 200, plain.text
    assert plain.json()["admitted"] is False
    assert goal_of(runtime, principal, run_id)["goal"] == ORIGINAL
    assert steers(runtime, run_id) == 0
    missing = client.post(
        "/api/assistant/messages",
        json={"message": text, "voice_steer": True, "task_id": task_id},
        headers={**HEADERS, "X-Operation-Id": "steer-without-snapshot"},
    )
    assert missing.status_code == 422, missing.text
    assert missing.json()["error"]["code"] == "VOICE_STEER_REQUIRES_SNAPSHOT"
    numeric = client.post(
        "/api/assistant/messages",
        json={"message": text, "voice_steer": 1, "voice_origin_ref": ref, "task_id": task_id},
        headers={**HEADERS, "X-Operation-Id": "steer-numeric"},
    )
    assert numeric.status_code == 422, numeric.text
    assert numeric.json()["error"]["code"] == "VALIDATION_FAILED"
    before = counts(runtime)
    admitted = send(
        client,
        text,
        key="review-one",
        task_id=task_id,
        voice_origin_ref=ref,
        voice_steer=True,
    )
    assert admitted.status_code == 200, admitted.text
    body = admitted.json()
    assert body["admitted"] is True and body["recovered"] is False
    assert body["work_run_id"] == run_id and body["goal"] == text
    assert "Nothing was sent or bought" in body["message"]
    assert calls == [] and box["executed"] == []
    after = counts(runtime)
    assert after["runs"] == before["runs"] and after["jobs"] == before["jobs"]
    assert after["tasks"] == before["tasks"] and after["proposals"] == before["proposals"]
    assert after["usage"] == 0
    assert steers(runtime, run_id) == 1
    assert goal_of(runtime, principal, box["other"]["id"])["goal"] == "Leave this work alone"
    wrong = send(
        client,
        text,
        key="review-other-task",
        task_id=task_id,
        voice_origin_ref=ref,
        voice_steer=True,
        steer_run_id=box["other"]["id"],
    )
    assert wrong.status_code == 200, wrong.text
    assert wrong.json()["admitted"] is False
    assert "not on this task" in wrong.json()["message"]
    assert steers(runtime, box["other"]["id"]) == 0
    again = send(
        client,
        text,
        key="review-one",
        task_id=task_id,
        voice_origin_ref=ref,
        voice_steer=True,
    )
    assert again.status_code == 200, again.text
    assert again.json()["admitted"] is True
    assert again.json()["work_run_id"] == run_id
    assert steers(runtime, run_id) == 1
    assert counts(runtime)["runs"] == before["runs"]


def test_review_screen_one_run_without_a_task_is_clear(box):
    text = "Keep the only open note."
    draft = review_snapshots(box, [text])[0]
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    other = goal_of(runtime, principal, box["other"]["id"])
    runtime.agent_runs.action(
        other["id"],
        RunAction(action="cancel", expected_version=other["version"]),
        "cancel-companion",
        principal,
    )
    admitted = send(
        client,
        text,
        key="review-sole",
        voice_origin_ref=draft["voice_origin_ref"],
        voice_steer=True,
    )
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["admitted"] is True
    assert admitted.json()["work_run_id"] == box["run"]["id"]
    assert admitted.json()["goal"] == text
    assert steers(runtime, box["run"]["id"]) == 1
    assert steers(runtime, box["other"]["id"]) == 0


def test_review_screen_several_current_runs_require_an_explicit_choice(tmp_path):
    box = workspace(tmp_path, companion="shared")
    text = "Keep the shared Birch note."
    draft = review_snapshots(box, [text])[0]
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    ref = draft["voice_origin_ref"]
    before = counts(runtime)
    ambiguous = send(
        client,
        text,
        key="review-several",
        task_id=box["task"]["id"],
        voice_origin_ref=ref,
        voice_steer=True,
    )
    assert ambiguous.status_code == 200, ambiguous.text
    assert ambiguous.json()["admitted"] is False
    assert "Name the work" in ambiguous.json()["message"]
    assert steers(runtime, box["run"]["id"]) == 0
    assert steers(runtime, box["other"]["id"]) == 0
    assert counts(runtime)["runs"] == before["runs"]
    chosen = send(
        client,
        text,
        key="review-chosen",
        task_id=box["task"]["id"],
        voice_origin_ref=ref,
        voice_steer=True,
        steer_run_id=box["other"]["id"],
    )
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["admitted"] is True
    assert chosen.json()["work_run_id"] == box["other"]["id"]
    assert chosen.json()["goal"] == text
    assert goal_of(runtime, principal, box["run"]["id"])["goal"] == ORIGINAL
    assert goal_of(runtime, principal, box["other"]["id"])["goal"] == text
    assert steers(runtime, box["run"]["id"]) == 0
    assert steers(runtime, box["other"]["id"]) == 1
    assert counts(runtime)["runs"] == before["runs"]
    assert counts(runtime)["jobs"] == before["jobs"]
    assert counts(runtime)["proposals"] == before["proposals"]


def test_review_screen_without_current_work_does_not_create_a_run(box):
    text = "Keep a note that has no current work."
    draft = review_snapshots(box, [text])[0]
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    empty = runtime.tasks.create(
        TaskInput(title="No work yet", follow_up_enabled=False),
        "empty-task",
    )["task"]
    before = counts(runtime)
    missing = send(
        client,
        text,
        key="review-empty-task",
        task_id=empty["id"],
        voice_origin_ref=draft["voice_origin_ref"],
        voice_steer=True,
    )
    assert missing.status_code == 200, missing.text
    assert missing.json()["admitted"] is False
    assert "No current work" in missing.json()["message"]
    assert counts(runtime) == before
    for run, key in ((box["run"], "cancel-main"), (box["other"], "cancel-companion")):
        current = goal_of(runtime, principal, run["id"])
        runtime.agent_runs.action(
            run["id"],
            RunAction(action="cancel", expected_version=current["version"]),
            key,
            principal,
        )
    response = send(
        client,
        text,
        key="review-none",
        task_id=box["task"]["id"],
        voice_origin_ref=draft["voice_origin_ref"],
        voice_steer=True,
    )
    assert response.status_code == 200, response.text
    assert response.json()["admitted"] is False
    assert "cannot take another goal change" in response.json()["message"]
    assert counts(runtime) == before
    assert steers(runtime, box["run"]["id"]) == 0


def test_review_screen_steer_keeps_interruption_and_receipt_recovery(box):
    text = "Keep only the Cedar note."
    later = "Keep the later Cedar note."
    draft, second = review_snapshots(box, [text, later])
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    ref = draft["voice_origin_ref"]
    runtime.conversation_work.offline_interrupt = "before_commit"
    refused = send(
        client, text, key="review-interrupt", task_id=task_id, voice_origin_ref=ref, voice_steer=True
    )
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "CONVERSATION_WORK_INTERRUPTED"
    assert goal_of(runtime, principal, run_id)["goal"] == ORIGINAL
    assert steers(runtime, run_id) == 0
    runtime.conversation_work.offline_interrupt = None
    admitted = send(
        client, text, key="review-interrupt", task_id=task_id, voice_origin_ref=ref, voice_steer=True
    )
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["admitted"] is True and admitted.json()["recovered"] is False
    assert steers(runtime, run_id) == 1
    runtime.conversation_work.offline_interrupt = "after_commit"
    mismatched = send(
        client,
        later,
        key="review-unknown",
        voice_origin_ref=ref,
        voice_steer=True,
        steer_run_id=box["other"]["id"],
    )
    assert mismatched.status_code == 409, mismatched.text
    assert mismatched.json()["error"]["code"] == "VOICE_INPUT_CHANGED"
    assert steers(runtime, box["other"]["id"]) == 0
    unknown = send(
        client,
        later,
        key="review-unknown",
        voice_origin_ref=second["voice_origin_ref"],
        voice_steer=True,
        steer_run_id=box["other"]["id"],
    )
    assert unknown.status_code == 409, unknown.text
    assert unknown.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_UNKNOWN"
    assert goal_of(runtime, principal, box["other"]["id"])["goal"] == later
    assert steers(runtime, box["other"]["id"]) == 1
    runtime.conversation_work.offline_interrupt = None
    changed = send(
        client,
        "Keep a different Cedar note.",
        key="review-unknown",
        voice_origin_ref=second["voice_origin_ref"],
        voice_steer=True,
        steer_run_id=box["other"]["id"],
    )
    assert changed.status_code == 409, changed.text
    assert changed.json()["error"]["code"] == "VOICE_INPUT_CHANGED"
    runtime.voice.work.drafts.pop(second["voice_origin_ref"])
    conflict = send(
        client,
        "Keep a different Cedar note.",
        key="review-unknown",
        voice_origin_ref=second["voice_origin_ref"],
        voice_steer=True,
        steer_run_id=box["other"]["id"],
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    assert steers(runtime, box["other"]["id"]) == 1
    recovered = send(
        client,
        later,
        key="review-unknown",
        voice_origin_ref=second["voice_origin_ref"],
        voice_steer=True,
        steer_run_id=box["other"]["id"],
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["admitted"] is True and recovered.json()["recovered"] is True
    assert recovered.json()["work_run_id"] == box["other"]["id"]
    assert steers(runtime, box["other"]["id"]) == 1
    assert steers(runtime, run_id) == 1


def test_review_screen_stream_close_is_not_the_success_receipt(box):
    text = "Keep the streamed Cedar note."
    draft = review_snapshots(box, [text])[0]
    client, runtime, principal = box["client"], box["runtime"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    headers = {**HEADERS, "X-Operation-Id": "review-stream"}
    body = {
        "message": text,
        "task_id": task_id,
        "voice_origin_ref": draft["voice_origin_ref"],
        "voice_steer": True,
    }
    with client.stream("POST", "/api/assistant/messages/stream", json=body, headers=headers) as first:
        assert first.status_code == 200
        chunk = next(first.iter_bytes())
        assert chunk
        with pytest.raises(json.JSONDecodeError):
            json.loads(chunk)
    recovered = client.post("/api/assistant/messages/stream", json=body, headers=headers)
    assert recovered.status_code == 200, recovered.text
    assert recovered.headers["content-type"].startswith("text/event-stream")
    with pytest.raises(json.JSONDecodeError):
        json.loads(recovered.text)
    events = parse_sse(recovered.text)
    assert events[-1]["type"] == "done"
    assert events[-1]["reply"]["admitted"] is True
    assert events[-1]["reply"]["work_run_id"] == run_id
    assert events[-1]["reply"]["goal"] == text
    assert steers(runtime, run_id) == 1
    repeated = client.post("/api/assistant/messages/stream", json=body, headers=headers)
    assert repeated.status_code == 200, repeated.text
    assert steers(runtime, run_id) == 1
    assert goal_of(runtime, principal, run_id)["plan_revision"] == 2


def test_review_screen_paired_device_is_refused_and_full_access_creates_no_job(box):
    text = "Keep only Birch from the review screen."
    draft = review_snapshots(box, [text])[0]
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id = box["run"]["id"]
    assert (
        client.post(
            "/api/devices/enrol-display",
            json={"name": "Fixture screen"},
            headers={**HEADERS, "X-Operation-Id": "enrol-review"},
        ).status_code
        == 200
    )
    paired = TestClient(box["app"])
    paired.headers.update(
        {**HEADERS, "Authorization": "Bearer " + client.cookies.get("desk_companion_device")}
    )
    denied = paired.post(
        "/api/assistant/messages",
        json={
            "message": text,
            "voice_origin_ref": draft["voice_origin_ref"],
            "voice_steer": True,
            "task_id": box["task"]["id"],
        },
        headers={**HEADERS, "X-Operation-Id": "paired-review"},
    )
    assert denied.status_code == 403, denied.text
    assert goal_of(runtime, principal, run_id)["goal"] == ORIGINAL
    policy = runtime.permissions.snapshot()
    runtime.permissions.change(
        PermissionChange(mode="full", expected_version=policy["version"]),
        "full-review",
    )
    before = counts(runtime)
    admitted = send(
        client,
        text,
        key="full-review",
        task_id=box["task"]["id"],
        voice_origin_ref=draft["voice_origin_ref"],
        voice_steer=True,
    )
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["admitted"] is True
    assert admitted.json().get("proposal") is None
    assert admitted.json().get("job") is None
    after = counts(runtime)
    assert after["jobs"] == before["jobs"] and after["proposals"] == before["proposals"]
    assert runtime.tasks.detail(box["task"]["id"])["task"]["next_step"] == "Keep the supplier note"
    assert steers(runtime, run_id) == 1


def test_no_work_message_does_not_create_a_run(box):
    runtime, client = box["runtime"], box["client"]
    before = counts(runtime)
    message, _ = phrase("mid-flow-change")
    missing = send(client, message, key="no-task")
    assert missing.status_code == 200, missing.text
    assert missing.json()["admitted"] is False
    assert counts(runtime) == before


def test_voice_steer_shows_one_verified_result_for_the_new_goal(box):
    text = "Keep only Birch."
    draft = review_snapshots(box, [text])[0]
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    calls = []
    runtime.text_ai.generate = lambda *args, **kwargs: calls.append(args)
    admitted = send(
        client,
        text,
        key="voice-result",
        task_id=task_id,
        voice_origin_ref=draft["voice_origin_ref"],
        voice_steer=True,
    )
    assert admitted.status_code == 200, admitted.text
    body = admitted.json()
    assert body["result"]["verified"] is True
    assert body["result"]["goal"] == text
    assert f"Report file verified: Goal: {text}" in body["message"]
    assert ORIGINAL not in body["message"]
    assert calls == [] and box["executed"] == []
    assert goal_of(runtime, principal, run_id)["model_calls"] == 0
    assert goal_of(runtime, principal, box["other"]["id"])["reads"] == 0
    published = reports(runtime, principal, run_id)
    assert len(published) == 1
    session = hashlib.sha256(principal["session"].encode()).hexdigest()
    content = runtime.artifacts.read(published[0], session_hash=session)["content"]
    assert f"Goal: {text}" in content
    assert f"Goal: {ORIGINAL}" not in content
    again = send(
        client,
        text,
        key="voice-result",
        task_id=task_id,
        voice_origin_ref=draft["voice_origin_ref"],
        voice_steer=True,
    )
    assert again.status_code == 200, again.text
    assert again.json()["result"]["artifact_id"] == body["result"]["artifact_id"]
    assert reports(runtime, principal, run_id) == published
    assert len(verified_turns(runtime, body["conversation_id"])) == 1


def test_interrupted_executor_result_is_not_success_and_retries_once(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    message, _ = phrase("mid-flow-change")
    runtime.conversation_work.offline_interrupt = "before_result"
    refused = send(client, message, key="result-interrupt", task_id=task_id)
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_INTERRUPTED"
    assert "Verified result" not in refused.text
    assert "admitted" not in refused.json()
    assert goal_of(runtime, principal, run_id)["goal"] == "quantity 48, budget 950 HKD."
    assert steers(runtime, run_id) == 1
    assert reports(runtime, principal, run_id) == []
    runtime.conversation_work.offline_interrupt = None
    admitted = send(client, message, key="result-interrupt", task_id=task_id)
    assert admitted.status_code == 200, admitted.text
    body = admitted.json()
    assert body["admitted"] is True and body["result"]["verified"] is True
    assert f"Goal: {body['goal']}" in body["message"]
    published = reports(runtime, principal, run_id)
    assert len(published) == 1
    cached = send(client, message, key="result-interrupt", task_id=task_id)
    assert cached.status_code == 200, cached.text
    assert reports(runtime, principal, run_id) == published
    assert steers(runtime, run_id) == 1


def test_unknown_executor_result_is_recovered_once(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    message, _ = phrase("stream-change")
    runtime.conversation_work.offline_interrupt = "after_result"
    unknown = send(client, message, key="result-unknown", task_id=task_id)
    assert unknown.status_code == 409, unknown.text
    assert unknown.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_UNKNOWN"
    assert "Verified result" not in unknown.text
    assert "admitted" not in unknown.json()
    assert steers(runtime, run_id) == 1
    published = reports(runtime, principal, run_id)
    assert len(published) == 1
    recovered = send(
        client,
        message,
        key="result-unknown",
        task_id=task_id,
    )
    assert recovered.status_code == 200, recovered.text
    body = recovered.json()
    assert body["admitted"] is True and body["recovered"] is True
    assert body["result"]["verified"] is True
    assert body["result"]["artifact_id"] == published[0]
    assert f"Report file verified: Goal: {body['goal']}" in body["message"]
    assert reports(runtime, principal, run_id) == published
    cached = send(client, message, key="result-unknown", task_id=task_id)
    assert cached.status_code == 200, cached.text
    assert reports(runtime, principal, run_id) == published
    assert len(verified_turns(runtime, body["conversation_id"])) == 1
    assert steers(runtime, run_id) == 1


def test_unverified_and_failed_results_are_not_shown_as_success(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    message, _ = phrase("mid-flow-change")
    original = runtime.artifacts.read

    def unverified(artifact_id, *, session_hash):
        reading = original(artifact_id, session_hash=session_hash)
        artifact = dict(reading["artifact"])
        artifact["status"] = "unknown"
        artifact["verification"] = "unverified"
        return {**reading, "artifact": artifact}

    runtime.artifacts.read = unverified
    refused = send(client, message, key="unverified-result", task_id=task_id)
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_UNVERIFIED"
    assert "Verified result" not in refused.text
    assert "admitted" not in refused.json()
    runtime.artifacts.read = original
    admitted = send(client, message, key="unverified-result", task_id=task_id)
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["result"]["verified"] is True
    published = reports(runtime, principal, run_id)
    assert len(published) == 1
    again = send(client, message, key="unverified-result", task_id=task_id)
    assert again.status_code == 200, again.text
    assert reports(runtime, principal, run_id) == published


def test_failed_executor_result_is_not_shown_as_success(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]

    def fail(run):
        raise DomainError("RUN_SELECTED_EVIDENCE_UNREAD", 422)

    runtime.agent_runs._deterministic = fail
    failed = send(client, "Change the goal: quantity 70.", key="failed-result", task_id=task_id)
    assert failed.status_code == 409, failed.text
    assert failed.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_FAILED"
    assert "Verified result" not in failed.text
    assert "admitted" not in failed.json()
    repeated = send(client, "Change the goal: quantity 70.", key="failed-result", task_id=task_id)
    assert repeated.status_code == 409, repeated.text
    assert repeated.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_FAILED"
    assert goal_of(runtime, principal, run_id)["goal"] == "quantity 70."
    assert reports(runtime, principal, run_id) == []
    assert steers(runtime, run_id) == 1


def test_another_login_cannot_see_the_verified_result(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    message, _ = phrase("mid-flow-change")
    admitted = send(client, message, key="owner-result", task_id=box["task"]["id"])
    assert admitted.status_code == 200, admitted.text
    body = admitted.json()
    excerpt = f"Goal: {body['goal']}"
    other = owner_client(box["app"])
    hidden = other.post(
        "/api/assistant/messages",
        json={
            "message": "Hello from another login",
            "conversation_id": body["conversation_id"],
            "task_id": box["task"]["id"],
        },
        headers={**HEADERS, "X-Operation-Id": "other-login"},
    )
    assert hidden.status_code == 404, hidden.text
    assert excerpt not in hidden.text
    assert "Verified result" not in hidden.text
    fresh = other.post(
        "/api/assistant/messages",
        json={"message": "Hello from another login", "task_id": box["task"]["id"]},
        headers={**HEADERS, "X-Operation-Id": "other-login-fresh"},
    )
    assert fresh.status_code == 200, fresh.text
    assert excerpt not in fresh.text
    assert "Verified result" not in fresh.text
    other_owner = hashlib.sha256(other.cookies.get("desk_companion_session").encode()).hexdigest()
    for entry in runtime.voice.conversations.entries.values():
        if entry.owner != other_owner:
            continue
        blob = "\n".join(item["text"] for item in entry.items)
        assert excerpt not in blob
        assert "Verified result" not in blob
    assert goal_of(runtime, principal, box["run"]["id"])["model_calls"] == 0


def test_follow_up_phrases_are_a_closed_list():
    data = follow_up_cases()
    assert data["asks"] and data["not_asks"]
    assert {item["language"] for item in data["asks"]} == {"en", "zh"}
    for item in data["asks"]:
        assert parse_work_followup(item["message"]) is True
        assert parse_changed_goal(item["message"]) is None
    for item in data["not_asks"]:
        assert parse_work_followup(item["message"]) is False


def _assert_reshown(body, *, goal, artifact_id):
    assert body["kind"] == "work_result"
    assert body["admitted"] is False and body["recovered"] is False and body["saved"] is False
    assert body.get("proposal") is None and body.get("job") is None
    assert body["goal"] == goal
    assert body["result"] == {
        "verified": True,
        "state": "verified",
        "verification": "byte_readback",
        "quality": "not_semantically_checked",
        "goal": goal,
        "artifact_id": artifact_id,
        "format": "markdown",
    }
    assert f"Goal: {goal}" in body["message"]
    assert ORIGINAL not in body["message"]
    assert "Nothing was sent or bought." in body["message"] or "没有发送或购买" in body["message"]


def test_later_turn_reshows_the_verified_result_without_another_executor(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    message, _ = phrase("mid-flow-change")
    calls = []

    def generate(*args, **kwargs):
        calls.append(args)
        raise AssertionError("provider called")

    provider = runtime.text_ai.config.provider
    runtime.text_ai.config.provider = "fake"
    runtime.text_ai.generate = generate
    admitted = send(client, message, key="change-once", task_id=task_id)
    assert admitted.status_code == 200, admitted.text
    first = admitted.json()
    goal, artifact_id = first["goal"], first["result"]["artifact_id"]
    published = reports(runtime, principal, run_id)
    steps = step_count(runtime, run_id)
    advances = watch_advance(runtime)
    before = counts(runtime)
    conversation_id = first["conversation_id"]
    for item in follow_up_cases()["asks"]:
        shown = send(
            client,
            item["message"],
            key=f"ask-{item['id']}",
            task_id=task_id,
            conversation_id=conversation_id,
            language=item["language"],
        )
        assert shown.status_code == 200, shown.text
        body = shown.json()
        _assert_reshown(body, goal=goal, artifact_id=artifact_id)
        assert body["work_run_id"] == run_id
        assert body["conversation_id"] == conversation_id
        cached = send(
            client,
            item["message"],
            key=f"ask-{item['id']}",
            task_id=task_id,
            conversation_id=conversation_id,
            language=item["language"],
        )
        assert cached.status_code == 200, cached.text
        assert cached.json()["result"]["artifact_id"] == artifact_id
    conflict = send(
        client,
        "What was the verified result?",
        key="ask-ordinary-en",
        task_id=task_id,
        conversation_id=conversation_id,
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["code"] == "OPERATION_ID_CONFLICT"
    assert calls == []
    runtime.text_ai.config.provider = provider
    for item in follow_up_cases()["not_asks"]:
        other = send(
            client,
            item["message"],
            key=f"not-{item['id']}",
            task_id=task_id,
            conversation_id=conversation_id,
        )
        assert other.status_code == 200, other.text
        assert other.json().get("kind") != "work_result"
        assert other.json().get("result", {}).get("verification") != "byte_readback"
        assert "Report file verified" not in other.text
        assert f"Goal: {goal}" not in other.text
    fresh = send(client, "How is this work going?", key="other-conversation", task_id=task_id)
    assert fresh.status_code == 200, fresh.text
    assert fresh.json()["conversation_id"] != conversation_id
    assert fresh.json().get("kind") != "work_result"
    assert f"Goal: {goal}" not in fresh.text
    assert advances == [] and calls == [] and box["executed"] == []
    assert reports(runtime, principal, run_id) == published
    assert step_count(runtime, run_id) == steps
    assert steers(runtime, run_id) == 1
    assert goal_of(runtime, principal, run_id)["goal"] == goal
    assert goal_of(runtime, principal, run_id)["model_calls"] == 0
    assert goal_of(runtime, principal, box["other"]["id"])["reads"] == 0
    after = counts(runtime)
    assert after["runs"] == before["runs"] and after["jobs"] == before["jobs"]
    assert after["usage"] == 0 and after["tasks"] == before["tasks"]


def test_follow_up_stream_recovers_without_a_second_executor(box):
    client, runtime, principal = box["client"], box["runtime"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    message, _ = phrase("stream-change")
    admitted = send(client, message, key="stream-change", task_id=task_id)
    assert admitted.status_code == 200, admitted.text
    first = admitted.json()
    published = reports(runtime, principal, run_id)
    steps = step_count(runtime, run_id)
    advances = watch_advance(runtime)
    headers = {**HEADERS, "X-Operation-Id": "stream-ask"}
    body = {
        "message": "How is this work going?",
        "task_id": task_id,
        "conversation_id": first["conversation_id"],
    }
    with client.stream(
        "POST", "/api/assistant/messages/stream", json=body, headers=headers
    ) as opened:
        assert opened.status_code == 200
        chunk = next(opened.iter_bytes())
        assert chunk
        with pytest.raises(json.JSONDecodeError):
            json.loads(chunk)
    recovered = client.post("/api/assistant/messages/stream", json=body, headers=headers)
    assert recovered.status_code == 200, recovered.text
    events = parse_sse(recovered.text)
    reply = events[-1]["reply"]
    assert events[-1]["type"] == "done"
    _assert_reshown(reply, goal=first["goal"], artifact_id=first["result"]["artifact_id"])
    repeated = client.post("/api/assistant/messages/stream", json=body, headers=headers)
    assert repeated.status_code == 200, repeated.text
    assert advances == []
    assert reports(runtime, principal, run_id) == published
    assert step_count(runtime, run_id) == steps
    assert steers(runtime, run_id) == 1


def test_voice_result_is_reshown_on_a_later_turn(box):
    text = "Keep only Birch."
    draft = review_snapshots(box, [text])[0]
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    admitted = send(
        client,
        text,
        key="voice-then-ask",
        task_id=task_id,
        voice_origin_ref=draft["voice_origin_ref"],
        voice_steer=True,
    )
    assert admitted.status_code == 200, admitted.text
    first = admitted.json()
    advances = watch_advance(runtime)
    shown = send(
        client,
        "核验结果是什么？",
        key="voice-ask",
        task_id=task_id,
        conversation_id=first["conversation_id"],
        language="zh",
    )
    assert shown.status_code == 200, shown.text
    _assert_reshown(shown.json(), goal=text, artifact_id=first["result"]["artifact_id"])
    assert advances == []
    assert steers(runtime, run_id) == 1
    assert goal_of(runtime, principal, run_id)["model_calls"] == 0
    assert box["executed"] == []


def test_follow_up_keeps_auth_boundaries(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    message, _ = phrase("mid-flow-change")
    admitted = send(client, message, key="auth-change", task_id=box["task"]["id"])
    assert admitted.status_code == 200, admitted.text
    first = admitted.json()
    goal, conversation_id = first["goal"], first["conversation_id"]
    other = owner_client(box["app"])
    hidden = other.post(
        "/api/assistant/messages",
        json={
            "message": "How is this work going?",
            "conversation_id": conversation_id,
            "task_id": box["task"]["id"],
        },
        headers={**HEADERS, "X-Operation-Id": "other-ask"},
    )
    assert hidden.status_code == 404, hidden.text
    assert f"Goal: {goal}" not in hidden.text
    fresh = other.post(
        "/api/assistant/messages",
        json={"message": "How is this work going?", "task_id": box["task"]["id"]},
        headers={**HEADERS, "X-Operation-Id": "other-ask-fresh"},
    )
    assert fresh.status_code == 200, fresh.text
    assert f"Goal: {goal}" not in fresh.text
    assert fresh.json().get("kind") != "work_result"
    assert (
        client.post(
            "/api/devices/enrol-display",
            json={"name": "Fixture screen"},
            headers={**HEADERS, "X-Operation-Id": "enrol-ask"},
        ).status_code
        == 200
    )
    paired = TestClient(box["app"])
    paired.headers.update(
        {**HEADERS, "Authorization": "Bearer " + client.cookies.get("desk_companion_device")}
    )
    denied = paired.post(
        "/api/assistant/messages",
        json={
            "message": "How is this work going?",
            "conversation_id": conversation_id,
            "task_id": box["task"]["id"],
        },
        headers={**HEADERS, "X-Operation-Id": "paired-ask"},
    )
    assert denied.status_code == 403, denied.text
    assert f"Goal: {goal}" not in denied.text
    policy = runtime.permissions.snapshot()
    runtime.permissions.change(
        PermissionChange(mode="full", expected_version=policy["version"]),
        "full-ask",
    )
    before = counts(runtime)
    advances = watch_advance(runtime)
    shown = send(
        client,
        "How is this work going?",
        key="full-ask-turn",
        task_id=box["task"]["id"],
        conversation_id=conversation_id,
    )
    assert shown.status_code == 200, shown.text
    _assert_reshown(shown.json(), goal=goal, artifact_id=first["result"]["artifact_id"])
    after = counts(runtime)
    assert after["jobs"] == before["jobs"] and after["proposals"] == before["proposals"]
    assert advances == []
    assert runtime.tasks.detail(box["task"]["id"])["task"]["next_step"] == "Keep the supplier note"
    assert goal_of(runtime, principal, box["run"]["id"])["model_calls"] == 0


def test_interrupted_result_is_not_reshown_and_can_still_finish_once(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    message, _ = phrase("mid-flow-change")
    runtime.conversation_work.offline_interrupt = "before_result"
    interrupted = send(client, message, key="interrupt-then-ask", task_id=task_id)
    assert interrupted.status_code == 409, interrupted.text
    assert interrupted.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_INTERRUPTED"
    runtime.conversation_work.offline_interrupt = None
    conversation_id = owner_conversation(runtime, principal).id
    advances = watch_advance(runtime)
    asked = send(
        client,
        "How is this work going?",
        key="ask-after-interrupt",
        task_id=task_id,
        conversation_id=conversation_id,
    )
    assert asked.status_code == 200, asked.text
    assert asked.json().get("kind") != "work_result"
    assert asked.json().get("result", {}).get("verified") is not True
    assert "Report file verified" not in asked.text
    assert advances == []
    assert reports(runtime, principal, run_id) == []
    runtime.agent_runs.advance_one = runtime.agent_runs.advance_one.original
    finished = send(client, message, key="interrupt-then-ask", task_id=task_id)
    assert finished.status_code == 200, finished.text
    assert finished.json()["result"]["verified"] is True
    assert len(reports(runtime, principal, run_id)) == 1
    assert steers(runtime, run_id) == 1


def test_failed_result_is_not_reshown(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    original = runtime.agent_runs._deterministic

    def fail(run):
        raise DomainError("RUN_SELECTED_EVIDENCE_UNREAD", 422)

    runtime.agent_runs._deterministic = fail
    failed = send(client, "Change the goal: quantity 70.", key="fail-then-ask", task_id=task_id)
    assert failed.status_code == 409, failed.text
    assert failed.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_FAILED"
    assert "Report file verified" not in failed.text
    conversation_id = owner_conversation(runtime, principal).id
    advances = watch_advance(runtime)
    asked = send(
        client,
        "Show the verified result.",
        key="ask-after-fail",
        task_id=task_id,
        conversation_id=conversation_id,
    )
    assert asked.status_code == 200, asked.text
    assert asked.json().get("kind") != "work_result"
    assert "Report file verified" not in asked.text
    assert advances == []
    assert reports(runtime, principal, run_id) == []
    assert steers(runtime, run_id) == 1
    repeated = send(
        client, "Change the goal: quantity 70.", key="fail-then-ask", task_id=task_id
    )
    assert repeated.status_code == 409, repeated.text
    assert repeated.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_FAILED"
    assert reports(runtime, principal, run_id) == []
    runtime.agent_runs._deterministic = original


def test_tampered_verified_file_is_not_reshown_as_success(box):
    runtime, client, principal = box["runtime"], box["client"], box["principal"]
    run_id, task_id = box["run"]["id"], box["task"]["id"]
    message, _ = phrase("explicit-change", run_id=box["run"]["id"])
    admitted = send(client, message, key="tamper-change", task_id=task_id)
    assert admitted.status_code == 200, admitted.text
    first = admitted.json()
    published = reports(runtime, principal, run_id)
    original = runtime.artifacts.read

    def unverified(artifact_id, *, session_hash):
        reading = original(artifact_id, session_hash=session_hash)
        artifact = dict(reading["artifact"])
        artifact["status"] = "unknown"
        artifact["verification"] = "unverified"
        return {**reading, "artifact": artifact}

    runtime.artifacts.read = unverified
    advances = watch_advance(runtime)
    refused = send(
        client,
        "What was the verified result?",
        key="tampered-ask",
        task_id=task_id,
        conversation_id=first["conversation_id"],
    )
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_UNVERIFIED"
    assert "admitted" not in refused.json()
    assert "Report file verified" not in refused.text
    assert f"Goal: {first['goal']}" not in refused.text
    repeated = send(
        client,
        "What was the verified result?",
        key="tampered-ask",
        task_id=task_id,
        conversation_id=first["conversation_id"],
    )
    assert repeated.status_code == 409, repeated.text
    assert repeated.json()["error"]["code"] == "CONVERSATION_WORK_RESULT_UNVERIFIED"
    assert advances == []
    assert reports(runtime, principal, run_id) == published
    runtime.artifacts.read = original
    shown = send(
        client,
        "What was the verified result?",
        key="tampered-ask-restored",
        task_id=task_id,
        conversation_id=first["conversation_id"],
    )
    assert shown.status_code == 200, shown.text
    _assert_reshown(shown.json(), goal=first["goal"], artifact_id=first["result"]["artifact_id"])
    assert advances == []
    assert reports(runtime, principal, run_id) == published
    assert steers(runtime, run_id) == 1

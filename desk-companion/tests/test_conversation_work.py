"""Ordinary Alice turns that change the goal of an existing Work run.

Scripted local conversation only. No provider call, live account, payment, or device.
"""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from desk.agent_run_schemas import RunAction, RunCreate
from desk.assistant import TOOLS
from desk.app import create_app
from desk.permissions import PermissionChange
from desk.sources import SourceInput
from desk.stream_contract import parse_sse
from desk.tasks import TaskInput

HEADERS = {"X-Desk-Request": "1"}
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "conversation-work" / "changed-goal.json"
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


def send(client, message, *, key, task_id=None, conversation_id=None, language="en"):
    body = {"message": message, "language": language}
    if task_id:
        body["task_id"] = task_id
    if conversation_id:
        body["conversation_id"] = conversation_id
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


def goal_of(runtime, principal, run_id):
    return runtime.agent_runs.detail(run_id, principal)["run"]


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
    again = send(
        client,
        change,
        key="change",
        task_id=task_id,
        conversation_id=body["conversation_id"],
    )
    assert again.status_code == 200, again.text
    assert again.json()["work_run_id"] == run_id
    assert steers(runtime, run_id) == 1
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
    assert goal_of(runtime, principal, second["id"])["goal"] == "Keep only the Birch quote."
    assert goal_of(runtime, principal, first["id"])["goal"] == ORIGINAL
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
    assert admitted.json().get("proposal") is None
    assert admitted.json().get("job") is None
    after = counts(runtime)
    assert after["jobs"] == before["jobs"] and after["proposals"] == before["proposals"]
    assert runtime.tasks.detail(box["task"]["id"])["task"]["next_step"] == "Keep the supplier note"
    assert goal_of(runtime, principal, box["other"]["id"])["goal"] == "Leave this work alone"


def test_no_work_message_does_not_create_a_run(box):
    runtime, client = box["runtime"], box["client"]
    before = counts(runtime)
    message, _ = phrase("mid-flow-change")
    missing = send(client, message, key="no-task")
    assert missing.status_code == 200, missing.text
    assert missing.json()["admitted"] is False
    assert counts(runtime) == before

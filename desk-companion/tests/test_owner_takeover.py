"""Owner takeover of one browser job at a local verification wall. No live site or model."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.access import PairingClaim, PairingDecision, PairingRequest
from desk.app import create_app
from desk.browser_supervisor import WorkerOutcome
from desk.computer_use_files import refresh_file, write_file
from desk.computer_use_models import ComputerUseInput, classify_owner_wall, wall_from_reason
from desk.computer_use_worker import act
from desk.jobs import JobApproval, JobHandoff
from desk.store import DomainError, encode
from desk.text_ai import TextConfig
from test_computer_use import png

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "browser"
WALL = (FIXTURES / "verification-wall.html").read_text()
CLEARED = (FIXTURES / "verification-cleared.html").read_text()
SECRET = "fixture-secret-otp-918273"
HEADERS = {"X-Desk-Request": "1"}


class VerificationDriver:
    """Fake browser. The owner flag is set by the test, never by Alice."""

    executable = "/fixture/chromium"

    def __init__(self):
        self.calls = 0
        self.owner_passed = False
        self.cleanup = True
        self.payloads = []
        self.provider_calls = 0

    def readiness(self):
        return None

    def run(self, payload, directory, checkpoint, *, on_observation, **kwargs):
        self.calls += 1
        self.payloads.append(payload)
        checkpoint("computer_open")
        resume = payload.get("resume_same_job") is True
        if resume:
            saved = json.loads((directory / "browser-state.json").read_text())
            assert saved.get("marker") == "same-job"
        page = CLEARED if resume and self.owner_passed else WALL
        wall = None if resume and self.owner_passed else classify_owner_wall(page)
        screen = png()
        number = 2 if resume else 1
        name = f"screen-{number}.png"
        write_file(directory, name, screen)
        observation = {
            "sequence": number,
            "screen": name,
            "sha256": hashlib.sha256(screen).hexdigest(),
            "url": "http://127.0.0.1/verification-rehearsal",
            "title": "Site verification",
            "text": page,
        }
        state = {"cookies": [], "origins": [], "marker": "same-job"}
        body = encode(state).encode()
        if resume:
            refresh_file(directory, "browser-state.json", body)
        else:
            write_file(directory, "browser-state.json", body)
        state_sha = hashlib.sha256(body).hexdigest()
        if resume and self.owner_passed and wall is None:
            self.provider_calls += 1
            assert on_observation(observation)["finish"] is True
            evidence = {
                "cleared": True,
                "wall": "captcha",
                "state_sha256": state_sha,
                "observed_text": "The rehearsal page is open again.",
            }
            refresh_file(directory, "wall-evidence.json", encode(evidence).encode())
            outcome, reason = "review_ready", "review_prepared_page"
        else:
            assert wall and wall["wall"] == "captcha"
            outcome, reason = "needs_owner", wall["reason"]
        return WorkerOutcome(
            {
                "observation": observation,
                "outcome": outcome,
                "reason": reason,
                "demo_submissions": 0,
                "demo": True,
                "browser_version": "fixture",
                "network_boundary": "public_request_routing_only",
            },
            None,
            True,
            self.cleanup,
        )


@pytest.fixture
def world(tmp_path):
    clock = [datetime(2026, 11, 10, 12, tzinfo=UTC)]
    app = create_app(tmp_path, password="fixture", scheduler=False, clock=lambda: clock[0])
    runtime = app.state.runtime
    runtime.text_ai.config = TextConfig(
        "openai", "gpt-6.1-sol", "https://api.openai.com/v1/responses", "synthetic-key"
    )
    driver = VerificationDriver()
    runtime.jobs.computer_use.enabled = True
    runtime.jobs.computer_use.supervisor = driver
    seen = []
    runtime.text_ai.transport = httpx.MockTransport(
        lambda request: seen.append(request.url)
        or httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "The page is open."}],
                    }
                ],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )
    )
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture"},
            headers=HEADERS,
        ).status_code
        == 200
    )
    principal = {
        "kind": "owner",
        "id": "owner",
        "session": client.cookies.get("desk_companion_session"),
    }
    return runtime, client, principal, driver, seen, clock


def prepare(world, key="prepare-wall"):
    runtime, _, principal, *_ = world
    return runtime.jobs.prepare(
        ComputerUseInput(
            title="Check the public page",
            goal="Open the page and stop if it asks for a person",
            start_url="demo:shopping",
            public_only=True,
            share_screen=True,
            max_steps=2,
        ),
        key,
        principal=principal,
    )["job"]


def approve(runtime, job):
    detail = runtime.jobs.detail(job["id"], review=True)
    runtime.jobs.approve(
        job["id"],
        JobApproval(expected_version=detail["version"], intent_hash=detail["intent_hash"]),
        job["id"] + "/approve",
    )


def pause(world, key="prepare-wall"):
    runtime, _, _, driver, seen, _ = world
    job = prepare(world, key)
    approve(runtime, job)
    runtime.jobs.run_one()
    detail = runtime.jobs.detail(job["id"], review=True)
    assert detail["state"] == "owner_takeover"
    assert detail["id"] == job["id"]
    assert driver.calls == 1 and driver.provider_calls == 0 and seen == []
    assert detail["result"]["verified"] is False
    assert detail["result"]["wall"] == "captcha"
    assert "will not solve it" in detail["result"]["needed"]
    assert SECRET not in encode(detail)
    return detail


def post(client, job_id, kind, version, operation, **extra):
    return client.post(
        f"/api/computer/jobs/{job_id}/{kind}",
        json={"expected_version": version, **extra},
        headers={**HEADERS, "X-Operation-Id": operation},
    )


def test_fixture_pages_name_the_wall_and_the_cleared_page_does_not():
    assert classify_owner_wall(WALL)["wall"] == "captcha"
    assert classify_owner_wall(CLEARED) is None
    assert classify_owner_wall("Total HKD 55.80\nPlace order\nNo real orders or payment.") is None
    assert classify_owner_wall("Enter the SMS code")["wall"] == "otp"
    assert classify_owner_wall("Confirm payment of HKD 10")["wall"] == "payment"
    assert classify_owner_wall("Sign in to continue")["wall"] == "login"
    assert wall_from_reason("final_submission_needs_owner")["wall"] == "payment"
    assert wall_from_reason("provider_step_unavailable") is None


def test_password_keystrokes_never_reach_the_page():
    class Page:
        async def evaluate(self, *_args):
            return {"tag": "input", "type": "password", "label": "Password"}

    reason = asyncio.run(act(Page(), {"type": "type", "text": SECRET, "x": 1, "y": 1}))
    assert reason == "personal_or_login_input_needs_owner"
    assert SECRET not in reason


def test_wall_pauses_the_same_job_and_the_owner_resumes_it(world):
    runtime, client, _, driver, seen, _ = world
    job = pause(world)
    kept = dict(job["result"]["observation"])
    with runtime.store.connection(write=True) as conn:
        record = json.loads(
            conn.execute("SELECT result FROM computer_jobs WHERE id=?", (job["id"],)).fetchone()[0]
        )
        record["kept_note"] = "still here"
        conn.execute(
            "UPDATE computer_jobs SET result=? WHERE id=?", (encode(record), job["id"])
        )
    denied = post(client, job["id"], "takeover", job["version"], "takeover-secret", password=SECRET)
    assert denied.status_code == 422
    assert SECRET.encode() not in Path(runtime.store.path).read_bytes()

    held = post(client, job["id"], "takeover", job["version"], "takeover-1")
    assert held.status_code == 200, held.text
    body = held.json()
    assert body["held"] is True and body["operation_id"] == "takeover-1"
    assert body["job"]["id"] == job["id"]
    assert body["job"]["result"]["phase"] == "held"
    assert body["job"]["result"]["kept_note"] == "still here"
    assert body["job"]["result"]["observation"] == kept
    again = post(client, job["id"], "takeover", job["version"], "takeover-1")
    assert again.status_code == 200 and again.json()["job"]["version"] == body["job"]["version"]

    driver.owner_passed = True
    returned = post(client, job["id"], "return", body["job"]["version"], "return-1")
    assert returned.status_code == 200, returned.text
    assert returned.json()["resumed"] is True
    assert returned.json()["job"]["state"] == "queued"
    assert returned.json()["job"]["result"]["kept_note"] == "still here"
    duplicate = post(client, job["id"], "return", body["job"]["version"], "return-1")
    assert duplicate.status_code == 200 and duplicate.json()["operation_id"] == "return-1"
    assert runtime.jobs.detail(job["id"])["state"] == "queued"
    assert len(runtime.jobs.listing()) == 1
    runtime.jobs.run_one()
    done = runtime.jobs.detail(job["id"], review=True)
    assert done["id"] == job["id"] and done["state"] == "succeeded"
    assert done["result"]["verified"] is True
    assert done["result"]["readback"]["evidence_sha256"]
    assert "rehearsal page is open again" in done["result"]["readback"]["observation"]["text"]
    assert driver.calls == 2 and driver.provider_calls == 1 and len(seen) == 1
    assert all(SECRET not in encode(item) for item in driver.payloads)
    screen = client.get(f"/api/computer/computer-use/jobs/{job['id']}/screen")
    assert screen.status_code == 200 and screen.content == png()


def test_return_without_evidence_and_a_lost_takeover_are_not_success(world):
    runtime, client, _, driver, _, _ = world
    job = pause(world)
    real = runtime.store.operation

    def fail_once(key, payload, apply):
        def boom(conn):
            apply(conn)
            raise RuntimeError("stream closed")

        real(key, payload, boom)

    runtime.store.operation = fail_once
    try:
        with pytest.raises(RuntimeError, match="stream closed"):
            post(client, job["id"], "takeover", job["version"], "takeover-lost")
    finally:
        runtime.store.operation = real
    stalled = runtime.jobs.detail(job["id"], review=True)
    assert stalled["state"] == "owner_takeover" and stalled["result"]["phase"] == "paused"
    recovered = post(client, job["id"], "takeover", job["version"], "takeover-lost")
    assert recovered.status_code == 200 and recovered.json()["held"] is True

    returned = post(client, job["id"], "return", recovered.json()["job"]["version"], "return-lost")
    assert returned.json()["resumed"] is True
    driver.owner_passed = True
    driver.cleanup = False
    runtime.jobs.run_one()
    unknown = runtime.jobs.detail(job["id"], review=True)
    assert unknown["state"] == "unknown"
    assert not (unknown.get("result") or {}).get("verified")
    replay = post(client, job["id"], "return", recovered.json()["job"]["version"], "return-lost")
    assert replay.status_code == 200
    assert runtime.jobs.detail(job["id"])["state"] == "unknown"
    assert len(runtime.jobs.listing()) == 1
    with pytest.raises(DomainError) as raised:
        runtime.jobs.reconcile(job["id"])
    assert raised.value.code == "COMPUTER_CLEANUP_REQUIRED"
    assert runtime.jobs.detail(job["id"])["state"] == "unknown"


def test_resume_stays_paused_when_the_wall_is_still_there(world):
    runtime, client, _, driver, seen, _ = world
    job = pause(world)
    held = post(client, job["id"], "takeover", job["version"], "takeover-still")
    version = held.json()["job"]["version"]
    returned = post(client, job["id"], "return", version, "return-still")
    assert returned.json()["resumed"] is True
    runtime.jobs.run_one()
    again = runtime.jobs.detail(job["id"], review=True)
    assert again["id"] == job["id"] and again["state"] == "owner_takeover"
    assert again["result"]["phase"] == "paused" and again["result"]["verified"] is False
    assert driver.owner_passed is False and driver.provider_calls == 0 and seen == []


def test_paired_device_and_another_login_cannot_take_over(world):
    runtime, client, _, _, _, _ = world
    job = pause(world)
    access = runtime.access
    code = access.issue("display", "issue-display")
    requested = access.request(PairingRequest(code=code["code"], name="Fixture screen"))
    access.decide(
        PairingDecision(request_id=requested["request_id"], action="approve"), "approve-display"
    )
    paired = access.claim(
        PairingClaim(request_id=requested["request_id"], secret=requested["secret"])
    )
    stranger = TestClient(client.app)
    stranger.headers["Authorization"] = "Bearer " + paired["token"]
    denied = post(stranger, job["id"], "takeover", job["version"], "paired-takeover")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "OWNER_SIGN_IN_REQUIRED"

    other = TestClient(client.app)
    other.cookies.set("desk_companion_session", runtime.store.create_owner_session())
    wrong = post(other, job["id"], "return", job["version"], "other-return")
    assert wrong.status_code == 403 and wrong.json()["error"]["code"] == "OWNER_REQUIRED"
    assert runtime.jobs.detail(job["id"])["state"] == "owner_takeover"
    assert runtime.jobs.detail(job["id"])["result"]["phase"] == "paused"


def test_takeover_expires_and_cancel_stays_cancelled(world):
    runtime, client, _, driver, _, clock = world
    job = pause(world)
    clock[0] += timedelta(seconds=181)
    runtime.jobs.expire()
    expired = runtime.jobs.detail(job["id"])
    assert expired["state"] == "expired"
    late = post(client, job["id"], "takeover", job["version"], "late-takeover")
    assert late.status_code == 409
    assert runtime.jobs.detail(job["id"])["state"] == "expired"

    clock[0] -= timedelta(seconds=181)
    second = prepare(world, "prepare-wall-again")
    approve(runtime, second)
    runtime.jobs.run_one()
    current = runtime.jobs.detail(second["id"], review=True)
    assert current["state"] == "owner_takeover"
    cancelled = client.post(
        f"/api/computer/jobs/{second['id']}/cancel",
        headers={**HEADERS, "X-Operation-Id": "cancel-wall"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["job"]["state"] == "cancelled"
    handed = post(client, second["id"], "return", current["version"], "return-cancelled")
    assert handed.status_code == 409
    runtime.jobs.run_one()
    assert runtime.jobs.detail(second["id"])["state"] == "cancelled"
    assert driver.calls == 2


def test_provider_failure_is_not_an_owner_wall(world):
    runtime, _, principal, driver, _, _ = world

    class ProviderStop(VerificationDriver):
        def run(self, payload, directory, checkpoint, *, on_observation, **kwargs):
            self.calls += 1
            checkpoint("computer_open")
            screen = png()
            write_file(directory, "screen-1.png", screen)
            write_file(directory, "browser-state.json", b'{"cookies":[],"origins":[]}')
            return WorkerOutcome(
                {
                    "observation": {
                        "sequence": 1,
                        "screen": "screen-1.png",
                        "sha256": hashlib.sha256(screen).hexdigest(),
                        "url": "http://127.0.0.1/verification-rehearsal",
                        "title": "Open page",
                        "text": "A public page",
                    },
                    "outcome": "needs_owner",
                    "reason": "provider_step_unavailable",
                    "demo_submissions": 0,
                    "demo": True,
                    "browser_version": "fixture",
                    "network_boundary": "public_request_routing_only",
                },
                None,
                True,
                True,
            )

    runtime.jobs.computer_use.supervisor = ProviderStop()
    job = runtime.jobs.prepare(
        ComputerUseInput(
            title="Provider stop",
            goal="Read a public page",
            start_url="demo:shopping",
            public_only=True,
            share_screen=True,
        ),
        "provider-stop",
        principal=principal,
    )["job"]
    approve(runtime, job)
    runtime.jobs.run_one()
    detail = runtime.jobs.detail(job["id"], review=True)
    assert detail["state"] == "succeeded"
    assert detail["result"]["outcome"] == "needs_owner"
    assert detail["result"]["readback"]["reason"] == "provider_step_unavailable"
    with pytest.raises(DomainError) as raised:
        runtime.jobs.takeover(
            job["id"],
            JobHandoff(expected_version=detail["version"]),
            "no-wall",
            principal=principal,
        )
    assert raised.value.code == "JOB_NOT_IN_TAKEOVER"

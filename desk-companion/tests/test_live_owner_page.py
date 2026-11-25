"""The same local Chromium page stays open for the admitting owner.

App-mediated clicks and typing only. No headed window, hosted desktop, or account.
"""

import os
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.computer_use_models import ComputerUseInput
from desk.jobs import JobApproval
from desk.store import encode
from desk.text_ai import TextConfig

from ui_fixture_paths import CHROME

SECRET = "fixture-" + __import__("uuid").uuid4().hex
HEADERS = {"X-Desk-Request": "1"}


def _chrome_available():
    return os.access(CHROME, os.X_OK)


pytestmark = pytest.mark.skipif(not _chrome_available(), reason="local Chrome is required")


def _finish_transport(seen):
    def handler(request):
        seen.append(request.url)
        return httpx.Response(
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

    return httpx.MockTransport(handler)


def _world(tmp_path, seen):
    clock = [datetime(2026, 11, 24, 8, tzinfo=UTC)]
    app = create_app(tmp_path, password="fixture", scheduler=False, clock=lambda: clock[0])
    runtime = app.state.runtime
    runtime.text_ai.config = TextConfig(
        "openai", "gpt-6.1-sol", "https://api.openai.com/v1/responses", "synthetic-key"
    )
    runtime.text_ai.transport = _finish_transport(seen)
    runtime.jobs.computer_use.enabled = True
    runtime.jobs.computer_use.supervisor.executable = CHROME
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
    return runtime, client, principal, clock


def _prepare(runtime, principal, key, start_url, goal):
    job = runtime.jobs.prepare(
        ComputerUseInput(
            title="Check the rehearsal page",
            goal=goal,
            start_url=start_url,
            public_only=True,
            share_screen=True,
            max_steps=2,
            engine="local",
        ),
        key,
        principal=principal,
    )["job"]
    detail = runtime.jobs.detail(job["id"], review=True)
    runtime.jobs.approve(
        job["id"],
        JobApproval(expected_version=detail["version"], intent_hash=detail["intent_hash"]),
        key + "/approve",
    )
    return job


def _wait_state(runtime, job_id, state, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        detail = runtime.jobs.detail(job_id, review=True)
        if detail["state"] == state:
            return detail
        time.sleep(0.1)
    return runtime.jobs.detail(job_id, review=True)


def _post(client, job_id, kind, version, operation, **extra):
    return client.post(
        f"/api/computer/jobs/{job_id}/{kind}",
        json={"expected_version": version, **extra},
        headers={**HEADERS, "X-Operation-Id": operation},
    )


from ui_fixture_paths import process_children as _descendants


def _chrome_children(pid):
    return [child for child, command in _descendants(pid) if "chrome" in command.lower()]


def _kill_chrome(pid):
    """Kill only Chromium descendants so the owned worker can confirm cleanup.

    Falling back to every descendant (the previous helper) SIGKILLs the worker
    before it reports cleanup. That correctly leaves cleanup-required and makes
    the next prepare raise COMPUTER_CLEANUP_REQUIRED — which this suite then
    misread as a flaky screen error.
    """
    deadline = time.monotonic() + 10
    victims = []
    while time.monotonic() < deadline:
        victims = _chrome_children(pid)
        if victims:
            break
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.05)
    if not victims:
        raise AssertionError(
            "No Chromium child appeared under the owned browser worker; "
            "refusing to kill the worker process group and erase cleanup evidence"
        )
    for child in victims:
        try:
            os.kill(child, 9)
        except OSError:
            pass


def test_password_page_stays_open_for_the_owner_and_a_nav_link_does_not(tmp_path):
    seen = []
    runtime, client, principal, clock = _world(tmp_path, seen)
    job = _prepare(
        runtime,
        principal,
        "live-wall",
        "demo:verification",
        "Open the rehearsal and stop if it asks for a password",
    )
    worker = threading.Thread(target=runtime.jobs.run_one, daemon=True)
    worker.start()
    paused = _wait_state(runtime, job["id"], "owner_takeover")
    assert paused["state"] == "owner_takeover", paused
    assert paused["result"]["takeover_available"] is True
    assert paused["result"]["phase"] == "paused"
    assert paused["result"]["wall"] == "login"
    assert seen == []
    assert runtime.jobs.computer_use.launches == 1

    catalogue = _prepare(
        runtime,
        principal,
        "live-nav",
        "demo:public-nav",
        "Read the public catalogue",
    )
    # The first worker is parked, so run the catalogue after the hold ends.

    held = _post(client, job["id"], "takeover", paused["version"], "takeover-live")
    assert held.status_code == 200, held.text
    version = held.json()["job"]["version"]
    before = client.get(f"/api/computer/computer-use/jobs/{job['id']}/screen")
    assert before.status_code == 200 and before.headers["content-type"].startswith("image/png")

    typed = _post(
        client,
        job["id"],
        "page",
        version,
        "type-live",
        action={"type": "type", "text": SECRET},
    )
    assert typed.status_code == 200, typed.text
    version = typed.json()["job"]["version"]
    focused = _post(
        client,
        job["id"],
        "page",
        version,
        "focus-live",
        action={"type": "click", "x": 180, "y": 160},
    )
    assert focused.status_code == 200, focused.text
    version = focused.json()["job"]["version"]
    clicked = _post(
        client,
        job["id"],
        "page",
        version,
        "click-live",
        action={"type": "click", "x": 180, "y": 244},
    )
    assert clicked.status_code == 200, clicked.text
    version = clicked.json()["job"]["version"]
    after = client.get(f"/api/computer/computer-use/jobs/{job['id']}/screen")
    assert after.status_code == 200
    assert after.content != before.content
    database = Path(runtime.store.path).read_bytes()
    assert SECRET.encode() not in database
    assert SECRET not in encode(clicked.json())
    assert seen == []

    stale = _post(client, job["id"], "return", paused["version"], "return-stale")
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "VERSION_CONFLICT"
    assert runtime.jobs.detail(job["id"])["state"] == "owner_takeover"

    returned = _post(client, job["id"], "return", version, "return-live")
    assert returned.status_code == 200, returned.text
    assert returned.json()["resumed"] is True
    assert returned.json()["job"]["request"]["start_url"] == "demo:verification"
    worker.join(timeout=30)
    done = runtime.jobs.detail(job["id"], review=True)
    assert done["state"] == "succeeded", done
    assert done["result"]["verified"] is True
    assert "rehearsal page is open again" in done["result"]["readback"]["observation"]["text"]
    evidence = done["result"]["readback"]["evidence_sha256"]
    assert evidence
    assert done["result"]["readback"]["state_sha256"]
    assert runtime.jobs.computer_use.launches == 1
    assert len(seen) == 1
    again = _post(client, job["id"], "return", version, "return-live")
    assert again.status_code == 200
    assert again.json()["operation_id"] == "return-live"
    assert again.json()["resumed"] is True
    assert runtime.jobs.computer_use.launches == 1

    runtime.jobs.run_one()
    catalogue_done = _wait_state(runtime, catalogue["id"], "succeeded")
    assert catalogue_done["state"] == "succeeded", catalogue_done
    assert catalogue_done["state"] != "owner_takeover"
    assert runtime.jobs.computer_use.launches == 2


def test_payment_wall_and_privacy_or_restart_close_the_page(tmp_path):
    from desk.schemas import SettingsInput

    seen = []
    runtime, client, principal, _clock = _world(tmp_path, seen)
    payment = _prepare(runtime, principal, "live-pay", "demo:payment", "Stop before payment")
    worker = threading.Thread(target=runtime.jobs.run_one, daemon=True)
    worker.start()
    paused = _wait_state(runtime, payment["id"], "owner_takeover")
    assert paused["result"]["wall"] == "payment"
    held = _post(client, payment["id"], "takeover", paused["version"], "pay-takeover")
    assert held.status_code == 200
    returned = _post(client, payment["id"], "return", held.json()["job"]["version"], "pay-return")
    assert returned.status_code == 200, returned.text
    assert returned.json()["resumed"] is not True
    still = runtime.jobs.detail(payment["id"], review=True)
    assert still["state"] == "owner_takeover" and still["result"]["phase"] == "paused"
    assert seen == []
    runtime.store.update_settings(
        SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True),
        "hide-pay",
    )
    worker.join(timeout=20)
    closed = runtime.jobs.detail(payment["id"], review=True)
    assert closed["state"] == "unknown"
    assert closed["error"] == "PRIVATE_CONTEXT_HIDDEN"
    assert runtime.jobs.computer_use.launches == 1
    runtime.store.update_settings(
        SettingsInput(expected_version=2, timezone="Asia/Hong_Kong", hide_private=False),
        "show-pay",
    )

    restart = _prepare(
        runtime, principal, "live-restart", "demo:verification", "Stop at the password"
    )
    again = threading.Thread(target=runtime.jobs.run_one, daemon=True)
    again.start()
    waiting = _wait_state(runtime, restart["id"], "owner_takeover")
    assert waiting["result"]["takeover_available"] is True
    runtime.jobs.computer_use.supervisor.live_page = None
    lost = client.get(f"/api/computer/computer-use/jobs/{restart['id']}/screen")
    assert lost.status_code == 409
    assert lost.json()["error"]["code"] == "BROWSER_PAGE_LOST"
    again.join(timeout=20)
    assert runtime.jobs.detail(restart["id"])["state"] == "unknown"
    launches = runtime.jobs.computer_use.launches
    runtime.jobs.run_one()
    assert runtime.jobs.computer_use.launches == launches
    assert seen == []


def test_dead_page_hidden_context_and_deadline_do_not_open_another_browser(tmp_path):
    from desk.schemas import SettingsInput

    seen = []
    runtime, client, principal, clock = _world(tmp_path, seen)
    job = _prepare(
        runtime,
        principal,
        "live-dead",
        "demo:verification",
        "Stop at the password",
    )
    worker = threading.Thread(target=runtime.jobs.run_one, daemon=True)
    worker.start()
    paused = _wait_state(runtime, job["id"], "owner_takeover")
    assert paused["result"]["takeover_available"] is True
    live = runtime.jobs.computer_use.supervisor.live_page
    assert live is not None and live.alive()

    runtime.store.update_settings(
        SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True),
        "hide-live",
    )
    denied = client.get(f"/api/computer/computer-use/jobs/{job['id']}/screen")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "PRIVATE_CONTEXT_HIDDEN"
    assert not denied.content.startswith(b"\x89PNG")
    handed = _post(client, job["id"], "return", paused["version"], "hidden-return")
    assert handed.status_code == 403
    runtime.store.update_settings(
        SettingsInput(expected_version=2, timezone="Asia/Hong_Kong", hide_private=False),
        "show-live",
    )

    stranger = TestClient(client.app)
    stranger.cookies.set("desk_companion_session", runtime.store.create_owner_session())
    other = _post(stranger, job["id"], "takeover", paused["version"], "other-live")
    assert other.status_code == 403
    assert runtime.jobs.detail(job["id"])["state"] == "owner_takeover"

    _kill_chrome(live.channel.process.pid)
    lost = client.get(f"/api/computer/computer-use/jobs/{job['id']}/screen")
    assert lost.status_code == 409
    assert lost.json()["error"]["code"] == "BROWSER_PAGE_LOST"
    worker.join(timeout=20)
    unknown = runtime.jobs.detail(job["id"], review=True)
    assert unknown["state"] == "unknown"
    assert unknown["error"] == "BROWSER_PAGE_LOST"
    launches = runtime.jobs.computer_use.launches
    runtime.jobs.run_one()
    assert runtime.jobs.computer_use.launches == launches
    assert seen == []

    second = _prepare(
        runtime, principal, "live-expire", "demo:verification", "Stop at the password"
    )
    expirer = threading.Thread(target=runtime.jobs.run_one, daemon=True)
    expirer.start()
    waiting = _wait_state(runtime, second["id"], "owner_takeover")
    assert waiting["result"]["takeover_available"] is True
    runtime.store.logout(client.cookies.get("desk_companion_session"))
    revoked = client.get(f"/api/computer/computer-use/jobs/{second['id']}/screen")
    assert revoked.status_code == 403
    assert not revoked.content.startswith(b"\x89PNG")
    clock[0] += timedelta(seconds=181)
    expirer.join(timeout=20)
    expired = runtime.jobs.detail(second["id"], review=True)
    assert expired["state"] == "expired", expired
    assert seen == []
    assert runtime.jobs.computer_use.launches == launches + 1


def test_killing_the_worker_instead_of_chrome_keeps_cleanup_required(tmp_path):
    """Regression for the four-way COMPUTER_CLEANUP_REQUIRED failure.

    SIGKILL of every descendant (the old _kill_chrome fallback when /proc had not
    yet listed Chromium) stops the worker before cleanup is confirmed. Product
    correctly blocks the next prepare. Screen still reports BROWSER_PAGE_LOST.
    """
    from desk.store import DomainError

    seen = []
    runtime, client, principal, _clock = _world(tmp_path, seen)
    job = _prepare(
        runtime,
        principal,
        "cleanup-kill",
        "demo:verification",
        "Stop at the password",
    )
    worker = threading.Thread(target=runtime.jobs.run_one, daemon=True)
    worker.start()
    _wait_state(runtime, job["id"], "owner_takeover")
    live = runtime.jobs.computer_use.supervisor.live_page
    assert live is not None
    for child, _command in _descendants(live.channel.process.pid):
        try:
            os.kill(child, 9)
        except OSError:
            pass
    lost = client.get(f"/api/computer/computer-use/jobs/{job['id']}/screen")
    assert lost.status_code == 409
    assert lost.json()["error"]["code"] == "BROWSER_PAGE_LOST"
    worker.join(timeout=20)
    assert runtime.jobs.detail(job["id"])["error"] == "BROWSER_PAGE_LOST"
    assert runtime.jobs.computer_use.blocker.exists()
    with pytest.raises(DomainError, match="COMPUTER_CLEANUP_REQUIRED"):
        _prepare(runtime, principal, "blocked-next", "demo:verification", "Stop at the password")
    assert seen == []

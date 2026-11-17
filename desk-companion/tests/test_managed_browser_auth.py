"""Owner form admission, no credential persistence, and one-task resumption."""

import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import httpx

from desk.managed_browser import ManagedBrowserExecutor
from desk.managed_browser_auth import BrowserAuthInput, ManagedBrowserAuth, registered_form
from desk.store import DomainError
from desk.schemas import SettingsInput
import test_managed_browser as cases
from test_managed_browser import prepare, approve, result


@pytest.fixture(name="world")
def managed_world(tmp_path):
    return cases.world.__wrapped__(tmp_path)


FORM = {
    "type": "browser_authentication",
    "credential_origin": "https://books.toscrape.com",
    "reason": "Owner sign-in",
    "options": [],
    "fields": [{"id": "password", "label": "Password", "required": True, "type": "password"}],
}
SECRET = "fixture-private-password-DO-NOT-PERSIST"


def pending(world):
    r, provider, client, _ = world
    provider.auth_form = copy.deepcopy(FORM)
    job = prepare(world)
    approve(r, job)
    pool = ThreadPoolExecutor(max_workers=1)
    worker = pool.submit(r.jobs.run_one)
    try:
        deadline = time.monotonic() + 2
        while not (result(world, job).get("result") or {}).get("owner_input"):
            if worker.done():
                worker.result()
                pytest.fail(str(result(world, job)))
            assert time.monotonic() < deadline
            time.sleep(0.005)
        path = f"/api/computer/jobs/{job['id']}/authentication"
        response = client.get(path)
        assert response.status_code == 200
        form = response.json()
        payload = {
            "nonce": form["form"]["nonce"],
            "expected_version": form["version"],
            "action": "submit",
            "allow_account_access": True,
            "fields": [{"field_id": "password", "value": SECRET}],
        }
        return job, path, payload, worker, pool
    except BaseException:
        r.jobs.cancel(job["id"], "cleanup")
        pool.shutdown(wait=True)
        raise


def test_new_admission_defaults_to_managed_and_keeps_legacy_local(world, monkeypatch):
    r, provider, client, _ = world
    monkeypatch.delenv("DESK_MANAGED_BROWSER_ENABLED", raising=False)
    assert ManagedBrowserExecutor(r).enabled
    monkeypatch.setenv("DESK_MANAGED_BROWSER_ENABLED", "0")
    assert not ManagedBrowserExecutor(r).enabled
    body = {
        "title": "Books",
        "goal": "Compare prices",
        "start_url": FORM["credential_origin"],
        "public_only": True,
        "share_screen": True,
    }
    headers = {"X-Desk-Request": "1", "X-Operation-Id": "new-default"}
    response = client.post("/api/computer/browser-tasks", json=body, headers=headers)
    assert response.status_code == 200
    job = r.jobs.detail(response.json()["job"]["id"], review=True)
    assert job["request"]["engine"] == "managed"
    assert not provider.calls
    from desk.computer_use_models import ComputerUseInput

    assert ComputerUseInput.model_validate(body).engine == "local"


def test_empty_202_and_stream_recovery_never_resubmit_task_or_approval(world):
    r, p, _, _ = world
    p.empty_ack = p.drop_stream = True
    job = prepare(world)
    approve(r, job)
    r.jobs.run_one()
    assert result(world, job)["state"] == "succeeded"
    events = [
        call[2]["events"][0]
        for call in p.calls
        if call[0] == "POST" and call[1].endswith("/events")
    ]
    assert sum(e["type"] == "agent.session.input.message" for e in events) == 1
    assert sum(e["type"].endswith("approval_request_result") for e in events) == 1
    assert p.stream_count == 2 and p.deleted


def test_owner_form_resumes_same_job_without_persisting_secret(world):
    r, p, client, _ = world
    job, path, payload, worker, pool = pending(world)
    try:
        forbidden = {**payload, "allow_account_access": False}
        response = client.post(path, json=forbidden, headers={"X-Desk-Request": "1"})
        assert response.status_code == 409
        assert not p.auth_accepted
        response = client.post(path, json=payload, headers={"X-Desk-Request": "1"})
        assert response.status_code == 200 and response.json()["received"] is True
        assert SECRET not in response.text
        worker.result(timeout=3)
        done = result(world, job)
        assert done["state"] == "succeeded"
        assert done["result"]["readback"]["data_scope"] == "owner_authorized_account"
        assert not r.jobs.managed_browser.auth.form(job["id"])
        assert p.decisions[-1] == {
            "type": "browser_authentication",
            "action": "submit",
            "fields": [{"field_id": "password", "value": SECRET}],
        }
        assert sum(c[0] == "POST" and c[1].endswith("/sessions") for c in p.calls) == 1
        assert p.deleted
        # Includes SQLite/WAL, generated reports, job events and operation receipts.
        for file in r.store.directory.rglob("*"):
            if file.is_file():
                assert SECRET.encode() not in file.read_bytes(), file
        assert SECRET not in json.dumps(r.jobs.export())
        assert client.post(path, json=payload, headers={"X-Desk-Request": "1"}).status_code == 409
    finally:
        r.jobs.cancel(job["id"], "cleanup")
        pool.shutdown(wait=True)


@pytest.mark.parametrize(
    "mutation", ["other_owner", "hidden", "expired", "cancelled", "provider", "stale_form"]
)
def test_auth_input_is_fenced_before_credentials_reach_provider(world, mutation):
    r, p, client, _ = world
    job, path, payload, worker, pool = pending(world)
    try:
        if mutation == "other_owner":
            client.post(
                "/api/session",
                json={"username": "owner", "password": "fixture"},
                headers={"X-Desk-Request": "1"},
            )
        elif mutation == "hidden":
            r.store.update_settings(
                SettingsInput(expected_version=1, timezone="Asia/Hong_Kong", hide_private=True),
                "hide",
            )
        elif mutation == "expired":
            with r.store.connection(write=True) as conn:
                conn.execute("UPDATE sessions SET expires='2000-01-01'")
        elif mutation == "cancelled":
            r.jobs.cancel(job["id"], "stop")
        elif mutation == "provider":
            r.text_ai.config.model = "different-model"
        else:
            payload["nonce"] = "f" * 32
        response = client.post(path, json=payload, headers={"X-Desk-Request": "1"})
        assert response.status_code in {401, 403, 409}
        assert SECRET not in response.text
        assert not any(d.get("action") == "submit" for d in p.decisions)
    finally:
        r.jobs.cancel(job["id"], "cleanup")
        worker.result(timeout=3)
        pool.shutdown(wait=True)
        assert r.jobs.managed_browser.auth.form(job["id"]) is None


def test_form_receipt_retry_does_not_retain_or_reconsume_values():
    broker = ManagedBrowserAuth()
    action = {"request_id": "one", "request": FORM}
    nonce = broker.present("job", action, [FORM["credential_origin"]])
    payload = BrowserAuthInput(
        nonce=nonce,
        expected_version=1,
        action="submit",
        allow_account_access=True,
        fields=[{"field_id": "password", "value": SECRET}],
    )
    broker.submit("job", payload)
    assert SECRET not in repr(payload)
    assert broker.take("job", action)["fields"][0]["value"] == SECRET
    assert broker.submit("job", payload)["received"]
    assert broker.take("job", action) is None
    assert SECRET not in repr(broker.pending)
    changed = payload.model_copy(
        update={"action": "cancel", "fields": [], "allow_account_access": False}
    )
    with pytest.raises(DomainError, match="ALREADY_SUBMITTED"):
        broker.submit("job", changed)
    next_action = {"request_id": "two", "request": FORM}
    broker.present("job", next_action, [FORM["credential_origin"]])
    with pytest.raises(DomainError, match="AUTH_CHANGED"):
        broker.submit("job", payload)


def test_missed_terminal_event_recovers_saved_turn_and_activity(world):
    r, p, _, _ = world
    p.miss_terminal_event = True
    job = prepare(world)
    approve(r, job)
    r.jobs.run_one()
    assert result(world, job)["state"] == "succeeded"
    assert p.deleted and p.stream_count == 2


def test_delete_reply_loss_can_be_verified_without_recreating_session(world):
    r, p, _, _ = world

    async def transport(request):
        response = await p(request)
        if request.method == "DELETE":
            raise httpx.ReadTimeout("Fixture lost deletion reply", request=request)
        return response

    r.text_ai.transport = httpx.MockTransport(transport)
    job = prepare(world)
    approve(r, job)
    r.jobs.run_one()
    assert result(world, job)["state"] == "succeeded"
    assert not r.jobs.managed_browser.blocker.exists()
    assert sum(c[0] == "DELETE" for c in p.calls) == 1


def test_cancel_auth_prompt_uses_cancel_without_account_scope(world):
    r, p, client, _ = world
    job, path, payload, worker, pool = pending(world)
    try:
        payload.update(action="cancel", fields=[], allow_account_access=False)
        assert client.post(path, json=payload, headers={"X-Desk-Request": "1"}).status_code == 200
        worker.result(timeout=3)
        assert result(world, job)["result"]["readback"]["data_scope"] == "public_pages"
        assert p.decisions[-1] == {"type": "browser_authentication", "action": "cancel"}
        assert p.deleted
    finally:
        r.jobs.cancel(job["id"], "cleanup")
        pool.shutdown(wait=True)


def test_abandoned_auth_form_expires_and_deletes_remote_session(world):
    r, p, _, _ = world
    job, _, _, worker, pool = pending(world)
    try:
        worker.result(timeout=3)
        assert result(world, job)["error"] == "JOB_DEADLINE_EXCEEDED"
        assert not p.auth_accepted and p.deleted
        assert r.jobs.managed_browser.auth.form(job["id"]) is None
    finally:
        pool.shutdown(wait=True)


def test_lost_provider_auth_reply_keeps_account_scope_and_never_retries(world):
    r, p, client, _ = world

    async def transport(request):
        response = await p(request)
        if request.method == "POST" and request.url.path.endswith("/events"):
            event = json.loads(request.content)["events"][0]
            if event.get("response", {}).get("action") == "submit":
                raise httpx.ReadTimeout("Fixture lost auth response", request=request)
        return response

    r.text_ai.transport = httpx.MockTransport(transport)
    job, path, payload, worker, pool = pending(world)
    try:
        assert client.post(path, json=payload, headers={"X-Desk-Request": "1"}).status_code == 200
        worker.result(timeout=3)
        assert result(world, job)["state"] == "failed"
        saved = json.loads((r.jobs.managed_browser.root / job["id"] / "managed-result.json").read_text())
        assert saved["account_access_authorized"] is True
        assert saved["turn_completed"] is False
        assert p.deleted and sum(d.get("action") == "submit" for d in p.decisions) == 1
    finally:
        r.jobs.cancel(job["id"], "cleanup")
        pool.shutdown(wait=True)


@pytest.mark.parametrize(
    "change",
    [
        {"credential_origin": None},
        {"credential_origin": "https://another.example"},
        {"fields": [{"id": "qr", "label": "QR", "required": True, "type": "qrcode"}]},
        {"options": [{"id": "x", "label": "x", "field_ids": ["missing"]}]},
    ],
)
def test_unregistered_or_unadmitted_form_cannot_collect_credentials(change):
    with pytest.raises(DomainError):
        registered_form({"request": {**FORM, **change}}, [FORM["credential_origin"]])

"""Behavioral release checks for model routing and the dated fleet spending allocation."""

import concurrent.futures
import json
from datetime import datetime, timedelta

import httpx
import pytest

from desk.managed_browser import ManagedBrowserExecutor
from desk.openai_live import OpenAILiveProtocol
from desk.openai_spend import DailySpend, HONG_KONG, USD, budgeted_response, provision
from desk.provider_policy import OPENAI_TEXT_ENDPOINT
from desk.store import DomainError
from desk.text_ai import TextConfig
from desk.voice import VoiceConfig
from test_managed_browser import FastClient, approve, prepare, result, world as world


def ledger(tmp_path, *, share=9 * USD, opening=0):
    clock = [datetime(2026, 11, 18, 12, tzinfo=HONG_KONG)]
    f = tmp_path / "private" / "daily.sqlite3"
    provision(f, start="2026-11-18", through="2026-11-24", share=share, opening=opening)
    return DailySpend(f, lambda: clock[0]), clock


def test_model_on_approved_hosted_request_is_the_selected_browser_model(world, monkeypatch):
    r, provider, _, _ = world
    monkeypatch.setenv("DESK_MANAGED_BROWSER_MODEL", "gpt-6.2-sol")
    r.jobs.managed_browser = ManagedBrowserExecutor(r)
    r.jobs.managed_browser.client_factory = FastClient
    browser = r.jobs.managed_browser
    assert r.text_ai.config.model == "gpt-6.1-sol"
    assert browser.status()["model"] == "gpt-6.2-sol" and browser.status()["configured"]
    job = prepare(world)
    approve(r, job)
    r.jobs.run_one()
    assert result(world, job)["state"] == "succeeded"
    creates = [
        body
        for method, path, body in provider.calls
        if method == "POST" and path.endswith("/agents/sessions")
    ]
    assert len(creates) == 1 and creates[0]["agent"]["model"] == "gpt-6.2-sol"
    assert creates[0]["environment"]["network"] == {
        "access": "restricted",
        "allowed_domains": ["books.toscrape.com"],
    }
    assert creates[0]["agent"]["service_tier"] == "default"
    assert browser.verify(result(world, job)["request"])["verified"]


def test_changed_browser_model_invalidates_old_job_and_unknown_models_fail_closed(world):
    r, provider, _, _ = world
    job = prepare(world)
    approve(r, job)
    r.jobs.managed_browser.model_override = "gpt-6.2-sol"
    r.jobs.run_one()
    assert result(world, job)["state"] in {"failed", "cancelled"} and not provider.calls
    r.jobs.managed_browser.model_override = "unreviewed-model"
    assert not r.jobs.managed_browser.status()["configured"]


def test_live_voice_uses_audio_model_and_new_delegation(monkeypatch):
    for k in (
        "DESK_TEXT_MODEL",
        "DESK_VOICE_PROVIDER",
        "DESK_VOICE_MODEL",
        "DESK_LIVE_BACKEND_MODEL",
        "DESK_TEXT_PROVIDER",
    ):
        monkeypatch.delenv(k, raising=False)
    cfg = VoiceConfig.environment()
    body = OpenAILiveProtocol().setup(cfg, "test")["session"]
    assert (
        body["model"] == "gpt-live-1.1" and body["delegation"]["responses"]["model"] == "gpt-6.2-sol"
    )
    assert TextConfig.environment().model == "gpt-6.2-sol"


def test_daily_racing_claims_restart_unknown_receipts_and_expiry(tmp_path):
    b, clock = ledger(tmp_path, share=1_000_000, opening=100_000)

    def claim(i):
        try:
            b.reserve(str(i), "trial", 300000)
            return 1
        except DomainError:
            return 0

    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        assert sum(pool.map(claim, range(12))) == 3
    assert b.summary()["available_usd"] == 0
    provision(b.path, start="2026-11-18", through="2026-11-24", share=1_000_000, opening=100_000)
    assert DailySpend(b.path, lambda: clock[0]).summary()["accounted_usd"] == 1
    with pytest.raises(ValueError):
        provision(b.path, start="2026-11-18", through="2026-12-24", share=USD)
    clock[0] += timedelta(days=1)
    b.reserve("next", "trial", 10000)
    clock[0] -= timedelta(days=1)
    with pytest.raises(DomainError, match="PERIOD_CLOSED"):
        b.reserve("rollback", "trial", 1)
    clock[0] = datetime(2026, 11, 24, 23, 59, 45, tzinfo=HONG_KONG)
    with pytest.raises(DomainError, match="DAY_END"):
        b.reserve("cross", "trial", 100, seconds=60)
    clock[0] += timedelta(minutes=1)
    with pytest.raises(DomainError, match="PERIOD_CLOSED"):
        b.reserve("expired", "trial", 100)
    clock[0] -= timedelta(hours=1)
    with pytest.raises(DomainError, match="PERIOD_CLOSED"):
        b.reserve("rewind", "trial", 100)


def test_complete_group_receipt_is_idempotent_and_unknown_hosted_cost_stays_held(tmp_path):
    b, _ = ledger(tmp_path)
    b.reserve("input", "session", 80000, scope="x")
    b.reserve("func", "session", 80000, scope="x")
    b.usage(["input", "func"], None, final=True)
    assert b.summary()["accounted_usd"] == 0.16
    b.usage(["input", "func"], 30000, final=True)
    b.usage(["input", "func"], 20000, final=True)
    assert b.summary()["accounted_usd"] == 0.03
    b.reserve("browser", "hosted", 2 * USD)
    b.usage(["browser"], 1000, final=True, retain=True)
    assert b.summary()["accounted_usd"] == 2.03
    with pytest.raises(DomainError, match="BUDGET_REACHED"):
        b.reserve("over", "session", 230000, scope="x")


def test_responses_file_input_is_counted_before_money_or_model_dispatch(tmp_path):
    b, _ = ledger(tmp_path, share=500000)
    paths = []

    def mock(req):
        paths.append(req.url.path)
        if paths[-1].endswith("/input_tokens"):
            return httpx.Response(200, json={"input_tokens": 200000})
        pytest.fail("unfunded request dispatched")

    with (
        httpx.Client(transport=httpx.MockTransport(mock)) as c,
        pytest.raises(DomainError, match="BUDGET_REACHED"),
    ):
        budgeted_response(
            c,
            OPENAI_TEXT_ENDPOINT,
            headers={},
            json_body={
                "model": "gpt-6.2-sol",
                "input": "fixture",
                "max_output_tokens": 1600,
                "store": False,
            },
            budget=b,
        )
    assert paths == ["/v1/responses/input_tokens"] and b.summary()["accounted_usd"] == 0


def test_missing_configured_ledger_never_allows_paid_work(tmp_path):
    b = DailySpend(tmp_path / "absent.sqlite3", lambda: datetime.now(HONG_KONG))
    with pytest.raises(DomainError, match="BUDGET_UNAVAILABLE"):
        b.reserve("id", "trial", USD)
    assert not b.path.exists()


def test_ordinary_session_uses_active_allocation_and_stops_before_second_create(tmp_path):
    from desk.app import create_app
    from fastapi.testclient import TestClient
    from session_protocol_fixture import install_session_protocol

    budget, clock = ledger(tmp_path, share=100000)
    app = create_app(
        tmp_path / "runtime", password="fixture", scheduler=False, clock=lambda: clock[0]
    )
    r = app.state.runtime
    r.openai_spend = budget
    provider = install_session_protocol(r)
    r.text_ai.config.model = "gpt-6.2-sol"
    c = TestClient(app)
    assert c.post(
        "/api/session",
        json={"username": "owner", "password": "fixture"},
        headers={"X-Desk-Request": "1"},
    ).is_success

    def send(key):
        return c.post(
            "/api/assistant/messages",
            json={"message": "Explain my desk setting."},
            headers={"X-Desk-Request": "1", "X-Operation-Id": key},
        ).json()

    assert send("one")["message"] == provider.final
    assert len(provider.creations) == 1
    create = provider.creations[0]
    assert "spend_control" not in create and create["agent"]["model"] == "gpt-6.2-sol"
    budget.reserve("other", "shared", 90000, seconds=1)
    assert send("two")["error"] == "OPENAI_DAILY_BUDGET_REACHED"
    assert len(provider.creations) == 1


def test_hosted_browser_without_funds_never_creates_remote_environment(world, tmp_path):
    r, provider, _, _ = world
    b, _ = ledger(tmp_path, share=1_000_000)
    r.openai_spend = b
    job = prepare(world)
    approve(r, job)
    r.jobs.run_one()
    assert not provider.calls and result(world, job)["state"] == "failed"
    assert b.summary()["accounted_usd"] == 0


def test_live_spend_counts_delegated_tokens_and_conservative_voice_seconds():
    from desk.openai_spend import voice_estimate

    usage = {
        "backend_input_tokens": 10000,
        "backend_output_tokens": 1000,
        "voice_seconds": 60,
        "backend_receipts_complete": 1,
        "finalization_confirmed": 1,
    }
    assert voice_estimate(usage, 30) == 121000
    assert voice_estimate(usage, 120) == 176000


def test_ledger_backed_local_computer_observation_counts_and_dispatches_to_same_provider(tmp_path):
    from desk.computer_use_protocol import OpenAIComputerProtocol

    paths = []

    def dispatch(request):
        paths.append((request.url.path, json.loads(request.content)["model"]))
        if request.url.path.endswith("/input_tokens"):
            return httpx.Response(200, json={"input_tokens": 120})
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": "Observed"}]}
                ],
                "usage": {"input_tokens": 120, "output_tokens": 10},
            },
        )

    cfg = TextConfig("openai", "gpt-6.2-sol", OPENAI_TEXT_ENDPOINT, "dummy-only")
    protocol = OpenAIComputerProtocol(
        cfg, "Read the supplied screen", [], transport=httpx.MockTransport(dispatch)
    )
    protocol.spend_budget, _ = ledger(tmp_path)
    got = protocol.step(
        {"url": "about:blank", "title": "FYP fixture", "text": ""},
        b"fixture image bytes",
        lambda: None,
    )
    assert got["finish"] is True
    assert paths == [
        ("/v1/responses/input_tokens", "gpt-6.2-sol"),
        ("/v1/responses", "gpt-6.2-sol"),
    ]
    assert 0 < protocol.spend_budget.summary()["accounted_usd"] < 0.01


def test_live_voice_budget_denial_precedes_any_provider_connection(tmp_path):
    import asyncio
    import time
    from desk.app import create_app
    from desk.openai_live import OPENAI_LIVE_ENDPOINT
    from voice_fixtures import Socket

    budget, clock = ledger(tmp_path, share=1000000)
    r = create_app(
        tmp_path / "voice-runtime", clock=lambda: clock[0], password="fixture", scheduler=False
    ).state.runtime
    r.openai_spend = budget
    r.voice.config = VoiceConfig(
        "openai_live", OPENAI_LIVE_ENDPOINT, "gpt-live-1", "fixture-only", "marin"
    )
    r.voice.connector = lambda *_a, **_k: pytest.fail(
        "Unaffordable voice websocket reached the provider"
    )
    principal = {"kind": "owner", "id": "owner", "session": r.store.create_owner_session()}

    async def run():
        sock = Socket()
        r.voice.active, r.voice.started = True, time.monotonic()
        await r.voice.run(sock, principal, "en", "voice")
        assert any(e.get("code") == "OPENAI_DAILY_BUDGET_REACHED" for e in sock.messages)
        assert not r.voice.active

    asyncio.run(run())
    assert budget.summary()["accounted_usd"] == 0

from datetime import UTC, datetime
import json
import pytest
import httpx
import test_managed_browser as managed_cases

from desk.browser_research import BrowserResearchDraft
from desk.commerce_quotes import read_quote
from desk.flight_search import recorded_quote, search_arguments
from desk.managed_session_config import managed_session
from desk.openai_cost_statement import parse_statement
from desk.openai_spend import DailySpend, managed_estimate, provision, token_estimate

managed_world = managed_cases.world

SPEC = {
    "kind": "flight",
    "origin": "HKG",
    "destination": "HND",
    "departure": "2026-11-25",
    "adults": 1,
    "checked_bag_kg": 20,
    "currency": "HKD",
    "budget_minor": 150000,
    "provider": "kiwi",
    "nonstop": True,
}
LEG = {
    "route": ["HKG", "HND"],
    "departureTime": "2026-11-25T19:55:00",
    "arrivalTime": "2026-11-26T00:45:00",
    "segments": [{"flightNumber": "UO628", "from": "HKG", "to": "HND", "carrier": "UO"}],
}
ITEM = {
    "tripType": "oneway",
    "price": 2005.999998,
    "outbound": LEG,
    "inbound": None,
    "baggage": {"checkedBag": 1.0},
    "bookingUrl": "https://kiwi.com/u/test123",
}


def draft():
    return BrowserResearchDraft(
        title="Find flights",
        goal="Compare these fares",
        start_url="https://www.kiwi.com/",
        quote_request=SPEC,
    ).intent().model_dump() | {"artifact_id": "a" * 32}


def call(rows):
    data = {
        "currency": "HKD",
        "passengers": {"adults": 1, "children": 0, "infants": 0},
        "itineraries": rows,
    }
    return {
        "type": "mcp_call",
        "name": "search-flight",
        "server_label": "kiwi",
        "status": "completed",
        "turn_id": "t",
        "error": None,
        "arguments": search_arguments(SPEC),
        "output": {"structuredContent": data},
    }


def test_connector_matches_actual_fare_and_preserves_unknown_weight():
    req = draft()
    conf, extra = managed_session(req, "gpt-6.2-sol")
    assert conf["environment"] == {"type": "none"} and extra is None
    assert req["share_screen"] is False
    assert conf["agent"]["tools"][0]["allowed_tools"] == ["search-flight"]
    assert json.loads(conf["input"][0]["content"][0]["text"])["adults_hold_bags"] == [1]
    wrong_dest = {**ITEM, "outbound": {**LEG, "route": ["HKG", "NRT"]}, "price": 100}
    r = recorded_quote([call([wrong_dest, ITEM])], req, "t")
    card = read_quote(req, json.dumps(r), "2026-11-19T01:00:00Z")
    assert card["offer"]["price_minor"] == 200600 and card["subtotal_minor"] == 200600
    assert card["total_minor"] is None and card["budget_status"] == "over"
    assert card["offer"]["checked_bag_kg_per_adult"] is None
    for count in (True, "1", 1.5):
        assert (
            recorded_quote([call([{**ITEM, "baggage": {"checkedBag": count}}])], req, "t")["offer"]
            is None
        )
    assert (
        recorded_quote(
            [call([{**ITEM, "bookingUrl": "https://other.example/u/test123"}])], req, "t"
        )["offer"]
        is None
    )
    with pytest.raises(ValueError):
        recorded_quote([{**call([ITEM]), "name": "feedback-to-devs"}], req, "t")
    with pytest.raises(ValueError):
        recorded_quote([{**call([ITEM]), "arguments": {}}], req, "t")


def test_costs_export_is_a_separate_utc_observation(tmp_path):
    stamp = int(datetime(2026, 11, 19, tzinfo=UTC).timestamp())
    csv = f"start_time,end_time,amount_value,amount_currency\n{stamp},{stamp + 86400},0.123456789,usd\n".encode()
    path = tmp_path / "private" / "ledger.sqlite"
    provision(path, start="2026-11-19", through="2026-11-24", share=9_000_000)
    ledger = DailySpend(path, lambda: datetime(2026, 11, 19, 2, tzinfo=UTC))
    ledger.reserve("b", "hosted_browser", 2_000_000)
    first = ledger.import_cost_statement(csv, "All projects")
    assert first == ledger.import_cost_statement(csv, "All projects")
    view = ledger.summary()
    assert view["reserved_or_unpriced_usd"] == 2 and view["available_usd"] == 7
    assert view["last_platform_statement"]["amount_usd"] == "0.123456789"
    with pytest.raises(ValueError):
        parse_statement(csv.replace(b"usd", b"eur"))


def test_only_final_usage_can_release_a_managed_hold():
    u = {
        "input_tokens": 10000,
        "input_tokens_details": {"cached_tokens": 9000},
        "output_tokens": 100,
    }
    assert token_estimate(u) == 7590
    assert token_estimate({**u, "input_tokens_details": {"cached_tokens": 10001}}) == 56100
    result = {
        "terminal_usage": u,
        "deletion_readback": True,
        "turn_completed": True,
        "elapsed_seconds": 60,
    }
    assert managed_estimate({**result, "environment": "none"}, True) == 7590
    assert managed_estimate({**result, "environment_size": "small"}, False) == 67590
    assert managed_estimate({**result, "environment": "none", "terminal_usage": None}, True) is None
    assert (
        managed_estimate({**result, "environment_size": "small", "deletion_readback": False}, False)
        is None
    )


def test_fleet_allocation_is_dated_and_reservations_keep_their_limit(tmp_path):
    from datetime import timedelta
    from desk.store import DomainError

    path = tmp_path / "state" / "ledger.sqlite"
    now = [datetime(2026, 11, 19, 2, tzinfo=UTC)]
    provision(path, start="2026-11-19", through="2026-11-24", share=9_000_000)
    ledger = DailySpend(path, lambda: now[0])
    ledger.reserve("prior", "hosted_browser", 8_810_000)
    ledger.reserve("flight", "flight_mcp", 250_000)
    assert ledger.summary()["available_usd"] == 0
    with pytest.raises(DomainError):
        ledger.reserve("next", "flight_mcp", 250_000)
    with pytest.raises(ValueError):
        ledger.allocate_today(
            local=11_000_000, other_devices=9_000_000, margin=1_000_000, reason="over total"
        )
    ledger.allocate_today(
        local=10_000_000, other_devices=9_000_000, margin=1_000_000, reason="active desk"
    )
    ledger.allocate_today(
        local=10_000_000, other_devices=9_000_000, margin=1_000_000, reason="active desk"
    )
    view = ledger.summary()
    assert view["available_usd"] == 1 and view["local_budget_used_usd"] == 9
    now[0] += timedelta(days=1)
    assert ledger.summary()["allocated_usd"] == 9


def test_orphan_cost_read_cannot_stop_remote_deletion():
    import time
    from desk.openai_sessions import SessionAPI
    from desk.text_ai import TextConfig

    deleted = []

    def handle(req):
        if req.method == "DELETE":
            deleted.append(True)
            return httpx.Response(200, json={"deleted": True})
        return (
            httpx.Response(404)
            if deleted
            else httpx.Response(200, json={"id": "sess_a", "status": "idle"})
        )

    api = SessionAPI(
        TextConfig("openai", "gpt-6.2-sol", "https://api.openai.com/v1/responses", "fake"),
        httpx.MockTransport(handle),
        deadline=time.monotonic() + 10,
    )

    def failed_meter():
        raise RuntimeError("cost receipt unavailable")

    try:
        assert api.close_remote("sess_a", before_delete=failed_meter)
        assert deleted == [True]
    finally:
        api.client.close()


def test_managed_browser_uses_named_terminal_turn_and_small_container(managed_world, tmp_path):
    runtime, provider, _, _ = managed_world
    path = tmp_path / "meter" / "day.sqlite"
    provision(path, start="2026-11-19", through="2026-11-19", share=9_000_000)
    runtime.openai_spend = DailySpend(path, lambda: datetime(2026, 11, 19, 2, tzinfo=UTC))
    late = []

    async def wire(req):
        if req.url.path.endswith("/turns/turn-1"):
            late.append(1)
            return httpx.Response(
                200,
                json={
                    "id": "turn-1",
                    "status": "completed",
                    "usage": (
                        {"input_tokens": 1000, "output_tokens": 20} if len(late) == 2 else None
                    ),
                },
            )
        response = await provider(req)
        if req.method == "POST" and req.url.path.endswith("/sessions"):
            body = response.json()
            body["environment"]["container_size"] = "small"
            return httpx.Response(201, json=body)
        return response

    runtime.text_ai.transport = httpx.MockTransport(wire)
    job = managed_cases.prepare(managed_world)
    managed_cases.approve(runtime, job)
    runtime.jobs.run_one()
    assert runtime.jobs.detail(job["id"])["state"] == "succeeded"
    assert len(late) == 2 and provider.deleted
    assert runtime.openai_spend.summary()["observed_usage_estimate_usd"] == 0.06572

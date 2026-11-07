import json

import httpx
import pytest

from scripts.live_eval_budget import BudgetTransport, CEILING, EvalBudget, EvalStopped, MODEL


def test_unknown_attempt_survives_reopen_and_prevents_overspend(tmp_path):
    budget = EvalBudget(tmp_path / "cost.sqlite3")
    budget.reserve("test", b"one", 120000, 1600)
    budget = EvalBudget(tmp_path / "cost.sqlite3")
    with pytest.raises(EvalStopped, match="UNRECONCILED"):
        budget.reserve("test", b"two", 120000, 1600)
    assert budget.snapshot()["unreconciled_requests"] == 1
    budget.close()
    with pytest.raises(EvalStopped, match="EXHAUSTED|UNRECONCILED"):
        EvalBudget(budget.path).reserve("test", b"three", 1, 16)


def test_receipt_releases_only_unused_hold_and_rejects_duplicate(tmp_path):
    budget = EvalBudget(tmp_path / "cost.sqlite3")
    request_id = budget.reserve("test", b"one", 1000, 1600)
    budget.finish(
        request_id,
        {
            "model": MODEL,
            "service_tier": "default",
            "usage": {"input_tokens": 1000, "output_tokens": 40},
        },
    )
    assert budget.snapshot()["conservative_accounted_usd"] == (1000 * 5500 + 40 * 11000) / 1e9
    with pytest.raises(EvalStopped, match="FINAL"):
        budget.finish(request_id, {"usage": {}})


def test_unexpected_model_closes_round_and_retains_hold(tmp_path):
    budget = EvalBudget(tmp_path / "cost.sqlite3")
    request_id = budget.reserve("test", b"one", 100, 1600)
    before = budget.snapshot()["conservative_accounted_usd"]
    budget.finish(
        request_id, {"model": "other", "usage": {"input_tokens": 10, "output_tokens": 10}}
    )
    after = budget.snapshot()
    assert after["closed"] and after["conservative_accounted_usd"] == before


def test_cache_receipts_keep_highest_write_rate_and_validate_breakdown(tmp_path):
    budget = EvalBudget(tmp_path / "cost.sqlite3")
    identity = budget.reserve("test", b"one", 1000, 1600)
    budget.finish(
        identity,
        {
            "model": MODEL,
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 40,
                "input_tokens_details": {"cached_tokens": 700, "cache_write_tokens": 200},
            },
        },
    )
    assert (
        budget.snapshot()["conservative_accounted_usd"]
        == (700 * 110 + 200 * 5500 + 100 * 2200 + 40 * 11000) / 1e9
    )
    identity = budget.reserve("test", b"two", 1000, 1600)
    budget.finish(
        identity,
        {
            "model": MODEL,
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 40,
                "input_tokens_details": {"cached_tokens": 900, "cache_write_tokens": 200},
            },
        },
    )
    assert budget.snapshot()["closed"]


def test_token_count_then_one_request_and_no_retry_after_uncertain_transport(tmp_path):
    seen = []

    def network(request):
        seen.append(request.url.path)
        if request.url.path.endswith("/input_tokens"):
            assert "max_output_tokens" not in json.loads(request.content)
            return httpx.Response(200, json={"input_tokens": 120000})
        assert json.loads(request.content)["service_tier"] == "default"
        raise httpx.ReadTimeout("uncertain sent request")

    budget = EvalBudget(tmp_path / "cost.sqlite3")
    transport = BudgetTransport(budget, "test", proxy="", upstream=httpx.MockTransport(network))
    body = {"model": MODEL, "input": "synthetic", "max_output_tokens": 1600, "store": False}
    with httpx.Client(transport=transport, trust_env=False) as client:
        with pytest.raises(httpx.ReadTimeout):
            client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": "Bearer fake"},
                json=body,
            )
        with pytest.raises(EvalStopped, match="UNRECONCILED"):
            client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": "Bearer fake"},
                json=body,
            )
    assert seen.count("/v1/responses") == 1
    assert budget.snapshot()["conservative_accounted_usd"] < CEILING / 1e9


def test_counter_failure_never_calls_generation(tmp_path):
    seen = []

    def network(request):
        seen.append(request.url.path)
        return httpx.Response(400, json={"error": {"code": "invalid_parameter", "param": "input"}})

    transport = BudgetTransport(
        EvalBudget(tmp_path / "cost.sqlite3"),
        "test",
        proxy="",
        upstream=httpx.MockTransport(network),
    )
    with httpx.Client(transport=transport, trust_env=False) as client:
        with pytest.raises(EvalStopped, match="COUNT_FAILED"):
            client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": "Bearer fake"},
                json={"model": MODEL, "input": "test", "max_output_tokens": 1600, "store": False},
            )
    assert seen == ["/v1/responses/input_tokens"] and transport.budget.snapshot()["requests"] == 0

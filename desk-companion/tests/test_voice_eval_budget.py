import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from scripts.voice_eval.budget import Budget, token_cost


def test_unknown_usage_keeps_reservation_across_restart(tmp_path):
    b = Budget(tmp_path / "budget.db")
    b.reserve("a", "gpt-live-1", 4)
    b.finish("a", estimate=0.02, finalized=False, result={"closed": False})
    reopened = Budget(b.path)
    assert reopened.snapshot()["accounted_usd"] == 4
    with pytest.raises(ValueError, match="BUDGET_EXHAUSTED"):
        reopened.reserve("b", "gpt-live-1", 1.01)
    with pytest.raises(ValueError, match="RUN_ALREADY_FINAL"):
        reopened.finish("a", estimate=0, finalized=True, result={"closed": True})


def test_atomic_reservation_and_duplicate_keys(tmp_path):
    b = Budget(tmp_path / "budget.db")

    def reserve(key):
        try:
            b.reserve(key, "gpt-live-1", 3)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(2) as executor:
        assert sum(executor.map(reserve, ["a", "b"])) == 1
    existing = b.snapshot()["runs"][0]["id"]
    with pytest.raises(sqlite3.IntegrityError):
        b.reserve(existing, "gpt-live-1", 0.1)


def test_known_usage_releases_unused_reservation(tmp_path):
    b = Budget(tmp_path / "budget.db")
    b.reserve("a", "gpt-live-1", 5)
    b.finish("a", estimate=0.05, finalized=True, result={"seconds": 60})
    b.reserve("b", "gpt-live-1", 4.95)
    assert b.snapshot()["accounted_usd"] == 5


def test_observed_overrun_does_not_allow_more_reservations(tmp_path):
    b = Budget(tmp_path / "budget.db")
    b.reserve("a", "gpt-live-1", 1)
    b.finish("a", estimate=4, finalized=False, result={"closed": False})
    with pytest.raises(ValueError, match="BUDGET_EXHAUSTED"):
        b.reserve("b", "gpt-live-1", 1.01)


def test_closing_round_blocks_further_spending_but_preserves_receipts(tmp_path):
    b = Budget(tmp_path / "budget.db")
    b.reserve("a", "gpt-live-1", 0.25)
    b.close()
    reopened = Budget(b.path)
    with pytest.raises(ValueError, match="EXPERIMENT_CLOSED"):
        reopened.reserve("b", "gpt-live-1", 0.1)
    reopened.finish("a", estimate=0.02, finalized=True, result={"closed": True})
    assert reopened.snapshot()["closed"] is True
    assert reopened.snapshot()["accounted_usd"] == 0.02


@pytest.mark.parametrize("bad", [0, -1, float("nan"), float("inf"), 6])
def test_invalid_reservations_fail_closed(tmp_path, bad):
    with pytest.raises(ValueError):
        Budget(tmp_path / "budget.db").reserve("bad", "gpt-live-1", bad)


def test_modality_rates_and_conservative_missing_details():
    usage = {
        "input_tokens": 1100,
        "input_token_details": {"text_tokens": 100, "audio_tokens": 1000},
        "output_tokens": 200,
        "output_token_details": {"text_tokens": 50, "audio_tokens": 150},
    }
    assert token_cost("gpt-realtime-2.1", usage) == pytest.approx(0.0432)
    assert token_cost("gpt-realtime-2.1", {"input_tokens": 100}) == 0.0032
    assert token_cost("gpt-6-luna", {"input_tokens": 1000, "output_tokens": 100}) == 0.00015
    assert (
        token_cost(
            "gpt-6-luna",
            {"input_tokens": 1000, "input_tokens_details": {"cache_write_tokens": 1000}},
        )
        == 0.00025
    )


def test_smaller_budget_is_durable_and_cannot_be_increased(tmp_path):
    from scripts.voice_eval.budget import Budget

    path = tmp_path / "small.sqlite3"
    first = Budget(path, ceiling=1)
    first.reserve("one", "gpt-live-1", 0.95)
    reopened = Budget(path)
    assert reopened.snapshot()["ceiling_usd"] == 1
    with pytest.raises(ValueError, match="BUDGET_POLICY_CHANGED"):
        Budget(path, ceiling=2)
    with pytest.raises(ValueError, match="BUDGET_EXHAUSTED"):
        reopened.reserve("two", "gpt-live-1", 0.1)
    first.close()
    assert Budget(path).snapshot()["closed"]

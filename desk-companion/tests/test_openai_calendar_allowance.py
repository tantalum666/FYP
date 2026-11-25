from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from desk.openai_calendar_allowance import renew
from desk.openai_spend import DailySpend, HONG_KONG, USD, provision
from desk.store import DomainError


def test_successor_limits_share_one_ledger_and_keep_old_receipts(tmp_path):
    at = [datetime(2026, 11, 24, 15, tzinfo=HONG_KONG)]
    path = tmp_path / "term" / "budget.db"
    provision(path, start="2026-11-01", through="2026-11-24", share=9 * USD)
    ledger = DailySpend(path, lambda: at[0])
    ledger.reserve("previous", "responses", 2 * USD)
    terms = dict(
        start="2026-11-25",
        through="2027-05-24",
        daily=10 * USD,
        monthly=200 * USD,
        day_opening=USD,
        month_opening=195 * USD,
        statement="e" * 64,
    )
    renew(ledger, **terms)
    with ledger._db() as db:
        assert (
            db.execute("SELECT through FROM allowance").fetchone()[0] == "2026-11-24"
        )  # rollback fails closed
    at[0] = datetime(2026, 11, 25, 15, tzinfo=HONG_KONG)
    assert ledger.summary()["available_usd"] == 3

    def attempt(key):
        try:
            ledger.reserve(key, "responses", 2 * USD)
            return True
        except DomainError as e:
            assert e.code == "OPENAI_MONTHLY_BUDGET_REACHED"
            return False

    with ThreadPoolExecutor(2) as pool:
        assert sum(pool.map(attempt, ("parallel-a", "parallel-b"))) == 1
    renew(ledger, **terms)
    assert DailySpend(path, lambda: at[0]).summary()["available_usd"] == 1
    ledger.usage(["previous"], USD, final=True)
    assert ledger.summary()["prior_unpriced_reserve_usd"] == 0
    with pytest.raises(DomainError, match="OPENAI_BUDGET_TERM_CONFLICT"):
        renew(ledger, **{**terms, "monthly": 201 * USD})
    at[0] = datetime(2026, 12, 1, 0, 1, tzinfo=HONG_KONG)
    assert ledger.summary()["monthly_available_usd"] == 200
    ledger.reserve("december", "responses", 10 * USD)
    with pytest.raises(DomainError, match="OPENAI_DAILY_BUDGET_REACHED"):
        ledger.reserve("extra", "responses", 1)
    at[0] = datetime(2027, 5, 25, 0, 0, tzinfo=HONG_KONG)
    with pytest.raises(DomainError, match="OPENAI_BUDGET_PERIOD_CLOSED"):
        ledger.reserve("expired", "responses", 1)
    assert ledger.summary()["available_usd"] == 0
    at[0] = datetime(2027, 5, 24, 12, tzinfo=HONG_KONG)
    with pytest.raises(DomainError, match="OPENAI_BUDGET_PERIOD_CLOSED"):
        ledger.reserve("clock-rollback", "responses", 1)

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
from desk.openai_calendar_allowance import renew, reserve_device_share
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


def test_device_share_is_debited_once_before_peer_activation(tmp_path):
    now = [datetime(2030, 4, 5, 10, tzinfo=HONG_KONG)]
    ledgers = []
    for name in ("primary", "secondary"):
        path = tmp_path / name / "budget.db"
        provision(path, start="2030-04-01", through="2030-04-03", share=5 * USD)
        ledgers.append(DailySpend(path, lambda: now[0]))
    primary, secondary = ledgers
    term = dict(
        start="2030-04-04",
        through="2030-05-31",
        daily=6 * USD,
        monthly=28 * USD,
        day_opening=0,
        month_opening=12 * USD,
        statement="a" * 64,
    )
    renew(primary, **term)
    primary.reserve("existing-hold", "responses", 2 * USD)
    split = dict(
        device="example-desk",
        fleet_daily=6 * USD,
        fleet_monthly=28 * USD,
        daily=2 * USD,
        monthly=5 * USD,
        through=term["through"],
    )
    # A retry after a lost response returns the same grant while the peer is still closed.
    with ThreadPoolExecutor(2) as pool:
        first, retry = list(pool.map(lambda _: reserve_device_share(primary, **split), range(2)))
    assert first == retry and not secondary.summary()["active"]
    assert primary.summary()["allocated_usd"] == 4
    assert primary.summary()["monthly_limit_usd"] == 23
    renew(secondary, **first)
    renew(secondary, **retry)
    assert primary.summary()["local_budget_used_usd"] == 2
    assert (
        primary.summary()["monthly_available_usd"] + secondary.summary()["monthly_available_usd"]
        == 14
    )
    for ledger, limit in ((primary, 2 * USD), (secondary, 2 * USD)):
        ledger.reserve("fill-day", "responses", limit)
        with pytest.raises(DomainError, match="OPENAI_DAILY_BUDGET_REACHED"):
            ledger.reserve("too-much", "responses", 1)
    with pytest.raises(DomainError, match="OPENAI_BUDGET_TERM_CONFLICT"):
        reserve_device_share(primary, **(split | {"device": "other-desk"}))
    with pytest.raises(DomainError, match="OPENAI_BUDGET_TERM_CONFLICT"):
        renew(primary, **term)
    now[0] = datetime(2030, 5, 1, 10, tzinfo=HONG_KONG)
    assert reserve_device_share(primary, **split) == first
    assert sum(item.summary()["available_usd"] for item in ledgers) == 6
    assert sum(item.summary()["monthly_available_usd"] for item in ledgers) == 28


@pytest.mark.parametrize("amount,opening", [(5, 0), (0, 25)])
def test_peer_share_cannot_spend_committed_day_or_month_room(tmp_path, amount, opening):
    path = tmp_path / "primary" / "budget.db"
    provision(path, start="2030-04-01", through="2030-04-02", share=6 * USD)
    ledger = DailySpend(path, lambda: datetime(2030, 4, 3, 12, tzinfo=HONG_KONG))
    renew(
        ledger,
        start="2030-04-03",
        through="2030-06-30",
        daily=6 * USD,
        monthly=28 * USD,
        day_opening=0,
        month_opening=opening * USD,
        statement="b" * 64,
    )
    if amount:
        ledger.reserve("in-flight", "responses", amount * USD)
    before = ledger.summary()
    with pytest.raises(DomainError, match="OPENAI_BUDGET_INSUFFICIENT_HEADROOM"):
        reserve_device_share(
            ledger,
            device="example-desk",
            fleet_daily=6 * USD,
            fleet_monthly=28 * USD,
            daily=2 * USD,
            monthly=5 * USD,
            through="2030-06-30",
        )
    assert ledger.summary() == before

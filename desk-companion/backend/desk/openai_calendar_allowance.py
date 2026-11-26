"""Calendar-period extensions to the existing local OpenAI reservation ledger."""

from datetime import date
import json
import re

from .store import DomainError


def renew(ledger, *, start, through, daily, monthly, day_opening, month_opening, statement):
    """Record an approved successor term in place. Keep every old charge and receipt."""
    first, last = date.fromisoformat(start), date.fromisoformat(through)
    if (
        first > last
        or not re.fullmatch(r"[a-f0-9]{64}", statement)
        or any(type(x) is not int for x in (daily, monthly, day_opening, month_opening))
        or not 0 < daily <= monthly
        or not 0 <= day_opening <= month_opening
    ):
        raise ValueError("Invalid calendar spending authorization")
    terms = (start, through, daily, monthly, day_opening, month_opening, statement)
    with ledger._db(True) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS calendar_allowances(
            starts TEXT PRIMARY KEY, through TEXT NOT NULL, daily_limit INTEGER NOT NULL,
            monthly_limit INTEGER NOT NULL, day_opening INTEGER NOT NULL, month_opening INTEGER NOT NULL,
            statement TEXT NOT NULL, cutoff INTEGER NOT NULL, previous_rule TEXT NOT NULL)""")
        prior = effective_rule(db)
        existing = db.execute(
            "SELECT * FROM calendar_allowances WHERE starts=?", (start,)
        ).fetchone()
        if existing:
            if tuple(existing)[:7] != terms:
                raise DomainError("OPENAI_BUDGET_TERM_CONFLICT", 409)
            return
        if not prior or prior["through"] >= start or prior["latest_day"] > through:
            raise ValueError("Renew only after the previous term and its clock watermark")
        if db.execute("SELECT 1 FROM charges WHERE day>=? LIMIT 1", (start,)).fetchone():
            raise ValueError("Reconcile the existing charges before dating this successor term")
        cutoff = db.execute("SELECT COALESCE(MAX(rowid),0) FROM charges").fetchone()[0]
        db.execute(
            "INSERT INTO calendar_allowances VALUES(?,?,?,?,?,?,?,?,?)",
            (*terms, cutoff, json.dumps(dict(prior), sort_keys=True)),
        )

        # Legacy versions keep seeing their expired term on rollback.


def effective_rule(db):
    prior = db.execute("SELECT * FROM allowance WHERE id=1").fetchone()
    if (
        not prior
        or not db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='calendar_allowances'"
        ).fetchone()
    ):
        return prior
    term = db.execute(
        "SELECT starts,through,daily_limit FROM calendar_allowances ORDER BY starts DESC LIMIT 1"
    ).fetchone()
    if not term:
        return prior
    return {
        **dict(prior),
        "starts": term["starts"],
        "through": term["through"],
        "opening": 0,
        "share": term["daily_limit"],
        "calendar": True,
    }


def reserve_device_share(ledger, *, device, fleet_daily, fleet_monthly, daily, monthly, through):
    """Debit a second desk's fixed share before issuing its terms. Amounts are micro-USD."""
    if (
        not isinstance(device, str)
        or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", device)
        or any(type(x) is not int for x in (daily, monthly, fleet_daily, fleet_monthly))
        or not 0 < daily <= monthly < fleet_monthly
        or not 0 < fleet_daily - daily <= fleet_monthly - monthly
    ):
        raise ValueError("Invalid device allocation")
    retained = (fleet_daily - daily, fleet_monthly - monthly)
    with ledger._db(True) as db:
        _, day, rule = ledger._period(db)
        if "calendar" not in rule.keys():
            raise DomainError("OPENAI_BUDGET_TERM_CONFLICT", 409)
        term = db.execute(
            "SELECT * FROM calendar_allowances WHERE starts=?", (rule["starts"],)
        ).fetchone()
        if term["through"] != through:
            raise DomainError("OPENAI_BUDGET_TERM_CONFLICT", 409)
        db.execute("""CREATE TABLE IF NOT EXISTS calendar_device_shares(
            term_start TEXT PRIMARY KEY, device TEXT NOT NULL, issued_on TEXT NOT NULL,
            fleet_daily INTEGER NOT NULL, fleet_monthly INTEGER NOT NULL,
            daily INTEGER NOT NULL, monthly INTEGER NOT NULL)""")
        prior = db.execute(
            "SELECT * FROM calendar_device_shares WHERE term_start=?", (term["starts"],)
        ).fetchone()
        expected = (device, fleet_daily, fleet_monthly, daily, monthly)
        current = (term["daily_limit"], term["monthly_limit"])
        if prior:
            if (
                tuple(
                    prior[k] for k in ("device", "fleet_daily", "fleet_monthly", "daily", "monthly")
                )
                != expected
                or current != retained
            ):
                raise DomainError("OPENAI_BUDGET_TERM_CONFLICT", 409)
            start = prior["issued_on"]
        else:
            if current != (fleet_daily, fleet_monthly):
                raise DomainError("OPENAI_BUDGET_TERM_CONFLICT", 409)
            if (
                db.execute("SELECT 1 FROM sqlite_master WHERE name='daily_allocations'").fetchone()
                and db.execute(
                    "SELECT 1 FROM daily_allocations WHERE day BETWEEN ? AND ? AND other_devices>0 LIMIT 1",
                    (day, through),
                ).fetchone()
            ):
                raise DomainError("OPENAI_BUDGET_TERM_CONFLICT", 409)
            room = calendar_room(db, day, rule)
            committed = db.execute(
                "SELECT COALESCE(SUM(accounted),0) FROM charges WHERE day=?", (day,)
            ).fetchone()[0]
            if committed + room["day_opening"] > retained[0] or room["remaining"] < monthly:
                raise DomainError("OPENAI_BUDGET_INSUFFICIENT_HEADROOM", 409)
            # Existing runtime versions enforce these same columns on every reservation.
            db.execute(
                "UPDATE calendar_allowances SET daily_limit=?,monthly_limit=? WHERE starts=?",
                (*retained, term["starts"]),
            )
            db.execute(
                "INSERT INTO calendar_device_shares VALUES(?,?,?,?,?,?,?)",
                (term["starts"], device, day, fleet_daily, fleet_monthly, daily, monthly),
            )
            start = day
        return dict(
            start=start,
            through=through,
            daily=daily,
            monthly=monthly,
            day_opening=0,
            month_opening=0,
            statement=term["statement"],
        )


def calendar_room(db, day, rule):
    if not db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='calendar_allowances'"
    ).fetchone():
        return None
    term = db.execute(
        "SELECT * FROM calendar_allowances WHERE starts=?", (rule["starts"],)
    ).fetchone()
    if not term:
        raise DomainError("OPENAI_BUDGET_UNAVAILABLE", 503)
    first_month = day[:7] == term["starts"][:7]
    # The opening is an external statement taken before enabling this term.
    # Old unsettled holds remain conservative headroom, separately identified from spend.
    old_holds = (
        db.execute(
            "SELECT COALESCE(SUM(accounted),0) FROM charges WHERE rowid<=? AND settled=0",
            (term["cutoff"],),
        ).fetchone()[0]
        if first_month
        else 0
    )
    month_amount = db.execute(
        "SELECT COALESCE(SUM(accounted),0) FROM charges WHERE rowid>? AND day>=? AND day<=?",
        (term["cutoff"], day[:7] + "-01", day),
    ).fetchone()[0]
    opening = term["month_opening"] if first_month else 0
    return {
        "day_opening": term["day_opening"] if day == term["starts"] else 0,
        "daily_limit": term["daily_limit"],
        "monthly_limit": term["monthly_limit"],
        "month_opening": opening,
        "month_accounted": month_amount,
        "old_holds": old_holds,
        "remaining": max(0, term["monthly_limit"] - opening - month_amount - old_holds),
    }

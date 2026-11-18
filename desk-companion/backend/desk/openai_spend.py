"""Operator-provisioned FYP spending allocation. Amounts are integer micro-USD.

Each installation owns a fixed share of the fleet allowance. The native client
uses its server's ledger. Reads, cancellation and deletion remain available
when admission expires. A missing receipt retains its original reservation.
"""

from contextlib import closing, contextmanager
from datetime import date, datetime, time, timedelta
import math
import os
from pathlib import Path
import sqlite3
import stat
from uuid import uuid4
from zoneinfo import ZoneInfo

from .bounded_json import bounded_json_post
from .provider_policy import OPENAI_BROWSER_MODELS, OPENAI_TEXT_ENDPOINT
from .store import DomainError

HONG_KONG = ZoneInfo("Asia/Hong_Kong")
USD = 1_000_000
TEXT_STAGE = 80_000
TEXT_SESSION = 250_000
HOSTED_BROWSER = 2_000_000
VOICE = 2_500_000


def token_estimate(usage):
    if not isinstance(usage, dict):
        return None
    inp, out = usage.get("input_tokens"), usage.get("output_tokens")
    if type(inp) is not int or type(out) is not int or min(inp, out) < 0 or inp + out == 0:
        return None
    # Use the highest Standard cache-write rate for every input plus 10%,
    # including the long-context premium when applicable. Never add cached
    # or reasoning tokens twice.
    return ((110 * inp + 165 * out if inp > 272_000 else 55 * inp + 110 * out) + 9) // 10


def voice_estimate(usage, elapsed, live=True):
    if live:
        backend = (
            token_estimate(
                {key: usage.get("backend_" + key) for key in ("input_tokens", "output_tokens")}
            )
            or 0
        )
        seconds = max(elapsed, usage.get("voice_seconds", 0))
        return backend + math.ceil(seconds * 55_000 / 60)
    inp = usage.get("input_tokens", 0)
    out = usage.get("output_tokens", 0)
    return math.ceil((32 * inp + 64 * out) * 1.1)


def _secure(path):
    st = path.lstat()
    if (
        path.resolve() != path
        or not stat.S_ISREG(st.st_mode)
        or st.st_uid != os.getuid()
        or st.st_mode & 0o077
    ):
        raise ValueError("Invalid budget ledger path")


def provision(path, *, start, through, share, opening=0):
    """One-time installation. Repeating the same configuration never resets spending."""
    path = Path(path).absolute()
    if not (
        date.fromisoformat(start) <= date.fromisoformat(through)
        and type(share) is int
        and 0 < share <= 20 * USD
        and type(opening) is int
        and opening >= 0
    ):
        raise ValueError("Invalid approved allowance")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (
        path.parent.resolve() != path.parent
        or path.parent.stat().st_uid != os.getuid()
        or path.parent.stat().st_mode & 0o077
    ):
        raise ValueError("Use a private ledger directory")
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    except FileExistsError:
        pass
    _secure(path)
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""CREATE TABLE IF NOT EXISTS allowance(id INTEGER PRIMARY KEY CHECK(id=1),
                   starts TEXT,through TEXT,share INTEGER,opening INTEGER,latest_day TEXT)""")
        db.execute("""CREATE TABLE IF NOT EXISTS charges(id TEXT PRIMARY KEY,day TEXT NOT NULL,
                   kind TEXT NOT NULL,scope TEXT,held INTEGER NOT NULL,accounted INTEGER NOT NULL,
                   observed INTEGER NOT NULL DEFAULT 0, settled INTEGER NOT NULL DEFAULT 0)""")
        db.execute("CREATE INDEX IF NOT EXISTS charges_day ON charges(day)")
        db.execute("CREATE INDEX IF NOT EXISTS charges_scope ON charges(scope)")
        db.execute(
            "INSERT OR IGNORE INTO allowance VALUES(1,?,?,?,?,'')", (start, through, share, opening)
        )
        if db.execute("SELECT starts,through,share,opening FROM allowance").fetchone() != (
            start,
            through,
            share,
            opening,
        ):
            raise ValueError("Existing allowance differs; existing charges were preserved")
        db.execute(
            "INSERT OR IGNORE INTO charges VALUES('opening',?,'prior spending',NULL,?,?,?,1)",
            (start, opening, opening, opening),
        )


class DailySpend:
    def __init__(self, path, clock):
        self.path = Path(path).absolute() if path else None
        self.clock = clock

    @contextmanager
    def _db(self, write=False):
        try:
            _secure(self.path)
            with (
                closing(
                    sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=4)
                ) as db,
                db,
            ):
                db.row_factory = sqlite3.Row
                db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                yield db
        except (OSError, sqlite3.Error, ValueError) as error:
            raise DomainError("OPENAI_BUDGET_UNAVAILABLE", 503) from error

    def _period(self, db, *, record=False):
        now = self.clock().astimezone(HONG_KONG)
        day = now.date().isoformat()
        rule = db.execute("SELECT * FROM allowance WHERE id=1").fetchone()
        if not rule:
            raise DomainError("OPENAI_BUDGET_UNAVAILABLE", 503)
        if record and day > rule["through"] and day > rule["latest_day"]:
            # A failed attempt after expiry must not reopen after a host clock rollback.
            db.execute("UPDATE allowance SET latest_day=? WHERE id=1", (day,))
            db.commit()
        if not rule["starts"] <= day <= rule["through"] or day < rule["latest_day"]:
            raise DomainError("OPENAI_BUDGET_PERIOD_CLOSED", 429)
        return now, day, rule

    def check_open(self):
        if self.path:
            with self._db(True) as db:
                self._period(db, record=True)

    def reserve(self, ident, kind, amount, *, scope=None, seconds=60):
        if not self.path:
            return
        if type(amount) is not int or amount <= 0:
            raise DomainError("OPENAI_BUDGET_UNAVAILABLE", 503)
        with self._db(True) as db:
            now, day, rule = self._period(db, record=True)
            midnight = datetime.combine(now.date() + timedelta(days=1), time.min, HONG_KONG)
            if (midnight - now).total_seconds() <= seconds:
                raise DomainError("OPENAI_BUDGET_DAY_END", 429)
            prior = db.execute(
                "SELECT day,kind,scope,held FROM charges WHERE id=?", (ident,)
            ).fetchone()
            if prior:
                # Billing admission is not an idempotency grant to send again.
                raise DomainError("OPENAI_BUDGET_ATTEMPT_REUSED", 409)
            used = db.execute(
                "SELECT COALESCE(SUM(accounted),0) FROM charges WHERE day=?", (day,)
            ).fetchone()[0]
            if used + amount > rule["share"]:
                raise DomainError("OPENAI_DAILY_BUDGET_REACHED", 429)
            if scope:
                used = db.execute(
                    "SELECT COALESCE(SUM(accounted),0) FROM charges WHERE scope=?", (scope,)
                ).fetchone()[0]
                if used + amount > TEXT_SESSION:
                    raise DomainError("OPENAI_SESSION_BUDGET_REACHED", 429)
            db.execute(
                "INSERT INTO charges(id,day,kind,scope,held,accounted) VALUES(?,?,?,?,?,?)",
                (ident, day, kind, scope, amount, amount),
            )
            db.execute("UPDATE allowance SET latest_day=? WHERE id=1", (day,))

    def active(self, ident):
        if not self.path:
            return
        with self._db() as db:
            _, day, _ = self._period(db)
            row = db.execute("SELECT day,settled FROM charges WHERE id=?", (ident,)).fetchone()
            if not row or row["day"] != day or row["settled"]:
                raise DomainError("OPENAI_BUDGET_PERIOD_CLOSED", 429)

    def usage(self, ids, amount, *, final=False, retain=False):
        """Only settle complete receipts. Repeated cumulative observations cannot create credit."""
        if not self.path or amount is None:
            return
        if type(amount) is not int or amount < 0:
            raise DomainError("OPENAI_BUDGET_UNAVAILABLE", 503)
        ids = tuple(dict.fromkeys(ids))
        params = ",".join("?" for _ in ids)
        if not ids:
            return
        stop = False
        with self._db(True) as db:
            rows = db.execute(f"SELECT * FROM charges WHERE id IN ({params})", ids).fetchall()
            if len(rows) != len(ids):
                raise DomainError("OPENAI_BUDGET_UNAVAILABLE", 503)
            observed = max(amount, max(r["observed"] for r in rows))
            held = sum(r["held"] for r in rows)
            if final:
                if any(r["settled"] for r in rows) and not all(r["settled"] for r in rows):
                    raise DomainError("OPENAI_BUDGET_UNAVAILABLE", 503)
                accounted = max(observed, held) if retain else observed
                if all(r["settled"] for r in rows):
                    accounted = max(accounted, sum(r["accounted"] for r in rows))
                db.execute(f"UPDATE charges SET settled=1,accounted=0 WHERE id IN ({params})", ids)
                db.execute(
                    "UPDATE charges SET observed=?,accounted=? WHERE id=?",
                    (observed, accounted, ids[0]),
                )
            elif not any(r["settled"] for r in rows):
                db.execute(
                    "UPDATE charges SET observed=?,accounted=held+? WHERE id=?",
                    (observed, max(0, observed - held), ids[0]),
                )
                stop = observed * 10 >= held * 9
        if stop:
            raise DomainError("OPENAI_BUDGET_EARLY_STOP", 429)

    def summary(self):
        if not self.path:
            return {"configured": False}
        day = self.clock().astimezone(HONG_KONG).date().isoformat()
        with self._db() as db:
            rule = db.execute("SELECT * FROM allowance WHERE id=1").fetchone()
            used = db.execute(
                "SELECT COALESCE(SUM(accounted),0) FROM charges WHERE day=?", (day,)
            ).fetchone()[0]
            return {
                "configured": True,
                "day": day,
                "timezone": "Asia/Hong_Kong",
                "through": rule["through"],
                "active": rule["starts"] <= day <= rule["through"] and day >= rule["latest_day"],
                "allocated_usd": rule["share"] / USD,
                "accounted_usd": used / USD,
                "available_usd": max(0, rule["share"] - used) / USD,
            }


def budgeted_response(client, endpoint, *, headers, json_body, budget=None):
    """Count the exact input before an eligible Responses generation, including file/image inputs."""
    if not budget or not budget.path:
        return bounded_json_post(client, endpoint, headers=headers, json_body=json_body)
    if (
        endpoint != OPENAI_TEXT_ENDPOINT
        or json_body.get("model") not in OPENAI_BROWSER_MODELS
        or json_body.get("store") is not False
        or json_body.get("stream")
        or type(json_body.get("max_output_tokens")) is not int
        or not 0 < json_body["max_output_tokens"] <= 1600
    ):
        raise DomainError("OPENAI_BUDGET_UNSUPPORTED_REQUEST", 409)
    # This read-only endpoint sees the same selected input and runs the same auth hooks.
    body = {
        k: json_body[k]
        for k in (
            "model",
            "input",
            "instructions",
            "reasoning",
            "text",
            "tools",
            "tool_choice",
            "parallel_tool_calls",
        )
        if k in json_body
    }
    budget.check_open()
    counted = bounded_json_post(client, endpoint + "/input_tokens", headers=headers, json_body=body)
    n = counted.get("input_tokens")
    if type(n) is not int or not 0 <= n <= 922_000:
        raise DomainError("OPENAI_BUDGET_TOKEN_COUNT", 409)
    maximum = token_estimate(
        {"input_tokens": math.ceil(n * 1.1) + 128, "output_tokens": json_body["max_output_tokens"]}
    )
    ident = uuid4().hex
    budget.reserve(ident, "responses", maximum)
    budget.active(ident)
    result = bounded_json_post(
        client, endpoint, headers=headers, json_body={**json_body, "service_tier": "default"}
    )
    budget.usage([ident], token_estimate(result.get("usage")), final=True)
    return result

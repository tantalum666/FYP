"""Read an operator's official Costs CSV without attributing a UTC bucket to local jobs."""

import csv
import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import StringIO
from pathlib import Path

from .store import encode


def parse_statement(raw: bytes):
    if len(raw) > 4_000_000:
        raise ValueError("Costs export exceeds the expected size")
    rows = list(csv.DictReader(StringIO(raw.decode("utf-8-sig"))))
    if not rows:
        raise ValueError("Empty cost export")
    windows = set()
    total = Decimal(0)
    for row in rows:
        try:
            start, end = int(row["start_time"]), int(row["end_time"])
            amount = Decimal(row["amount_value"])
            currency = row["amount_currency"].lower()
        except (KeyError, TypeError, ValueError, InvalidOperation) as error:
            raise ValueError("Invalid OpenAI Costs row") from error
        if currency != "usd" or not amount.is_finite() or amount.adjusted() > 12:
            raise ValueError("Expected finite USD amounts")
        if start < 0 or end - start != 86400 or start % 86400:
            raise ValueError("Expected one complete UTC reporting day")
        windows.add((start, end))
        total += amount
    if len(windows) != 1:
        raise ValueError("Choose a single UTC day from the dashboard")
    start, end = windows.pop()
    return {
        "source": "openai_costs_csv",
        "currency": "USD",
        "amount_usd": str(total.normalize()),
        "utc_day": datetime.fromtimestamp(start, UTC).date().isoformat(),
        "period_start": start,
        "period_end": end,
        "rows": len(rows),
        "sha256": sha256(raw).hexdigest(),
    }


def save_statement(db, raw: bytes, scope: str, now):
    if not scope.strip() or len(scope) > 160:
        raise ValueError("State the exact dashboard filter scope")
    item = parse_statement(raw)
    item.update(scope=scope, imported_at=now.astimezone(UTC).isoformat())
    db.execute(
        "CREATE TABLE IF NOT EXISTS platform_cost_reports("
        "utc_day TEXT, digest TEXT, scope TEXT, report TEXT, PRIMARY KEY(digest,scope))"
    )
    db.execute(
        "INSERT OR IGNORE INTO platform_cost_reports VALUES(?,?,?,?)",
        (item["utc_day"], item["sha256"], scope, encode(item)),
    )
    row = db.execute(
        "SELECT report FROM platform_cost_reports WHERE digest=? AND scope=?",
        (item["sha256"], scope),
    ).fetchone()
    return json.loads(row[0])


def latest_statement(db):
    if not db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='platform_cost_reports'"
    ).fetchone():
        return None
    row = db.execute(
        "SELECT report FROM platform_cost_reports ORDER BY utc_day DESC,rowid DESC LIMIT 1"
    ).fetchone()
    return json.loads(row[0]) if row else None


if __name__ == "__main__":
    from .openai_spend import DailySpend

    parser = argparse.ArgumentParser(
        description="Import one official UTC Costs export into local diagnostics"
    )
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--scope", required=True, help="The actual project and API-source filters")
    args = parser.parse_args()
    ledger = DailySpend(args.ledger, lambda: datetime.now(UTC))
    with args.csv.open("rb") as file:
        print(json.dumps(ledger.import_cost_statement(file.read(4_000_001), args.scope), indent=2))

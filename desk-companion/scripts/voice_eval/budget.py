"""Durable, conservative reservations. Unknown usage never becomes zero spend."""

import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

CEILING_USD = 5.0
RATES = {
    "gpt-realtime-2.1": (4, 32, 24, 64),
    "gpt-realtime-2.1-mini": (0.6, 10, 2.4, 20),
    "gpt-6-luna": (0.1, 0.1, 0.5, 0.5),
}


def token_cost(model, usage):
    """USD estimate at uncached standard rates; retain provider usage separately."""
    ti, ai, to, ao = RATES[model]
    incoming = usage.get("input_token_details") or usage.get("input_tokens_details") or {}
    outgoing = usage.get("output_token_details") or usage.get("output_tokens_details") or {}
    total = 0
    for details, count, text_rate, audio_rate in (
        (incoming, usage.get("input_tokens", 0), ti, ai),
        (outgoing, usage.get("output_tokens", 0), to, ao),
    ):
        text, audio = details.get("text_tokens", 0), details.get("audio_tokens", 0)
        if min(text, audio, count) < 0 or text + audio > count:
            raise ValueError("INVALID_USAGE")
        total += text * text_rate + audio * audio_rate
        total += (count - text - audio) * max(text_rate, audio_rate)
    if model == "gpt-6-luna":
        # Receipt omits write TTL. Reserve the larger published 12h write rate,
        # replacing the ordinary $0.10/M input amount already counted above.
        total += incoming.get("cache_write_tokens", 0) * (0.25 - 0.1)
    return total / 1_000_000


class Budget:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, model TEXT, "
                "reserve REAL, estimate REAL, finalized INTEGER, result TEXT, at TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS policy (id INTEGER PRIMARY KEY CHECK(id=1), closed INTEGER)"
            )
            conn.execute("INSERT OR IGNORE INTO policy VALUES(1,0)")

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def reserve(self, run_id, model, amount):
        if not math.isfinite(amount) or amount <= 0 or amount > CEILING_USD:
            raise ValueError("INVALID_RESERVATION")
        with self.connection() as conn:
            if conn.execute("SELECT closed FROM policy WHERE id=1").fetchone()[0]:
                raise ValueError("EXPERIMENT_CLOSED")
            charged = conn.execute(
                "SELECT COALESCE(SUM(CASE WHEN finalized=1 THEN estimate ELSE MAX(estimate,reserve) END),0) "
                "FROM runs"
            ).fetchone()[0]
            if charged + amount > CEILING_USD:
                raise ValueError("BUDGET_EXHAUSTED")
            conn.execute(
                "INSERT INTO runs VALUES(?,?,?,0,0,'{}',?)",
                (
                    run_id,
                    model,
                    amount,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def finish(self, run_id, *, estimate, finalized, result):
        if (
            not math.isfinite(estimate)
            or estimate < 0
            or not isinstance(result, dict)
            or not result
        ):
            raise ValueError("INVALID_ESTIMATE")
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None or row["result"] != "{}":
                raise ValueError("RUN_ALREADY_FINAL_OR_UNKNOWN")
            # Retain the reservation if the provider receipt cannot be reconciled.
            conn.execute(
                "UPDATE runs SET estimate=?,finalized=?,result=? WHERE id=?",
                (
                    estimate,
                    int(finalized),
                    json.dumps(result),
                    run_id,
                ),
            )

    def close(self):
        with self.connection() as conn:
            conn.execute("UPDATE policy SET closed=1 WHERE id=1")

    def snapshot(self):
        with self.connection() as conn:
            rows = [dict(r) for r in conn.execute("SELECT * FROM runs ORDER BY at")]
            closed = bool(conn.execute("SELECT closed FROM policy WHERE id=1").fetchone()[0])
        return {
            "closed": closed,
            "ceiling_usd": CEILING_USD,
            "observed_uncached_estimate_usd": sum(r["estimate"] for r in rows),
            "accounted_usd": sum(
                r["estimate"] if r["finalized"] else max(r["estimate"], r["reserve"]) for r in rows
            ),
            "runs": [{**r, "result": json.loads(r["result"])} for r in rows],
            "billing_note": "Provider usage estimates, not a verified account bill. Unknown runs retain reservations.",
        }

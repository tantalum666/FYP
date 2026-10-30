"""Offline reference facts for the complex application task; never an agent tool.

This checks fixture consistency only. It does not operate apps, grade their
execution, or produce the candidate's spreadsheet/report/calendar deliverables.
The controller and this reference must be excluded from an evaluated agent.
"""

import argparse
import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo

FIXTURE = Path(__file__).resolve().parents[1] / "evals/app_workflow_v1"
CENT = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def rows(path):
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def quote_results(case, quotes, rates, phase):
    requested = case["phases"][phase]
    latest = {}
    today = case["clock"][:10]
    for quote in quotes:
        if quote["updated"] > today:
            continue
        old = latest.get(quote["supplier"])
        if old is None or (quote["updated"], quote["revision"]) > (old["updated"], old["revision"]):
            latest[quote["supplier"]] = quote
    results = []
    for supplier, quote in sorted(latest.items()):
        units = max(requested["booklets"], quote["min_booklets"])
        items = (
            Decimal(quote["poster"]) * case["quantity"]["posters"]
            + Decimal(quote[requested["mode"]]) * units
            + Decimal(quote["badge"]) * case["quantity"]["badges"]
        )
        delivered = money(
            items * (1 - Decimal(quote["item_discount"])) + Decimal(quote["delivery_fee"])
        )
        if quote["currency"] not in rates:
            raise ValueError("MISSING_FX_RATE")
        delivered_hkd = money(delivered * Decimal(rates[quote["currency"]]))
        reserve = money(delivered_hkd * Decimal(case["contingency_rate"]))
        total = delivered_hkd + reserve
        failures = []
        if quote["valid_until"] < today:
            failures.append("expired_quote")
        if quote["delivery"] > case["delivery_deadline"]:
            failures.append("late_delivery")
        if total > Decimal(requested["budget_hkd"]):
            failures.append("over_budget")
        results.append(
            {
                "supplier": supplier,
                "quote_id": quote["id"],
                "currency": quote["currency"],
                "booklets_purchased": units,
                "delivered_hkd": str(delivered_hkd),
                "reserve_hkd": str(reserve),
                "total_hkd": str(total),
                "eligible": not failures,
                "exclusions": failures,
            }
        )
    candidates = sorted(
        (r for r in results if r["eligible"]),
        key=lambda r: (Decimal(r["total_hkd"]), r["supplier"]),
    )
    return {
        "quotes": results,
        "selected": candidates[0] if candidates else None,
        "clarification_required": not candidates,
    }


def task_results(case, task_rows):
    latest = {}
    for row in task_rows:
        old = latest.get(row["id"])
        if old is None or datetime.fromisoformat(row["updated_at"]) > datetime.fromisoformat(
            old["updated_at"]
        ):
            latest[row["id"]] = dict(row)
    for task_id, update in case["task_updates"].items():
        current = latest[task_id]
        if datetime.fromisoformat(update["updated_at"]) > datetime.fromisoformat(
            current["updated_at"]
        ):
            current.update(update)
    remaining = [r for r in latest.values() if r["status"] != "completed"]
    return {
        "unique_tasks": len(latest),
        "remaining_count": len(remaining),
        "remaining_hours": str(sum((Decimal(r["remaining_hours"]) for r in remaining), Decimal(0))),
        "tasks": [latest[k] for k in sorted(latest)],
    }


def rehearsal_results(case, availability, existing, phase):
    spans = [
        (r["member"], datetime.fromisoformat(r["start"]), datetime.fromisoformat(r["end"]))
        for r in availability
    ]
    busy = [
        (datetime.fromisoformat(r["start"]), datetime.fromisoformat(r["end"])) for r in existing
    ]
    duration = timedelta(minutes=case["rehearsal_minutes"])
    chosen = []
    for day in sorted({start.date() for _, start, _ in spans}):
        if day.weekday() in case["phases"][phase]["exclude_weekdays"]:
            continue
        for minute in range(14 * 60, 17 * 60, 15):
            start = datetime(
                day.year,
                day.month,
                day.day,
                minute // 60,
                minute % 60,
                tzinfo=ZoneInfo(case["timezone"]),
            )
            end = start + duration
            if not all(
                any(who == member and a <= start and end <= b for who, a, b in spans)
                for member in case["members"]
            ):
                continue
            if any(start < b and a < end for a, b in busy):
                continue
            chosen.append({"start": start.isoformat(), "end": end.isoformat()})
            break
        if len(chosen) == case["rehearsals"]:
            break
    return chosen


def reference(root=FIXTURE):
    case = json.loads((root / "controller/case.json").read_text())
    quotes = json.loads((root / "controller/quotes.json").read_text())
    rates = {r["currency"]: r["HKD_per_unit"] for r in rows(root / "inputs/fx-rates.csv")}
    return {
        "reference_only": True,
        "application_execution": "not_run",
        "candidate_submission": "not_evaluated",
        "tasks": task_results(case, rows(root / "inputs/tasks.csv")),
        "phases": {
            phase: {
                "budget": quote_results(case, quotes, rates, phase),
                "rehearsals": rehearsal_results(
                    case,
                    rows(root / "inputs/availability.csv"),
                    rows(root / "inputs/existing-events.csv"),
                    phase,
                ),
            }
            for phase in case["phases"]
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    content = json.dumps(reference(), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(content)
    else:
        print(content, end="")

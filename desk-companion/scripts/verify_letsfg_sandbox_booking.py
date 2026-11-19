"""Reopen one LetsFG sandbox booking and compare it with the approved test quote."""

import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx


BOOKINGS = "https://letsfg.co/developers/api/v1/sandbox/flights/bookings/"


def amount(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Missing or invalid monetary amount") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("Expected a finite, nonnegative amount")
    return result


def verify(client, expected):
    booking_id = expected["booking_id"]
    if not isinstance(booking_id, str) or not re.fullmatch(
        r"sb_dev_[A-Za-z0-9_-]{1,96}", booking_id
    ):
        raise ValueError("Expected a sandbox booking reference")
    outcome = expected["outcome"]
    if outcome not in {"completed", "price_change_declined"}:
        raise ValueError("Unknown expected outcome")
    approved = amount(expected["approved_amount"])
    currency = expected["currency"]
    offer = {field: expected[field] for field in ("search_id", "offer_id")}
    if not re.fullmatch(r"[A-Z]{3}", currency) or not all(
        isinstance(value, str) and value.startswith("sb_") for value in offer.values()
    ):
        raise ValueError("Expected the currency and references from the approved sandbox search")

    response = client.get(booking_id)
    if response.status_code != 200:
        raise ValueError(f"Sandbox booking read returned HTTP {response.status_code}")
    booking = response.json()
    if not isinstance(booking, dict) or not isinstance(booking.get("offer"), dict):
        raise ValueError("The sandbox did not return a booking with an offer")
    if (
        booking.get("sandbox") is not True
        or booking.get("terminal") is not True
        or booking.get("booking_id") != booking_id
        or any(booking["offer"].get(field) != value for field, value in offer.items())
        or booking.get("currency") != currency
        or amount(booking.get("held_amount")) != approved
        or booking.get("card_last4") != "4242"
    ):
        raise ValueError("The provider record does not match the approved sandbox booking")

    captured = booking.get("charged_amount")
    reference = booking.get("pnr")
    if outcome == "completed":
        if (
            booking.get("state") != "completed"
            or not isinstance(reference, str)
            or not re.fullmatch(r"[A-Z0-9]{6}", reference)
            or amount(captured) != approved
        ):
            raise ValueError("The sandbox has no matching completed and captured booking")
    elif (
        booking.get("state") != "failed"
        or reference not in (None, "")
        or (captured is not None and amount(captured) != 0)
        or not isinstance(booking.get("failure_reason"), str)
        or "declined the new price" not in booking["failure_reason"].lower()
        or not isinstance(booking.get("message"), str)
        or "hold was released" not in booking["message"].lower()
    ):
        raise ValueError(
            "The sandbox did not confirm refusal of the increase and release of the hold"
        )

    return {
        "sandbox": True,
        "state": booking["state"],
        "currency": currency,
        "approved_amount": str(approved),
        "simulated_capture": str(amount(captured)) if captured is not None else None,
        "simulated_pnr": reference or None,
        "release_reported": outcome == "price_change_declined",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "expectation", type=Path, help="Private expected quote and booking reference"
    )
    args = parser.parse_args()
    try:
        expected = json.loads(args.expectation.read_text())
        with httpx.Client(
            base_url=BOOKINGS, trust_env=False, follow_redirects=False, timeout=18
        ) as client:
            result = verify(client, expected)
    except httpx.HTTPError as exc:
        parser.exit(1, f"Could not reach the sandbox ({type(exc).__name__}).\n")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.exit(1, f"Booking verification failed ({type(exc).__name__}): {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

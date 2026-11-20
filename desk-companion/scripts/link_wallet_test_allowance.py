"""Checks used before FYP hands a recurring Link test card to a Stripe sandbox checkout."""

import re
from datetime import UTC, datetime


MAX_ORDER_USD_CENTS = 1_000


def check_checkout(get, terms, *, checkout_id, order_reference, expected_minor):
    """Read the merchant and the current order immediately before using the credential."""
    if not isinstance(checkout_id, str) or not re.fullmatch(r"cs_test_[A-Za-z0-9]+", checkout_id):
        raise ValueError("A test Checkout Session is required")
    if terms.get("test") is not True or terms.get("currency") != "usd":
        raise ValueError("The allowance must be for USD sandbox purchases")
    limit = terms.get("per_order_minor")
    if type(limit) is not int or not 0 < limit <= MAX_ORDER_USD_CENTS:
        raise ValueError("Invalid FYP per-order limit")
    if type(expected_minor) is not int or not 0 < expected_minor <= limit:
        raise ValueError("The quoted total exceeds the FYP per-order limit or is invalid")
    account = get("account")
    if not account.get("id") or account["id"] != terms["stripe_account"]:
        raise ValueError("The Stripe account differs from the allowance merchant")
    session = get("checkout/sessions/" + checkout_id)
    if (
        session.get("id") != checkout_id
        or session.get("livemode") is not False
        or session.get("mode") != "payment"
        or session.get("status") != "open"
        or session.get("payment_status") != "unpaid"
        or session.get("payment_intent") is not None
    ):
        raise ValueError("The test checkout is unavailable or already has a payment attempt")
    metadata = session.get("metadata") or {}
    if (
        not order_reference
        or session.get("client_reference_id") != order_reference
        or metadata.get("fyp_case") != order_reference
        or metadata.get("fyp_wallet_allowance") != terms["ref"]
        or session.get("currency") != "usd"
        or type(session.get("amount_total")) is not int
        or session["amount_total"] != expected_minor
    ):
        raise ValueError("The checkout does not match this allowance and the exact reviewed quote")
    return session


def check_issuer_approval(request, terms, *, request_id, now):
    """Use the status and terms returned by the issuer for this particular allowance."""
    if (
        not request_id
        or request.get("id") != request_id
        or request.get("status") != "approved"
        or request.get("credential_type") != "card"
        or request.get("test") is False
        or request.get("livemode") is True
        or terms.get("test") is not True
    ):
        raise ValueError("Link has not approved this test card allowance")
    period = request.get("recurring") or {}
    if (
        request.get("merchant_name") != terms["merchant_name"]
        or request.get("merchant_url", "").rstrip("/") != terms["merchant_url"]
        or (request.get("metadata") or {}).get("fyp_case") != terms["ref"]
        or request.get("currency") != terms["currency"]
        or request.get("amount") != terms["per_period_minor"]
        or period.get("interval") != terms["interval"]
        or period.get("interval_count", 1) != terms["interval_count"]
    ):
        raise ValueError("The issuer's merchant, period or spending limit changed")
    granted_expiry = datetime.fromisoformat(request["expires_at"])
    requested_expiry = datetime.fromisoformat(terms["expires_utc"])
    if not now < granted_expiry <= requested_expiry:
        raise ValueError("The spending allowance has expired or exceeds its authorized term")


def check_issued_card(card, *, now):
    """Check the issuer's values as received. Never repair or substitute card digits."""
    number = card.get("number")
    if not isinstance(number, str) or not re.fullmatch(r"[0-9]{12,19}", number):
        raise ValueError("Link returned an invalid test card number format")
    checksum = 0
    for position, digit in enumerate(reversed(number)):
        value = int(digit)
        if position % 2:
            value *= 2
            if value > 9:
                value -= 9
        checksum += value
    if checksum % 10:
        raise ValueError("Link's test card failed its card-number checksum")

    valid_until = card.get("valid_until")
    if valid_until is not None:
        if isinstance(valid_until, (float, int)):
            expiry = datetime.fromtimestamp(valid_until, UTC)
        else:
            expiry = datetime.fromisoformat(valid_until)
        if expiry <= now:
            raise ValueError("The individual card credential has expired")

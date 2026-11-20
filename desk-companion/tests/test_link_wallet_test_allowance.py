from datetime import UTC, datetime, timedelta

import pytest

from scripts.link_wallet_test_allowance import (
    check_checkout,
    check_issued_card,
    check_issuer_approval,
)


NOW = datetime(2026, 11, 20, tzinfo=UTC)
END = (NOW + timedelta(days=180)).isoformat()
TERMS = {
    "test": True,
    "ref": "allowance",
    "currency": "usd",
    "per_order_minor": 1000,
    "stripe_account": "acct_test_merchant",
    "merchant_name": "FYP Alice Test Shop",
    "merchant_url": "https://checkout.stripe.com",
    "per_period_minor": 50000,
    "interval": "month",
    "interval_count": 1,
    "expires_utc": END,
}


def checkout(amount=1000, *, account=TERMS["stripe_account"], expected=1000, **changed):
    session = {
        "id": "cs_test_order",
        "livemode": False,
        "mode": "payment",
        "status": "open",
        "payment_status": "unpaid",
        "payment_intent": None,
        "client_reference_id": "order",
        "currency": "usd",
        "amount_total": amount,
        "metadata": {"fyp_case": "order", "fyp_wallet_allowance": TERMS["ref"]},
    } | changed
    records = {"account": {"id": account}, "checkout/sessions/cs_test_order": session}
    return check_checkout(
        records.__getitem__,
        TERMS,
        checkout_id=session["id"],
        order_reference="order",
        expected_minor=expected,
    )


def issuer(now=NOW, **changed):
    request = {
        "id": "wallet_order",
        "status": "approved",
        "credential_type": "card",
        "recurring": {"interval": "month"},
        "merchant_name": TERMS["merchant_name"],
        "merchant_url": TERMS["merchant_url"],
        "metadata": {"fyp_case": TERMS["ref"]},
        "currency": "usd",
        "amount": 50000,
        "expires_at": END,
    } | changed
    check_issuer_approval(request, TERMS, request_id="wallet_order", now=now)


def test_exact_per_order_ceiling_and_approved_monthly_terms():
    assert checkout()["amount_total"] == 1000
    issuer()
    with pytest.raises(ValueError, match="per-order limit"):
        checkout(1001, expected=1001)


@pytest.mark.parametrize(
    "changed",
    [
        {"amount": 950},
        {"amount": 1010},
        {"currency": "hkd"},
        {"account": "acct_other"},
        {"livemode": True},
        {"mode": "subscription"},
        {"payment_intent": "pi_pending"},
        {"metadata": {"fyp_case": "order", "fyp_wallet_allowance": "different"}},
    ],
)
def test_checkout_cannot_redirect_or_reprice_an_approved_purchase(changed):
    with pytest.raises(ValueError):
        checkout(**changed)


@pytest.mark.parametrize(
    "changed",
    [
        {"status": "pending_approval"},
        {"status": "canceled"},
        {"merchant_name": "Different"},
        {"recurring": {"interval": "day"}},
        {"amount": 50001},
        {"livemode": True},
        {"now": NOW + timedelta(days=180)},
        {"expires_at": (NOW + timedelta(days=181)).isoformat()},
    ],
)
def test_issuer_must_still_approve_the_exact_bounded_authority(changed):
    with pytest.raises(ValueError):
        issuer(**changed)


def test_issued_card_validation_and_separate_credential_deadline():
    example = {"number": "4242" * 4, "valid_until": (NOW + timedelta(hours=1)).isoformat()}
    check_issued_card(example, now=NOW)
    with pytest.raises(ValueError, match="checksum"):
        check_issued_card(example | {"number": example["number"][:-1] + "1"}, now=NOW)
    with pytest.raises(ValueError, match="credential has expired"):
        check_issued_card(example, now=NOW + timedelta(hours=1))

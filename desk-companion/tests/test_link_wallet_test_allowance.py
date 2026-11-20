from datetime import UTC, datetime, timedelta

import pytest

from scripts.link_wallet_test_allowance import (
    check_checkout,
    check_issued_card,
    check_issuer_approval,
    checked_card_proof,
    link_scope_tokens,
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


@pytest.mark.parametrize(
    "raw",
    [
        "payment_methods.agentic userinfo:read",
        "payment_methods.agentic,userinfo:read",
        " userinfo:read,\t payment_methods.agentic, userinfo:read ",
    ],
)
def test_link_scope_tokens_before_and_after_token_rotation(raw):
    assert link_scope_tokens(raw) == {"payment_methods.agentic", "userinfo:read"}


@pytest.mark.parametrize(
    "raw", [None, "", ["payment_methods.agentic"], "payment_methods.agentic_extra,userinfo:read"]
)
def test_link_scope_tokens_do_not_imply_an_ungranted_payment_scope(raw):
    assert "payment_methods.agentic" not in link_scope_tokens(raw)


def test_shared_credential_handoff_binds_and_redacts():
    card = {"number": "4242" * 4, "exp_month": 12, "exp_year": "30", "cvc": "123"}
    expected = {
        "request_id": "fixture",
        "merchant_name": "FYP",
        "merchant_url": "https://example.test",
    }
    artifact = {
        "spend_request_id": "fixture",
        "merchant_name": "FYP",
        "merchant_url": "https://example.test/",
        "card": card,
    }
    assert checked_card_proof(artifact, **expected, now=NOW) == {
        "last4": "4242",
        "exp_month": 12,
        "exp_year": 2030,
        "credential_valid_until": None,
    }
    with_deadline = artifact | {"card": card | {"valid_until": END}}
    assert checked_card_proof(with_deadline, **expected, now=NOW)["credential_valid_until"] == END
    with pytest.raises(ValueError, match="not bound"):
        checked_card_proof(artifact | {"spend_request_id": "other"}, **expected, now=NOW)
    with pytest.raises(ValueError, match="checksum"):
        checked_card_proof(
            artifact | {"card": card | {"number": card["number"][:-1] + "1"}}, **expected, now=NOW
        )
    with pytest.raises(ValueError, match="expiry month"):
        checked_card_proof(artifact | {"card": card | {"exp_year": 2025}}, **expected, now=NOW)
    with pytest.raises(ValueError, match="security code format"):
        checked_card_proof(artifact | {"card": card | {"cvc": ""}}, **expected, now=NOW)

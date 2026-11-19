"""Independently read one FYP test merchant order. All Stripe requests are GETs."""

import argparse
import json
import re
import tomllib
from pathlib import Path

import httpx


def test_object(value):
    if value.get("livemode") is not False:
        raise ValueError("The provider did not identify a test-mode object")
    return value


def receipt(client, session_id, reference, amount, currency, *, full_refund_id=None):
    if not re.fullmatch(r"cs_test_[a-zA-Z0-9]+", session_id):
        raise ValueError("Expected a test Checkout Session ID")
    if full_refund_id is not None and (
        not isinstance(full_refund_id, str) or not re.fullmatch(r"re_[a-zA-Z0-9]+", full_refund_id)
    ):
        raise ValueError("Expected a Stripe Refund ID")

    def get(path):
        response = client.get(path)
        if response.status_code != 200:
            raise RuntimeError(f"Stripe read returned HTTP {response.status_code}")
        return response.json()

    session = test_object(get("checkout/sessions/" + session_id))
    if (
        session["id"] != session_id
        or session["client_reference_id"] != reference
        or session["amount_total"] != amount
        or session["currency"] != currency
    ):
        raise ValueError("Checkout does not match the expected order")
    if session["status"] != "complete" or session["payment_status"] != "paid":
        raise ValueError("Checkout has no completed payment")
    intent_id = session["payment_intent"]
    if not isinstance(intent_id, str) or not re.fullmatch(r"pi_[a-zA-Z0-9]+", intent_id):
        raise ValueError("Missing payment reference")
    intent = test_object(get("payment_intents/" + intent_id))
    charge_id = intent.get("latest_charge")
    if (
        intent["id"] != intent_id
        or intent["status"] != "succeeded"
        or intent["amount_received"] != amount
        or intent["currency"] != currency
        or not isinstance(charge_id, str)
        or not re.fullmatch(r"ch_[a-zA-Z0-9]+", charge_id)
    ):
        raise ValueError("The paid amount or charge reference did not match the order")
    charge = test_object(get("charges/" + charge_id))
    if (
        charge["id"] != charge_id
        or charge["payment_intent"] != intent_id
        or charge["status"] != "succeeded"
        or not charge["captured"]
        or not charge["paid"]
        or charge["amount_captured"] != amount
        or charge["currency"] != currency
    ):
        raise ValueError("The expected payment has no matching captured charge")
    result = {
        "livemode": False,
        "checkout_status": session["status"],
        "payment_status": session["payment_status"],
        "payment_intent_status": intent["status"],
        "charge_status": charge["status"],
        "method": charge["payment_method_details"]["type"],
        "captured": charge["captured"],
        "amount_minor": amount,
        "currency": currency,
        "actual_charge_minor": 0,
    }
    if full_refund_id is None:
        if charge["amount_refunded"] != 0:
            raise ValueError("The charge already has a refund")
        return result

    # Bind the Refund to both test objects even when it omits its own livemode field.
    refund = get("refunds/" + full_refund_id)
    if (
        amount <= 0
        or charge.get("refunded") is not True
        or charge.get("amount_refunded") != amount
        or refund.get("object") != "refund"
        or refund.get("id") != full_refund_id
        or refund.get("livemode", False) is not False
        or refund.get("charge") != charge_id
        or refund.get("payment_intent") != intent_id
        or refund.get("status") != "succeeded"
        or refund.get("amount") != amount
        or refund.get("currency") != currency
    ):
        raise ValueError("The refund has no matching, completed full reversal of this charge")
    result["refund"] = {"status": "succeeded", "amount_minor": amount, "currency": currency}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, required=True, help="Private Stripe CLI sandbox configuration"
    )
    parser.add_argument("--profile", default="fyp-test")
    parser.add_argument(
        "--session-file",
        type=Path,
        required=True,
        help="Private JSON file with the test Checkout id",
    )
    parser.add_argument("--reference", required=True, help="Expected merchant client_reference_id")
    parser.add_argument("--amount-minor", type=int, required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument(
        "--full-refund-file",
        type=Path,
        help="Private JSON file with the id of a single expected full refund",
    )
    args = parser.parse_args()
    refund_id = None
    if args.full_refund_file:
        refund_id = json.loads(args.full_refund_file.read_text())["id"]
        if not isinstance(refund_id, str) or not refund_id:
            parser.error("The refund file must contain a Stripe Refund ID")
    with args.config.open("rb") as f:
        profile = tomllib.load(f)[args.profile]
    key = profile.get("test_mode_api_key", "")
    if (
        not key
        or not profile.get("test_mode_pub_key", "").startswith("pk_test_")
        or key.startswith(("sk_live_", "rk_live_"))
    ):
        raise ValueError("Use a provisioned sandbox profile")
    with httpx.Client(
        base_url="https://api.stripe.com/v1/",
        auth=(key, ""),
        trust_env=False,
        follow_redirects=False,
        timeout=12,
    ) as client:
        account = client.get("account")
        if account.status_code != 200 or account.json().get("id") != profile["account_id"]:
            raise ValueError("The sandbox account does not match the expected profile")
        result = receipt(
            client,
            json.loads(args.session_file.read_text())["id"],
            args.reference,
            args.amount_minor,
            args.currency.lower(),
            full_refund_id=refund_id,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

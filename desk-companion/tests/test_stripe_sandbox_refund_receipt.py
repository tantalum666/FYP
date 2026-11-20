import sys

import httpx
import pytest

from scripts.verify_stripe_sandbox_checkout import main, receipt


def provider_records(*, charge_id="ch_shop", refund_id="re_shop"):
    return {
        "checkout/sessions/cs_test_shop": {
            "id": "cs_test_shop",
            "client_reference_id": "tissues",
            "amount_total": 100,
            "currency": "usd",
            "livemode": False,
            "status": "complete",
            "payment_status": "paid",
            "payment_intent": "pi_shop",
        },
        "payment_intents/pi_shop": {
            "id": "pi_shop",
            "status": "succeeded",
            "amount_received": 100,
            "currency": "usd",
            "livemode": False,
            "latest_charge": charge_id,
        },
        f"charges/{charge_id}": {
            "object": "charge",
            "id": charge_id,
            "payment_intent": "pi_shop",
            "status": "succeeded",
            "paid": True,
            "captured": True,
            "amount_captured": 100,
            "amount_refunded": 100,
            "refunded": True,
            "currency": "usd",
            "livemode": False,
            "payment_method_details": {"type": "amazon_pay"},
        },
        f"refunds/{refund_id}": {
            "id": refund_id,
            "object": "refund",
            "charge": charge_id,
            "payment_intent": "pi_shop",
            "status": "succeeded",
            "amount": 100,
            "currency": "usd",
        },
    }


def verify(records, refund_id="re_shop"):
    def get(request):
        assert request.method == "GET"
        return httpx.Response(200, json=records[request.url.path.lstrip("/")])

    with httpx.Client(
        transport=httpx.MockTransport(get), base_url="https://example.test"
    ) as client:
        return receipt(client, "cs_test_shop", "tissues", 100, "usd", full_refund_id=refund_id)


def test_terminal_refund_and_original_paid_only_contract():
    records = provider_records()
    assert verify(records)["refund"] == {
        "status": "succeeded",
        "amount_minor": 100,
        "currency": "usd",
    }
    with pytest.raises(ValueError, match="already has a refund"):
        verify(records, refund_id=None)
    records["charges/ch_shop"].update(refunded=False, amount_refunded=0)
    assert "refund" not in verify(records, refund_id=None)


def test_amazon_pay_charge_and_refund_identifiers():
    records = provider_records(charge_id="py_wallet", refund_id="pyr_wallet")
    result = verify(records, refund_id="pyr_wallet")
    assert result["method"] == "amazon_pay"
    assert result["refund"]["amount_minor"] == 100

    records["charges/py_wallet"]["object"] = "transfer"
    with pytest.raises(ValueError, match="captured charge"):
        verify(records, refund_id="pyr_wallet")


def test_external_identifiers_cannot_change_the_lookup_path():
    records = provider_records()
    with pytest.raises(ValueError, match="Refund ID"):
        verify(records, refund_id="../charges/ch_shop")
    records["payment_intents/pi_shop"]["latest_charge"] = "py_wallet?expand[]=customer"
    with pytest.raises(ValueError, match="charge reference"):
        verify(records)


@pytest.mark.parametrize(
    ("resource", "change"),
    [
        ("refunds/re_shop", {"status": "pending"}),
        ("refunds/re_shop", {"amount": 50}),
        ("refunds/re_shop", {"currency": "hkd"}),
        ("refunds/re_shop", {"charge": "ch_other"}),
        ("refunds/re_shop", {"payment_intent": "pi_other"}),
        ("refunds/re_shop", {"livemode": True}),
        ("charges/ch_shop", {"amount_refunded": 50}),
        ("charges/ch_shop", {"refunded": False}),
    ],
)
def test_incomplete_or_unrelated_refund(resource, change):
    records = provider_records()
    records[resource].update(change)
    with pytest.raises(ValueError, match="completed full reversal"):
        verify(records)


def test_explicit_refund_file_cannot_fall_back_to_paid_only(tmp_path, monkeypatch):
    refund_file = tmp_path / "refund.json"
    refund_file.write_text('{"id":null}')
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify",
            "--config",
            "unused",
            "--session-file",
            "unused",
            "--reference",
            "tissues",
            "--amount-minor",
            "75",
            "--currency",
            "usd",
            "--full-refund-file",
            str(refund_file),
        ],
    )
    with pytest.raises(SystemExit) as caught:
        main()
    assert caught.value.code == 2

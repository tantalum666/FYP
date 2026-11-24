import unicodedata

import pytest

from desk.approval_status import is_unbound_assent
from desk.shop_checkout.conversation import shop_quote_subject


def _wording(message):
    return unicodedata.normalize("NFKC", message).strip().casefold()


@pytest.mark.parametrize(
    "message",
    [
        "Yes.",
        "Confirm.",
        "Yes, okay",
        "Yes do them all!",
        "both",
        "all of them",
        "go ahead",
        "Please accept them all.",
        "一起可以了。",
        "都好啊。",
        "Yes, confirm it.",
        " YES，please approve that！ ",
        "Okay — kindly accept both.",
        "Sure; go ahead and confirm all of them, please!",
        "Yep, do it.",
        "是的，请确认。",
        "好的，麻烦您帮我确认一下吧！",
        "可以，都确定吧。",
        "好啊确认它。",
    ],
)
def test_unbound_assent(message):
    assert is_unbound_assent(_wording(message))


@pytest.mark.parametrize(
    "message",
    [
        "",
        "please!",
        "Yes, confirm the shop order.",
        "Sure, recover shop order.",
        "OK, approve $19.50.",
        "Yes, confirm the second one.",
        "Yes, confirm it. Add a task note: shipped.",
        "Task note: yes, confirm it.",
        "Yes, confirm it?",
        "Can you confirm it",
        'Yes, "confirm it".',
        "Yes, don't confirm it.",
        "好的，请确认退款。",
        "可以，确认 42 元。",
        "任务备注：好的，确认吧。",
        "好的，请确认？",
        "可以，确认吗",
        "「好的，确认吧。」",
        "好，不要确认。",
    ],
)
def test_not_unbound_assent(message):
    assert not is_unbound_assent(_wording(message))


@pytest.mark.parametrize("zh", [False, True])
@pytest.mark.parametrize(
    ("quote", "expected"),
    [
        ({"name": "Rice", "terms": {"quantity": 3}}, "Rice × 3"),
        (
            {"name": "Tea", "terms": {"quantity": 4, "items": [{"product_id": 17, "quantity": 4}]}},
            "Tea × 4",
        ),
        (
            {"item_names": {"29": "茶杯"}, "terms": {"items": [{"product_id": 29, "quantity": 2}]}},
            "茶杯 × 2",
        ),
    ],
)
def test_single_quote_subject(quote, expected, zh):
    assert shop_quote_subject(quote, zh) == expected


@pytest.mark.parametrize(("zh", "expected"), [(False, "2 products"), (True, "2 种商品")])
def test_mixed_quote_subject(zh, expected):
    quote = {
        "item_names": {"17": "Tea", "29": "Cup"},
        "terms": {"items": [{"product_id": 17, "quantity": 4}, {"product_id": 29, "quantity": 2}]},
    }
    assert shop_quote_subject(quote, zh) == expected


@pytest.mark.parametrize(
    ("quote", "error"),
    [
        ({"name": "Rice", "terms": {}}, KeyError),
        ({"item_names": {"17": "Tea"}, "terms": {"items": [{"product_id": 17}]}}, KeyError),
        ({"item_names": {}, "terms": {"items": [{"product_id": 17, "quantity": 2}]}}, KeyError),
        ({"name": "Tea", "terms": {"quantity": 0}}, ValueError),
        ({"terms": {"items": "bad"}}, ValueError),
    ],
)
def test_malformed_quote_subject(quote, error):
    with pytest.raises(error):
        shop_quote_subject(quote, False)

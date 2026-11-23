"""A changed checkout can need owner review at the very same total."""

from desk.approval_status import _commerce


class RepricedShop:
    kind = "SHOP"

    def pending_reviews(self, db, chat, now, limit):
        return [
            {
                "id": "original-review",
                "state": "reprice",
                "review_minor": 3300,
                "quote": {"name": "Tissues", "terms": {"quantity": 2, "total_minor": 3300}},
                "previous": {"terms": {"total_minor": 3300}},
            }
        ], False


def test_approval_overview_explains_equal_total_reprice_in_both_languages():
    for zh, expected in ((True, "结算内容有变化"), (False, "changed checkout terms")):
        items, limited = _commerce(RepricedShop(), None, None, None, zh)
        assert not limited and len(items) == 1
        assert items[0].revised and expected in items[0].reason
        assert items[0].reason.count("HK$33.00") == 1
        assert items[0].commerce_ref == ("SHOP", "original-review", 3300)

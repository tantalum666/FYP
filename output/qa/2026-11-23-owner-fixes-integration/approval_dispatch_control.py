"""Compare plain, inferred and explicitly selected consent on separate synthetic desks."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from desk.app import COOKIE
from test_conversation_shop_checkout import Shop, quote
from test_real_flight_checkout import BUY, action, ask, desk, research


def run_case(mode):
    with TemporaryDirectory() as name:
        instance = desk.__wrapped__(Path(name).resolve())
        chat, _, _ = research(instance)
        instance.account["connected"] = True
        view = ask(instance.c, "purchase", BUY, chat)["live_flight_checkout"]
        offers = action(instance, view, chat, "search")
        live = action(instance, offers, chat, "select", 1)
        assert live["state"] == "review"
        session = instance.c.cookies[COOKIE]
        commerce = instance.r.shop_orders
        commerce.enabled, commerce.provider = True, Shop()
        row = commerce.attach(quote(), "shop-ref", {"kind": "owner", "id": "owner", "session": session},
                              instance.r.voice.conversations.entries[chat])
        body = {"message": "yes", "conversation_id": chat}
        if mode in ("inferred", "selected"):
            body["shopping_review"] = {"id": row["id"], "version": row["version"], "amount_minor": row["review_minor"]}
        if mode == "selected":
            body["selected_commerce_card"] = True
        before = commerce.provider.submissions
        result = instance.c.post("/api/assistant/messages", headers={"X-Operation-Id": "consent"}, json=body)
        result.raise_for_status()
        reply = result.json()
        shop_state = commerce.read(row["id"], instance.r.voice.conversations.owner(
            {"kind": "owner", "session": session}), chat)["state"]
        actual = {"kind": reply["kind"], "shop_state": shop_state,
                  "shop_submissions": commerce.provider.submissions-before,
                  "flight_submissions": len(instance.source.submitted)}
        assert not instance.source.submitted
        return actual


if __name__ == "__main__":
    out = {mode: run_case(mode) for mode in ("plain", "inferred", "selected")}
    Path(sys.argv[1]).write_text(json.dumps(out, indent=2) + "\n")

"""Bind merchant-specific review services to the existing ordinary chat lifecycle."""

from . import commerce_aftercare
from .flight_booking import conversation as flights
from .shop_checkout import conversation as shopping


def can_resume(runtime, principal, payload):
    if payload.shopping_review:
        return runtime.shop_orders.can_resume(
            principal, payload.conversation_id, payload.shopping_review, payload.task_id
        )
    return runtime.flight_bookings.can_resume(
        principal, payload.conversation_id, payload.flight_review, payload.task_id
    ) or (
        not payload.flight_review
        and runtime.shop_orders.can_resume(
            principal, payload.conversation_id, None, payload.task_id
        )
    )


def turn(runtime, payload, principal, chat):
    if result := commerce_aftercare.turn(runtime, payload, principal, chat):
        return result
    if payload.shopping_review:
        return shopping.turn(runtime, payload, principal, chat)
    if payload.flight_review:
        return flights.turn(runtime, payload, principal, chat)
    if (
        chat
        and principal
        and principal.get("kind") == "owner"
        and runtime.shop_orders.enabled
        and runtime.flight_bookings.enabled
        and runtime.personal_context.visible(principal)
        and payload.message.strip().rstrip("。？?").casefold()
        in {"查一下订单", "查询订单", "订单状态", "查看订单"}
        and runtime.shop_orders.listing(principal, chat.id)
        and runtime.flight_bookings.listing(principal, chat.id)
    ):
        return {
            "mode": "local",
            "kind": "clarify",
            "message": "请指定购物订单或航班订单。",
            "saved": False,
        }
    return shopping.turn(runtime, payload, principal, chat) or flights.turn(
        runtime, payload, principal, chat
    )


def present(runtime, reply, key, principal, chat, payload, *, cached=False):
    for quote_field, result_field, service, render, lang in (
        (
            "sandbox_quote",
            "flight_booking",
            runtime.flight_bookings,
            flights.describe,
            payload.language,
        ),
        (
            "shop_quote",
            "shopping_order",
            runtime.shop_orders,
            shopping.describe,
            shopping.language_for(payload.message, payload.language),
        ),
    ):
        if cached and reply.get(result_field):
            row = service.read(reply[result_field]["id"], service.owner(principal), chat.id)
        elif quote_field in reply:
            row = service.attach(reply[quote_field], key, principal, chat)
        else:
            continue
        result = {k: v for k, v in reply.items() if k != quote_field}
        return {**result, "kind": result_field, result_field: row, "message": render(row, lang)}
    return reply


def tool_available(runtime, name, *, scoped):
    if name == "sandbox_shop_quote":
        return scoped and runtime.shop_orders.enabled
    if name == "sandbox_flight_quote":
        return scoped and runtime.flight_bookings.enabled
    return True


def context_instructions(runtime, principal, chat, context):
    instructions = []
    if runtime.shop_orders.enabled:
        orders = runtime.shop_orders.listing(principal, chat.id)
        if orders:
            context["test_shop_orders"] = [
                {k: row[k] for k in ("quote", "state", "receipt")} for row in orders[:3]
            ]
        instructions.append(
            "For an owner asking to buy a product (买、购买 or 购物), use sandbox_shop_quote for the product name in its original language and exact quantity. The shop quotes items and Hong Kong delivery. For existing orders use the matching chat receipt; use the recorded gross charge, successful refund and net separately. A buyer cancellation or refund is confirmed only by the local merchant/payment receipts. You cannot refund, pay or approve a revision."
        )
    if runtime.flight_bookings.enabled:
        if rows := flights.prompt_context(runtime, principal, chat):
            context["test_flight_bookings"] = rows
            instructions.append(
                "For questions about these existing LetsFG test bookings use their verified states. Only a completed record with a PNR and captured amount confirms a simulated booking. Stopping an in-progress order and refunding an issued ticket are different. Only a verified supplier read can establish a released hold. Do not create another quote to check an existing order."
            )
        instructions.append(
            "For an owner asking to book a flight (订票 or 订航班), use sandbox_flight_quote for its initial test fare. Only the owner can approve. Distinguish booking from real-market fare research and ask if the itinerary is unclear."
        )
    if instructions:
        instructions.append("Monetary fields ending in _minor are HKD minor units.")
    return "\n".join(["", *instructions]) if instructions else ""

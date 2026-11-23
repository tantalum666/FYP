"""Bind merchant-specific review services to the existing ordinary chat lifecycle."""

from . import commerce_aftercare
from .store import DomainError
from .commerce_review import language_for
from .flight_booking import calendar_handoff
from .flight_booking import conversation as flights
from .shop_checkout import conversation as shopping


def follow_orders(runtime):
    """Run on the desk even while its conversation surface is closed."""
    for service in (runtime.shop_orders, runtime.flight_bookings):
        try:
            service.follow_one()
        except DomainError as error:
            # A concurrent decision or privacy change invalidates this read.
            if error.code not in {
                "COMMERCE_FOLLOW_SCOPE_CHANGED",
                "SHOP_REVIEW_CHANGED",
                "FLIGHT_REVIEW_CHANGED",
                "SHOP_NOT_FOUND",
                "FLIGHT_NOT_FOUND",
            }:
                raise


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
    if result := calendar_handoff.turn(runtime.flight_bookings, payload, principal, chat):
        return result
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
    lang = language_for(payload.message, payload.language)
    if "booked_flight_calendar" in reply:
        return calendar_handoff.preview_from_function(
            runtime.flight_bookings, payload, principal, chat, reply["booked_flight_calendar"]
        )
    choice = getattr(payload, "calendar_flight_choice", None)
    calendar_requested = getattr(payload, "flight_calendar_requested", False) or choice is not None
    if alternatives := reply.get("flight_alternatives"):
        if calendar_requested or alternatives.get("avoid_calendar_conflicts"):
            try:
                alternatives = runtime.flight_bookings.current_alternatives(alternatives, principal)
            except DomainError as error:
                if error.code not in {"FLIGHT_CALENDAR_UNKNOWN", "FLIGHT_CALENDAR_BUSY"}:
                    raise
                return {
                    "mode": "local",
                    "kind": "clarify",
                    "error": error.code,
                    "message": flights.failure(error.code, lang),
                    "saved": False,
                }
        return {
            **reply,
            "flight_alternatives": alternatives,
            "kind": "clarify",
            "saved": False,
            "message": flights.describe_alternatives(alternatives, lang),
        }
    if reply.get("kind") == "clarify" and str(reply.get("error", "")).startswith("FLIGHT_"):
        return {**reply, "message": flights.failure(reply["error"], lang)}
    for quote_field, result_field, service, render in (
        (
            "sandbox_quote",
            "flight_booking",
            runtime.flight_bookings,
            flights.describe,
        ),
        (
            "shop_quote",
            "shopping_order",
            runtime.shop_orders,
            shopping.describe,
        ),
    ):
        if cached and reply.get(result_field):
            row = service.read(reply[result_field]["id"], service.owner(principal), chat.id)
        elif quote_field in reply:
            quote = reply[quote_field]
            if calendar_requested and result_field == "flight_booking":
                # The owner's selected option carries its constraint even if the
                # model omits the optional field in a refreshed Function call.
                quote = {**quote, "avoid_calendar_conflicts": True}
                if choice is not None:
                    from .flight_booking.provider import matches_choice

                    if not matches_choice(quote, choice):
                        return {
                            "mode": "local",
                            "kind": "clarify",
                            "message": flights.failure("FLIGHT_CHOICE_CHANGED", lang),
                            "saved": False,
                        }
                    quote["search_terms"] = {
                        **choice.model_dump(exclude_none=True),
                        "avoid_calendar_conflicts": True,
                    }
            row = service.attach(quote, key, principal, chat)
        else:
            continue
        result = {k: v for k, v in reply.items() if k != quote_field}
        if cached and reply.get("flight_calendar_link") and result_field == "flight_booking":
            message = calendar_handoff.linked_message(service, row["id"], principal, chat.id, lang == "zh")
            return {**result, result_field: row, "message": message}
        if (
            cached
            and reply.get("commerce_note")
            and row["version"] == reply[result_field]["version"]
        ):
            return {**result, result_field: row}
        result.pop("commerce_note", None)
        return {**result, "kind": result_field, result_field: row, "message": render(row, lang)}
    return reply


def tool_available(runtime, name, *, scoped):
    if name == "sandbox_shop_quote":
        return scoped and runtime.shop_orders.enabled
    if name in {"sandbox_flight_quote", "booked_flight_calendar_draft"}:
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
            "For an owner asking to shop (买、购买 or 购物), call sandbox_shop_quote once with every requested product name in its original language and its exact quantity. Ask about any unclear item before quoting the basket. The shop quotes the whole cart and Hong Kong delivery. For existing orders use the matching chat receipt. Its net deducts only settled refunds. Report pending funds separately, unknown amounts as unverified and last_verified amounts as historical. A buyer cancellation or refund is confirmed only by the local merchant/payment receipts. You cannot refund, pay or approve a revision."
        )
    if runtime.flight_bookings.enabled:
        if rows := flights.prompt_context(runtime, principal, chat):
            context["test_flight_bookings"] = rows
            instructions.append(
                "For questions about these existing LetsFG test bookings use their verified states. Only a completed record with a PNR and captured amount confirms a simulated booking. Stopping an in-progress order and refunding an issued ticket are different. Only a verified supplier read can establish a released hold. Do not create another quote to check an existing order. To put a booked itinerary on the desk calendar, use booked_flight_calendar_draft so its supplier record determines the times and a separate owner review can save it."
            )
        instructions.append(
            "For an owner asking to book a flight (订票 or 订航班), use sandbox_flight_quote for its initial test fare. When the owner asks to avoid their schedule, set avoid_calendar_conflicts=true. The fare Function compares locally, so this comparison does not need a separate calendar_query. Keep it on when rechecking that choice. Only the owner can approve. Distinguish booking from real-market fare research and ask if the itinerary is unclear."
        )
    if instructions:
        instructions.append("Monetary fields ending in _minor are HKD minor units.")
    return "\n".join(["", *instructions]) if instructions else ""

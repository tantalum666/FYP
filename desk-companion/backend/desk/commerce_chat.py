"""Bind merchant-specific review services to the existing ordinary chat lifecycle."""

from . import commerce_aftercare
from .store import DomainError
from .commerce_review import language_for
from .flight_booking import calendar_handoff
from .flight_booking import conversation as flights
from .flight_booking import shortlist
from .flight_booking import live_chat
from .flight_booking import market_search
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
    if not payload.flight_review and not payload.shopping_review and runtime.live_flight_checkouts.can_resume(
        principal, payload.conversation_id, None, payload.task_id
    ):
        return True
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
    if result := live_chat.turn(runtime, payload, principal, chat):
        return result
    if result := commerce_aftercare.turn(runtime, payload, principal, chat):
        return result
    if result := shortlist.turn(runtime.flight_bookings, payload, principal, chat):
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
    if request := reply.get("market_flight_request"):
        try:
            request = market_search.accepted_airports(request, payload.message, chat)
        except DomainError as error:
            return {"mode":"local", "kind":"clarify", "saved":False, "error":error.code,
                    "message":flights.failure(error.code,language_for(payload.message,payload.language))}
        view = runtime.live_flight_checkouts.start_market(principal, chat, request, key)
        return live_chat.reply(view, chat, payload.message, payload.language)
    if proposal := reply.get('proposal'):
        if not cached:
            runtime.live_flight_checkouts.bind(principal, chat, proposal)
    if reply.get('live_flight_review'):
        return live_chat.reply(runtime.live_flight_checkouts.start(principal,chat),chat,payload.message,payload.language)
    if cached and reply.get('kind')=='live_flight_checkout':
        ident=reply.get('live_id')
        view=(runtime.live_flight_checkouts.view(principal,chat.id,ident) if ident
              else runtime.live_flight_checkouts.start(principal,chat))
        return live_chat.reply(view,chat,payload.message,payload.language)
    lang = language_for(payload.message, payload.language)
    if cached and reply.get("flight_shortlist_chat"):
        reply = shortlist.recover_review(runtime.flight_bookings, reply, key, principal, chat, payload)
    if request := reply.get("flight_shortlist_review"):
        return shortlist.apply_review(runtime.flight_bookings, request, key, principal, chat, lang)
    if "booked_flight_calendar" in reply:
        return calendar_handoff.preview_from_function(
            runtime.flight_bookings, payload, principal, chat, reply["booked_flight_calendar"]
        )
    choice = getattr(payload, "calendar_flight_choice", None)
    calendar_requested = getattr(payload, "flight_calendar_requested", False) or choice is not None
    if alternatives := reply.get("flight_alternatives"):
        service = runtime.flight_bookings
        if number := alternatives.get("shortlist_number"):
            if cached:
                row = service.shortlists(principal, chat.id).get(number)
                if not row:
                    return {
                        "mode": "local", "kind": "clarify", "saved": False,
                        "flight_shortlist_chat": chat.id,
                        "message": "这份航班清单已关闭。" if lang == "zh" else "That flight shortlist is closed.",
                    }
                alternatives = {**row["shortlist"], "shortlist_number": number, "original": True}
        elif cached and (chat is None or chat.id != payload.conversation_id):
            # Older replies did not bind an unselected menu to its chat or login.
            # Do not import such a reply into a new conversation on an operation retry.
            return {
                "mode": "local", "kind": "clarify", "saved": False,
                "message": "请重新查询这份旧航班清单。" if lang == "zh" else
                "Please search again for the flights from that earlier conversation.",
            }
        elif calendar_requested or alternatives.get("avoid_calendar_conflicts"):
            try:
                alternatives = service.current_alternatives(alternatives, principal)
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
        if "search_terms" in alternatives:
            alternatives = service.attach_shortlist(alternatives, key, principal, chat)
        return {
            **reply,
            **({"flight_shortlist_chat": chat.id} if alternatives.get("shortlist_number") else {}),
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


def tool_available(runtime, name, *, scoped, principal=None, chat=None):
    if name == "live_flight_search":
        return scoped and bool(principal and principal.get("kind") == "owner")
    if name == "flight_purchase_review":
        return scoped
    if name == "sandbox_shop_quote":
        return scoped and runtime.shop_orders.enabled
    if name == "revisit_flight_shortlist":
        return scoped and runtime.flight_bookings.enabled and runtime.flight_bookings.has_shortlist(
            principal, chat.id
        )
    if name in {"sandbox_flight_quote", "booked_flight_calendar_draft"}:
        return scoped and runtime.flight_bookings.enabled
    return True


def revisiting_shortlist(context):
    return (shortlist.refers_to_options(context.get("user_message", ""))
            and any(tool["name"] == "revisit_flight_shortlist" for tool in context["tools"]))


def context_instructions(runtime, principal, chat, context, *, test_selection=False):
    message = context.get("user_message", "")
    tools = {tool["name"] for tool in context["tools"]}
    if "live_flight_search" in tools:
        sandbox = test_selection or market_search.explicit_test(message, chat)
        # The owner can still work with legacy test bookings or a pinned test shortlist.
        if sandbox or revisiting_shortlist(context):
            tools.discard("live_flight_search")
        else:
            tools.discard("sandbox_flight_quote")
        context["tools"] = [tool for tool in context["tools"] if tool["name"] in tools]
    if revisiting_shortlist(context):
        # The desk has the original search and checks the calendar locally. Earlier
        # chat turns and calendar draft previews may contain private appointments.
        tools -= {"sandbox_flight_quote", "calendar_query", "flight_purchase_review"}
        context["tools"] = [tool for tool in context["tools"] if tool["name"] in tools]
        for field in context.keys() - {"user_message", "language", "tools", "now", "timezone"}:
            del context[field]
    instructions = []
    if "live_flight_search" in tools:
        instructions.append(
            "For a fresh real flight request call live_flight_search with HKD fares using the itinerary "
            "from this conversation in ONE Function call. For a multi-airport city use physical airport codes, "
            "ask once if a preference matters. If the owner accepts either airport (都行/都可以/either), use ALL "
            "physical IATA codes from the preceding question in the appropriate array. Carry forward the date, "
            "passenger count, checked baggage and constraints. Resolve relative dates in the owner's time zone. "
            "Never turn airport flexibility into selection or payment. Ask only for a missing requirement. "
            "Never substitute fictional fares. The supplier and secure checkout verify total, baggage and consent."
        )
    if "flight_purchase_review" in tools:
        instructions.append(
            "For a purchase of a previously shown real Kiwi fare use flight_purchase_review. "
            "Its original linked quote, checked baggage, dates and passenger count govern. "
            "Never switch a real ticket to the fictional sandbox. Only the owner can purchase in the private checkout review."
        )
    if runtime.shop_orders.enabled:
        orders = runtime.shop_orders.listing(principal, chat.id)
        if orders:
            context["test_shop_orders"] = [
                {k: row[k] for k in ("quote", "state", "receipt")} for row in orders[:3]
            ]
        instructions.append(
            "For an owner asking to shop (买、购买 or 购物), call sandbox_shop_quote once with every exact product and quantity, budget_minor and currency, and all required variant attributes. For alternatives keep the same product family and only quantities the owner allowed. Ask about unclear constraints. The shop quotes the whole cart and Hong Kong delivery. For existing orders use the matching chat receipt. Its net deducts only settled refunds. Report pending funds separately, unknown amounts as unverified and last_verified amounts as historical. A buyer cancellation or refund is confirmed only by the local merchant/payment receipts. You cannot select a substitute, refund, pay or approve a revision."
        )
    if runtime.flight_bookings.enabled:
        if "revisit_flight_shortlist" in tools:
            instructions.append(
                "Use revisit_flight_shortlist for earlier flight options, including choosing one "
                "by its original number. It checks the calendar locally when requested. "
                "Ask the desk to show the options if the choice is unclear."
            )
        if "revisit_flight_shortlist" in tools or (
            tools & {"live_flight_search", "sandbox_flight_quote"} and (
                shortlist.flight_request(message) or
                any(shortlist.flight_request(turn.get("text", "")) for turn in chat.items[-2:])
            )
        ):
            # The fare service reads the calendar locally. Its Session needs neither
            # the automatic agenda snapshot nor previews of local calendar drafts.
            context.pop("calendar", None)
            context.pop("initiative", None)
            for approval in context.get("pending_approvals", ()):
                if approval["kind"] in {"create", "change"}:
                    approval.pop("preview", None)
        if rows := flights.prompt_context(runtime, principal, chat):
            context["test_flight_bookings"] = rows
            instructions.append(
                "For questions about these existing LetsFG test bookings use their verified states. Only a completed record with a PNR and captured amount confirms a simulated booking. Stopping an in-progress order and refunding an issued ticket are different. Only a verified supplier read can establish a released hold. Do not create another quote to check an existing order. To put a booked itinerary on the desk calendar, use booked_flight_calendar_draft so its supplier record determines the times and a separate owner review can save it."
            )
        if "sandbox_flight_quote" in tools:
            instructions.append(
                "For an owner asking to book a flight (订票 or 订航班), use sandbox_flight_quote for its initial test fare. When the owner asks to avoid their schedule, set avoid_calendar_conflicts=true. The fare Function compares locally, so this comparison does not need a separate calendar_query. Keep it on when rechecking that choice. Only the owner can approve. Distinguish booking from real-market fare research and ask if the itinerary is unclear."
            )
    if instructions:
        instructions.append("Sandbox checkout totals are in HKD minor units. Keep the owner's shopping budget in its original currency.")
    return "\n".join(["", *instructions]) if instructions else ""

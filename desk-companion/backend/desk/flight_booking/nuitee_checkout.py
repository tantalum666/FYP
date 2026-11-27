"""One private checkout decision for an opted-in Nuitée traveller test card."""

from datetime import datetime, timedelta
import re

from ..calendar import iso
from ..store import DomainError
from . import nuitee_fares
from .live_fares import minor_amount
from .nuitee_sandbox import NAME, RevisedSandboxFare, order_reference

CARD_STATES = {"card_pending", "ticketed_payment_pending", "paid_pending_ticket"}


def start(service, principal, chat, ident, version, amount, currency):
    with service.lock:
        row = service._get(ident, service.owner(principal), chat)
        if row.get("provider") != NAME or not row.get("active"):
            raise DomainError("FLIGHT_LIVE_REVIEW_CHANGED", 409)
        provider = service.provider_for(row)
        if row["version"] != version or row["state"] not in {"review", "card_pending"}:
            return {"view": service._view(row)}
        offer = row["offers"][row["selected"] - 1]
        if (currency, amount) != (offer["currency"], offer["total_minor"]) or not service._payable(
            row, offer
        ):
            raise DomainError("FLIGHT_LIVE_REVIEW_CHANGED", 409)
        if row["state"] == "card_pending":
            session = provider.unseal(row["card_session"])
            intent = provider.intent(session, offer)
            if intent["status"] != "requires_payment_method":
                return {"view": reconcile(service, principal, row)}
            try:
                if datetime.fromisoformat(session["expires"]) <= service.store.clock():
                    raise DomainError("FLIGHT_NUITEE_RECORD_EXPIRED", 409)
                provider.check_session(session, service._offer_query(row, offer), offer)
            except DomainError as exc:
                # A browser already received this intent. Preserve its original reference
                # for later reads even if the supplier will no longer honor the terms.
                service._write(principal, row, state="needs_attention", reason=exc.code)
                return {"view": service._view(row)}
        else:
            if not service._sync_source(principal, row):
                return {"view": service._view(row)}
            if row["expires"] <= iso(service.store.clock()):
                return {"view": _restart(service, principal, row, "review_expired")}
            offer = service._refresh_offer(principal, row, row["selected"])
            if offer is None or row["version"] != version:
                return {"view": service._view(row)}
            # A prebook cannot charge a card. The compare-and-swap below commits the
            # original session before the browser receives its test payment material.
            try:
                session = provider.prebook(service._offer_query(row, offer), offer)
            except RevisedSandboxFare as changed:
                choices = list(row["offers"])
                choices[row["selected"] - 1] = changed.offer
                service._write(
                    principal,
                    row,
                    offers=choices,
                    source=service._offer_source(row, changed.offer),
                    state="review" if service._payable(row, changed.offer) else "seller_only",
                    approved_minor=None,
                    reason="terms_changed",
                    receipt={},
                    expires=iso(service.store.clock() + timedelta(minutes=5)),
                )
                return {"view": service._view(row)}
            except DomainError as exc:
                # No payment material has been issued to the browser and only a prebook was attempted.
                return {"view": _restart(service, principal, row, exc.code)}
            service._write(
                principal,
                row,
                state="card_pending",
                approved_minor=amount,
                card_session=provider.seal(session),
            )
        return {
            "view": service._view(row),
            "card": {
                "publishable_key": provider.keys["public"],
                "client_secret": session["secret"],
            },
        }


def _restart(service, principal, row, reason):
    service._write(
        principal,
        row,
        state="source",
        selected=None,
        offers=[],
        receipt={},
        card_session=None,
        approved_minor=None,
        reason=reason,
    )
    return service._view(row)


def _ticket_receipt(book, session, offer, query):
    price = book.get("pricing") or {}
    payment = book.get("payment") or {}
    outbound, inbound = nuitee_fares.legs(book["journey"], query)
    if (
        book.get("bookingId") != session["booking_id"]
        or order_reference(book) != session["order_reference"]
        or outbound != offer["outbound"]
        or inbound != offer["inbound"]
        or (minor_amount(price.get("totalAmount")), price.get("currency"))
        != (offer["total_minor"], offer["currency"])
        or (minor_amount(payment.get("amount")), payment.get("currency"))
        != (offer["total_minor"], offer["currency"])
    ):
        raise ValueError("receipt does not belong to the approved itinerary")
    ticket_data = book.get("ticketData") or {}
    tickets = [
        t.get("ticketNumber")
        for t in (ticket_data.get("tickets") or [])
        if isinstance(t, dict)
        and str(t.get("status", "")).casefold() == "issued"
        and isinstance(t.get("ticketNumber"), str)
        and re.fullmatch(r"[0-9]{13}", t["ticketNumber"])
    ]
    references = [
        r["airlinePnr"]
        for r in (book.get("airlineLocators") or [])
        if isinstance(r, dict)
        and r.get("airlineCode") == "ND"
        and isinstance(r.get("airlinePnr"), str)
        and re.fullmatch(r"[A-Z0-9]{5,8}", r["airlinePnr"])
    ]
    if (
        book.get("status") == "CONFIRMED"
        and ticket_data.get("ticketedAt")
        and len(tickets) == 1
        and references
    ):
        return {"pnr": references[0], "ticket_numbers": tickets}
    return {}


def reconcile(service, principal, row):
    """A browser result can prompt this read; it cannot certify payment or ticketing."""
    if not row.get("card_session") or row["state"] in {"completed", "failed"}:
        return service._view(row)
    provider = service.provider_for(row)
    session = provider.unseal(row["card_session"])
    offer = row["offers"][row["selected"] - 1]
    intent = provider.intent(session, offer)
    state = intent.get("status")
    if state not in {"requires_capture", "succeeded"} and not session.get("booking_id"):
        if state == "canceled":
            service._record(
                principal, row, {"state": "failed", "reason": "card_authorization_canceled"}
            )
        return service._view(row)

    receipt = {"currency": offer["currency"], "processor_status": state}
    if state == "requires_capture":
        receipt["held_minor"] = offer["total_minor"]
    elif state == "succeeded" and type(intent.get("amount_received")) is int:
        receipt["charged_minor"] = intent["amount_received"]

    if not session.get("booking_id"):
        now = service.store.clock()
        if (row.get("book_next_check") or "") > iso(now):
            return service._view(row)
        try:
            provider.check_session(session, service._offer_query(row, offer), offer)
        except DomainError as exc:
            service._write(
                principal, row, state="needs_attention", reason=exc.code, receipt=receipt
            )
            return service._view(row)
        # Reserve the only original prebook before posting. The documented idempotent
        # provider operation may recover a lost acknowledgement on that exact prebook.
        service._write(
            principal,
            row,
            state="processing",
            receipt=receipt,
            book_next_check=iso(now + timedelta(seconds=30)),
        )
        try:
            session["booking_id"] = provider.book(session)
        except DomainError:
            service._write(
                principal, row, state="uncertain", reason="check_original_booking", receipt=receipt
            )
            return service._view(row)
        service._write(principal, row, card_session=provider.seal(session), book_next_check=None)

    try:
        book = provider.booking(session)
        tickets = _ticket_receipt(book, session, offer, service._offer_query(row, offer))
    except (ValueError, KeyError, TypeError, AttributeError, IndexError):
        service._write(principal, row, state="needs_attention", reason="receipt_mismatch")
        return service._view(row)

    receipt.update(tickets)
    captured = receipt.get("charged_minor") == offer["total_minor"] and state == "succeeded"
    if tickets:
        next_state = "completed" if captured else "ticketed_payment_pending"
    else:
        next_state = "paid_pending_ticket" if captured else "processing"
    if state == "canceled" or (
        state == "succeeded" and "charged_minor" in receipt and not captured
    ):
        next_state = "needs_attention"
    if row["state"] != next_state or row.get("receipt") != receipt:
        service._write(principal, row, state=next_state, receipt=receipt, reason=None)
    return service._view(row)

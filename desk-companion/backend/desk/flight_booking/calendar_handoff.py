"""Review a verified test itinerary in its original chat and save one private desk event."""

import re
from datetime import timedelta

from ..calendar import iso
from ..commerce_review import language_for
from ..store import DomainError
from .calendar_event import build_calendar_event
from .provider import BookedFlightCalendarQuery
from .service import public


DRAFT_TOOL = {
    "name": "booked_flight_calendar_draft",
    "description": (
        "When the owner wants a flight already booked in this conversation on their desk calendar, "
        "prepare a local preview from its verified supplier receipt. Supply a flight number only "
        "when specified. Leave unknown times and amounts to the receipt. The owner separately "
        "confirms on the desk. This function cannot save, pay, book or modify a remote calendar."
    ),
    "parameters": BookedFlightCalendarQuery.model_json_schema(),
}


_COMMANDS = {
    "preview": r"(?:(?:请|帮我|请帮我)?(?:把|將|将)?(?:这趟|这个|这张|已订的|我的)?(?:已经订好的|已订的)?(?:测试)?(?:航班|机票|行程)(?:加到|加入|添加到|放进)(?:我的)?(?:桌面)?日历|(?:add|put) (?:this|my|the) (?:booked |test )?(?:flight|itinerary) (?:to|in) (?:my |the )?(?:desk )?calendar)",
    "save": r"(?:确认(?:加入|添加到|保存到)(?:桌面)?日历|confirm (?:adding|saving) (?:this |the )?flight to (?:my |the )?(?:desk )?calendar)",
    "dismiss": r"(?:暂不加入日历|取消加入日历|skip adding (?:this |the )?flight to (?:my |the )?(?:desk )?calendar)",
    "read": r"(?:查看航班日程|查看已加入的航班|check (?:this |the )?flight on (?:my |the )?(?:desk )?calendar)",
}


def _select(service, owner, chat, ref, action, flight_number):
    if ref:
        row = service._get(ref.id, owner, chat)
        if flight_number and not any(
            s["flight"].replace(" ", "") == flight_number for s in row["quote"]["segments"]
        ):
            return None
        return row
    with service.store.connection() as db:
        rows = db.execute(
            """SELECT id FROM sandbox_flight_bookings WHERE owner=? AND chat=?
               AND json_extract(data,'$.state')='completed'
               AND (?='preview' OR json_extract(data,'$.calendar_preview') IS NOT NULL
                    OR json_extract(data,'$.calendar_event_id') IS NOT NULL)
               AND (? IS NULL OR EXISTS (SELECT 1 FROM json_each(data,'$.quote.segments') leg
                    WHERE replace(json_extract(leg.value,'$.flight'),' ','')=?)) LIMIT 2""",
            (owner, chat, action, flight_number, flight_number),
        ).fetchall()
    return service._get(rows[0]["id"], owner, chat) if len(rows) == 1 else None


def _scope(service, db, principal, owner, chat, row):
    service.runtime.personal_context.require_owner_transaction(db, principal)
    if not db.execute(
        "SELECT 1 FROM sandbox_flight_bookings WHERE id=? AND owner=? AND chat=? AND serial=?",
        (row["id"], owner, chat, row["_serial"]),
    ).fetchone():
        raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
    return service.store.settings(db)["timezone"]


def linked_message(service, ident, principal, chat, zh):
    owner = service.owner(principal)
    row = service._get(ident, owner, chat)
    with service.store.connection() as db:
        _scope(service, db, principal, owner, chat, row)
        found = db.execute(
            "SELECT 1 FROM events WHERE id=? AND deleted=0", (row.get("calendar_event_id"),)
        ).fetchone()
    if found:
        return (
            "已在桌面日历查到这趟测试航班。"
            if zh
            else "I found this test flight on your desk calendar."
        )
    return "原航班日程已移除。" if zh else "The original flight event has been removed."


def turn(service, payload, principal, chat):
    action = next(
        (
            name
            for name, pattern in _COMMANDS.items()
            if re.fullmatch(pattern, payload.message.strip().rstrip("。.！!"), re.I)
        ),
        None,
    )
    if not action:
        return None
    return _review(service, payload, principal, chat, action)


def preview_from_function(service, payload, principal, chat, arguments):
    query = BookedFlightCalendarQuery.model_validate(arguments)
    number = query.flight_number.replace(" ", "") if query.flight_number else None
    return _review(service, payload, principal, chat, "preview", number)


def _review(service, payload, principal, chat, action, flight_number=None):
    zh = language_for(payload.message, payload.language) == "zh"
    ref = payload.flight_review if payload.selected_commerce_card else None

    def reply(message, row=None):
        if row is None:
            return {"kind": "clarify", "mode": "local", "saved": False, "message": message}
        return {
            "kind": "flight_booking",
            "mode": "local",
            "saved": bool(row.get("calendar_event_id")),
            "flight_booking": public(row),
            "commerce_note": True,
            "message": message,
            "flight_calendar_link": bool(row.get("calendar_event_id")),
        }

    if (
        not service.enabled
        or not chat
        or payload.attachment_ids
        or chat.attachment_ids
        or (payload.selected_commerce_card and payload.shopping_review)
    ):
        return reply(
            "请在这趟航班的原对话里单独确认日历操作。"
            if zh
            else "Use the original flight conversation to review the calendar action."
        )
    owner = service.owner(principal)
    with service.lock:
        row = _select(service, owner, chat.id, ref, action, flight_number)
        if row is None:
            return reply(
                "请从原对话里已出票的那张机票选择加入日历。"
                if zh
                else "Choose the booked flight on its receipt in the original chat."
            )
        if row.get("calendar_event_id"):
            return reply(linked_message(service, row["id"], principal, chat.id, zh), row)
        if ref and (
            ref.version != row["version"] or ref.amount_minor != public(row)["review_minor"]
        ):
            raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
        if action == "read":
            return reply("这趟航班还没有加入日历。" if zh else "This flight has no desk event yet.")
        if action == "dismiss":
            if row.pop("calendar_preview", None):
                with service.store.connection(write=True) as db:
                    _scope(service, db, principal, owner, chat.id, row)
                    row["version"] += 1
                    service._write_row(db, row)
            return reply("已收起日历草稿。" if zh else "Calendar draft dismissed.", row)
        if row["state"] != "completed" or not row.get("remote"):
            return reply(
                "需要先查实出票及模拟扣款。"
                if zh
                else "The booking and its test charge need verification first."
            )
        try:
            service._refresh(row, required=True)
            with service.store.connection(write=True) as db:
                zone = _scope(service, db, principal, owner, chat.id, row)
                event = build_calendar_event(row, zone).event.model_dump(mode="json")
                now = service.store.clock()
                draft = row.get("calendar_preview") or {}
                reviewed = draft.get("event") == event and draft.get("expires", "") > iso(now)
                if not reviewed:
                    row["calendar_preview"] = {
                        "event": event,
                        "expires": iso(now + timedelta(minutes=5)),
                    }
                    row["version"] += 1
                    service._write_row(db, row)
                if action == "preview" or not reviewed:
                    return reply(
                        "请核对这趟航班的日历时间。"
                        if zh
                        else "Review the flight times for your calendar.",
                        row,
                    )
        except DomainError as error:
            if error.code not in {"FLIGHT_CALENDAR_UNVERIFIED", "FLIGHT_PROVIDER_UNAVAILABLE"}:
                raise
            return reply(
                "暂时无法核准这趟航班的回执和时间。"
                if zh
                else "I could not verify this itinerary and its receipt."
            )

        def save(db):
            zone = _scope(service, db, principal, owner, chat.id, row)
            create = build_calendar_event(row, zone)
            preview = row["calendar_preview"]
            if create.event.model_dump(mode="json") != preview["event"] or preview[
                "expires"
            ] <= iso(service.store.clock()):
                raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
            result = service.store.insert_events(db, create, "assistant")
            row["calendar_event_id"] = result["event_ids"][0]
            row.pop("calendar_preview")
            row["version"] += 1
            service._write_row(db, row)
            return result

        service.store.operation(
            "flight-calendar/" + row["id"], {"type": "flight_calendar", "booking": row["id"]}, save
        )
        row = service._get(row["id"], owner, chat.id)
        return reply(linked_message(service, row["id"], principal, chat.id, zh), row)

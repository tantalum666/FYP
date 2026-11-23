"""Owner-reviewed test flights. LetsFG owns fulfillment; the desk records exact approvals."""

from datetime import timedelta
import json
import os

from ..calendar import iso
from ..commerce_review import ChatReviews
from ..store import DomainError
from .calendar_fit import check_itineraries
from .timetable import departure_day
from .provider import FlightQuery, LetsFG, PNR, booking_id, matched, matches_choice, minor, select_fare


def _flight_identity(legs):
    return tuple((s["flight"], s["origin"], s["destination"], s["departs"][:10]) for s in legs)


def _option_query(row, leg, ceiling, calendar):
    terms = FlightQuery.model_validate(row["original_search"])
    ceilings = (terms.max_hkd, row.get("shortlist_max_hkd"), ceiling)
    return terms.model_copy(update={
        "flight_number": leg["flight"],
        "nonstop": True,
        "max_hkd": min((cap for cap in ceilings if cap is not None), default=None),
        "avoid_calendar_conflicts": bool(
            terms.avoid_calendar_conflicts or row.get("shortlist_calendar") or calendar
        ),
    })


def public(row):
    quote = row["quote"]
    return {
        "id": row["id"],
        "version": row["version"],
        "state": row["state"],
        "segments": quote["segments"],
        "adults": quote["adults"],
        "currency": quote["currency"],
        "quoted_minor": quote["total_minor"],
        "approved_minor": row["approved"],
        "review_minor": row["question"]["new"] if row["question"] else quote["total_minor"],
        **(
            {"calendar_fit": row.get("calendar_fit", "unknown")}
            if quote.get("avoid_calendar_conflicts")
            and row["state"] in {"quoted", "reprice", "submit_unknown"}
            else {}
        ),
        **(
            {"can_find_other": True}
            if row["state"] == "quoted"
            and row.get("calendar_fit") in {"conflict", "unknown"}
            and quote.get("search_terms")
            and not row.get("remote")
            and row.get("approved") is None
            else {}
        ),
        "review_deadline_ms": row["question"]["expires"] if row["question"] else None,
        "previous_minor": row["question"]["old"] if row["question"] else None,
        "pnr": row.get("pnr") if row["state"] == "completed" else None,
        "charged_minor": row.get("capture") if row["state"] == "completed" else None,
        "released": row["state"] in {"failed", "stopped"} and row.get("released", False),
        "stop_status": row.get("stop_status"),
        **({"calendar_linked": True} if row.get("calendar_event_id") else {}),
        **(
            {
                "calendar_preview": {
                    **row["calendar_preview"]["event"],
                    "fit": row["calendar_preview"].get("fit", "unknown"),
                }
            }
            if row.get("calendar_preview") and row["state"] == "completed"
            else {}
        ),
    }


class FlightBookings(ChatReviews):
    follow_states = ("submitting", "processing", "answering", "stopping", "reprice")
    _open_shortlist = (
        "json_extract(data,'$.state') IN ('shortlisted','quoted','expired') "
        "AND json_extract(data,'$.approved') IS NULL AND json_extract(data,'$.remote') IS NULL"
    )

    def __init__(self, runtime):
        super().__init__(runtime, "FLIGHT")
        self.provider = LetsFG()
        self.enabled = os.getenv("DESK_LETSFG_SANDBOX_ENABLED") == "1"

    def prepare(self, query, *, excluding=()):
        if not self.enabled:
            raise DomainError("FLIGHT_SANDBOX_DISABLED", 403)
        when = departure_day(self.store.clock(), query.origin)
        if query.avoid_calendar_conflicts:
            with self.store.connection() as db:
                if self.store.settings(db)["hide_private"]:
                    raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)
            candidates = self.provider.candidates(query, when)
            if excluding:
                candidates = [
                    offer
                    for offer in candidates
                    if _flight_identity(offer["segments"]) != excluding
                ]
                if not candidates:
                    raise DomainError("FLIGHT_NO_OTHER", 409)
            with self.store.connection() as db:
                fits = check_itineraries(self.store, db, candidates)
            quote = {**select_fare(candidates, query, fits), "avoid_calendar_conflicts": True}
        else:
            quote = self.provider.quote(query, when)
        # Keep the search limits with this local quote so an explicit request for a
        # different flight can reuse the date, party, carrier and budget.
        quote["search_terms"] = query.model_dump(mode="json", exclude_none=True)
        if "alternatives" in quote:
            return {"flight_alternatives": quote, "saved": False}
        quote["scenario"] = "price_change" if query.rehearse_price_change else "success"
        return {"sandbox_quote": quote, "saved": False}

    def find_other(self, principal, chat, ref):
        owner = self.owner(principal)
        with self.lock:
            row = self._get(ref.id, owner, chat)
            if (
                not public(row).get("can_find_other")
                or row["version"] != ref.version
                or row["quote"]["total_minor"] != ref.amount_minor
                or row["expires"] <= iso(self.store.clock())
            ):
                raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
            terms = FlightQuery.model_validate(row["quote"]["search_terms"])
            query = terms.model_copy(
                update={
                    "flight_number": None,
                    "nonstop": bool(terms.flight_number or terms.nonstop),
                    "avoid_calendar_conflicts": True,
                }
            )
            excluded = _flight_identity(row["quote"]["segments"])
        # No review lock is held across the supplier lookup. Recheck the scope
        # and original order before presenting a second, unapproved quote.
        result = self.prepare(query, excluding=excluded)
        self.owner(principal)
        with self.lock:
            prior = self._get(ref.id, owner, chat)
            if (
                prior["state"] != "quoted"
                or prior.get("approved") is not None
                or prior.get("remote")
            ):
                raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
        return result

    def current_alternatives(self, alternatives, principal):
        self.owner(principal)
        options = alternatives["alternatives"]
        with self.store.connection() as db:
            fits = check_itineraries(
                self.store, db, [dict(option, segments=[option["segment"]]) for option in options]
            )
        permitted = [option for option, fit in zip(options, fits, strict=True) if fit == "clear"]
        if not permitted:
            raise DomainError(
                "FLIGHT_CALENDAR_UNKNOWN" if "unknown" in fits else "FLIGHT_CALENDAR_BUSY", 409
            )
        return {**alternatives, "alternatives": permitted, "avoid_calendar_conflicts": True}

    def has_shortlist(self, principal, chat):
        with self.store.connection() as db:
            self.runtime.personal_context.require_owner_transaction(db, principal)
            return db.execute(
                "SELECT 1 FROM sandbox_flight_bookings WHERE owner=? AND chat=? "
                "AND json_type(data,'$.shortlist')='object' AND " + self._open_shortlist + " LIMIT 1",
                (self.runtime.voice.conversations.owner(principal), chat),
            ).fetchone() is not None

    def shortlists(self, principal, chat, *, include_closed=False):
        """Number the original offers in chat order, including closed lists in the numbering."""
        with self.store.connection() as db:
            self.runtime.personal_context.require_owner_transaction(db, principal)
            records = db.execute(
                f"""WITH lists AS (
                       SELECT row_number() OVER (ORDER BY rowid) AS number, id, data,
                              ({self._open_shortlist}) AS is_open
                       FROM sandbox_flight_bookings
                       WHERE owner=? AND chat=? AND json_type(data,'$.shortlist')='object'
                   ) SELECT number, id, is_open, json_extract(data,'$.version') AS version,
                            json_extract(data,'$.shortlist') AS shortlist FROM lists
                   WHERE is_open OR ? ORDER BY number""",
                (self.runtime.voice.conversations.owner(principal), chat, include_closed),
            )
            return {
                r["number"]: {
                    "id": r["id"], "version": r["version"], "open": bool(r["is_open"]),
                    "shortlist": json.loads(r["shortlist"]),
                }
                for r in records
            }

    def attach_shortlist(self, alternatives, key, principal, chat):
        offered = dict(alternatives)
        terms = offered.pop("search_terms")
        terms["avoid_calendar_conflicts"] = bool(offered.get("avoid_calendar_conflicts"))
        chats = self.runtime.voice.conversations
        with chats.lock:
            if chats.entries.get(chat.id) is not chat:
                raise DomainError("CONVERSATION_SCOPE_CHANGED", 409)
            saved = self.insert(
                {"shortlist": offered, "original_search": terms},
                key, principal, chat, state="shortlisted",
            )
        for number, row in self.shortlists(principal, chat.id).items():
            if row["id"] == saved["id"]:
                return {**row["shortlist"], "shortlist_number": number}
        raise DomainError("FLIGHT_REVIEW_CHANGED", 409)

    def _quote_fields(self, quote):
        return {
            "quote": quote,
            "question": None,
            "approved": None,
            "expires": iso(self.store.clock() + timedelta(minutes=15)),
            "remote": None,
            "next_read": 0,
            "scenario": quote["scenario"],
        }

    def attach(self, quote, key, principal, chat):
        saved = self.insert(self._quote_fields(quote), key, principal, chat)
        if quote.get("avoid_calendar_conflicts"):
            return self.read(saved["id"], self.owner(principal), chat.id)
        return public(saved)

    def _recheck_option(self, leg, query):
        # A flight number can appear at two different times in the same day's inventory.
        # A fresh offer ID and fare may change; the reviewed itinerary must still match.
        try:
            fares = self.provider.candidates(query, departure_day(self.store.clock(), query.origin))
            offer = next((fare for fare in fares if fare["segments"] == [leg]), None)
        except DomainError as error:
            if error.code not in {"FLIGHT_NO_MATCH", "FLIGHT_PAST_DATE"}:
                raise
            offer = None
        if offer is None:
            return None
        return {
            **offer,
            "search_terms": query.model_dump(mode="json", exclude_none=True),
            "avoid_calendar_conflicts": query.avoid_calendar_conflicts,
            "scenario": "price_change" if query.rehearse_price_change else "success",
        }

    def review_shortlist(self, request, key, principal, chat):
        """Apply the exact option and review version captured in the owner's chat operation."""
        owner = self.owner(principal)
        if not self.enabled:
            raise DomainError("FLIGHT_SANDBOX_DISABLED", 403)
        row = self._get(request["id"], owner, chat, include_unquoted=True)
        if row.get("shortlist_operation") == key:
            if row.get("option_unavailable"):
                raise DomainError("FLIGHT_OPTION_UNAVAILABLE", 409)
            return self.read(row["id"], owner, chat) if row.get("quote") else None
        if (
            not row.get("shortlist")
            or (row["version"] != request["version"] and row.get("shortlist_pending") != key)
            or row["state"] not in {"shortlisted", "quoted", "expired"}
            or row.get("remote")
            or row.get("approved") is not None
        ):
            raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
        option = request.get("option")
        if option is not None and not 1 <= option <= len(row["shortlist"]["alternatives"]):
            raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
        quote = None
        if option is not None:
            leg = row["shortlist"]["alternatives"][option - 1]["segment"]
            query = _option_query(row, leg, request.get("max_hkd"), request.get("check_calendar"))
            original = row["original_search"]
            prior_cap = row.get("shortlist_max_hkd", original.get("max_hkd"))
            prior_calendar = row.get("shortlist_calendar", original.get("avoid_calendar_conflicts", False))
            row.update(shortlist_max_hkd=query.max_hkd, shortlist_calendar=query.avoid_calendar_conflicts)
            if query.max_hkd != prior_cap or query.avoid_calendar_conflicts != prior_calendar:
                # Admit the narrower terms before the lookup. An outage or a slow
                # response must not leave a wider approval available in another worker.
                with self.lock, self.store.connection(write=True) as db:
                    self.runtime.personal_context.require_owner_transaction(db, principal)
                    row.update(shortlist_pending=key, version=row["version"] + 1)
                    if row["state"] == "quoted":
                        row["state"] = "expired"
                    self._write_row(db, row)
            quote = self._recheck_option(leg, query)
        with self.lock, self.store.connection(write=True) as db:
            self.runtime.personal_context.require_owner_transaction(db, principal)
            row.pop("shortlist_pending", None)
            row.update(shortlist_operation=key, option_unavailable=bool(option and not quote))
            row["version"] += 1
            if option is None:
                row["state"] = "cancelled"
            elif quote:
                row.update(self._quote_fields(quote), state="quoted")
                row.pop("calendar_fit", None)
                if quote["avoid_calendar_conflicts"]:
                    self._check_calendar(row, db)
            elif row.get("quote"):
                row["state"] = "expired"
            # The serial also changes on cancellation, submission and forgetting the chat.
            self._write_row(db, row)
        if row["option_unavailable"]:
            raise DomainError("FLIGHT_OPTION_UNAVAILABLE", 409)
        return public(row) if row.get("quote") else None

    def bind_legacy_selection(self, ident, key, principal, chat, *, selection, ceiling, calendar):
        """On replay, check a fare already issued by the previous shortlist Function."""
        owner = self.owner(principal)
        row = self._get(ident, owner, chat, include_unquoted=True)
        if (
            row.get("shortlist_operation") != key or row["state"] != "quoted"
            or "shortlist_max_hkd" in row or row.get("remote") or row.get("approved") is not None
        ):
            return
        quote = row["quote"]
        leg = quote["segments"][0]
        query = _option_query(row, leg, ceiling, calendar or quote.get("avoid_calendar_conflicts"))
        with self.store.connection(write=True) as db:
            self.runtime.personal_context.require_owner_transaction(db, principal)
            row.update(shortlist_max_hkd=query.max_hkd, shortlist_calendar=query.avoid_calendar_conflicts)
            if (
                selection and row["shortlist"]["alternatives"][selection - 1]["segment"] == leg
                and matches_choice(quote, query)
            ):
                quote.update(search_terms=query.model_dump(exclude_none=True),
                             avoid_calendar_conflicts=query.avoid_calendar_conflicts)
                if query.avoid_calendar_conflicts:
                    self._check_calendar(row, db)
            else:
                self._state(row, "expired")
                row["option_unavailable"] = True
            self._write_row(db, row)
        return public(row)

    def read(self, ident, owner, chat, *, following=False):
        with self.lock:
            row = self._read_row(ident, owner, chat, following)
            if row is None:
                return None
            now = self.store.clock()
            if row["state"] == "quoted" and row["expires"] <= iso(now):
                self._state(row, "expired")
                self._save(row)
            elif row["state"] == "submitting" and row["next_read"] <= now.timestamp():
                self._state(row, "submit_unknown")
                self._save(row)
            elif (
                row["remote"]
                and row["state"] in {"processing", "reprice", "answering", "stopping"}
                and row["next_read"] <= now.timestamp()
            ):
                self._refresh(row)
            if (
                not following
                and row["quote"].get("avoid_calendar_conflicts")
                and row["state"] in {"quoted", "reprice", "submit_unknown"}
                and row.get("calendar_revision") != self.store.revision()
            ):
                with self.store.connection(write=True) as db:
                    self._check_calendar(row, db)
                    self._write_row(db, row)
            return public(row)

    def _check_calendar(self, row, db):
        fit = check_itineraries(self.store, db, [row["quote"]])[0]
        old = row.get("calendar_fit")
        if old is not None and old != fit:
            row["version"] += 1
        row.update(calendar_fit=fit, calendar_revision=self.store.revision(db))
        return fit == "clear" and (old is None or old == fit)

    def _begin_review(self, row, review, state, owner, **fields):
        # Admit one effect against the same calendar snapshot as the recorded decision.
        # The provider call happens only after the transaction commits.
        with self.store.connection(write=True) as db:
            if review.action == "confirm" and row["quote"].get("avoid_calendar_conflicts"):
                if not db.execute(
                    "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
                    (owner, iso(self.store.clock())),
                ).fetchone():
                    raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
                if not self._check_calendar(row, db):
                    self._write_row(db, row)
                    return False
            now = self.store.clock()
            if row["state"] == "quoted" and row["expires"] <= iso(now):
                self._state(row, "expired")
                self._write_row(db, row)
                return False
            if row["state"] == "reprice" and row["question"]["expires"] <= now.timestamp() * 1000:
                row["next_read"] = 0
                self._write_row(db, row)
                return False
            row.update(last_review=review.model_dump(), **fields)
            self._state(row, state)
            self._write_row(db, row)
        return True

    def _refresh(self, row, *, required=False):
        row["next_read"] = self.store.clock().timestamp() + 20
        self._save(row)
        try:
            record = self.provider.status(row["remote"])
            self._project(row, record)
        except DomainError as error:
            if error.code == "FLIGHT_PROVIDER_UNAVAILABLE":
                if required:
                    raise
                return
            self._state(row, "unverified")
        except (KeyError, TypeError, ValueError):
            self._state(row, "unverified")
        self._save(row)

    def _project(self, row, record):
        matched(record, row["remote"], row["quote"])
        if record.get("currency") != "HKD" or record.get("card_last4") != "4242":
            raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)
        state = record.get("state")
        if state == "needs_attention" and type(record.get("manual_booking")) is bool:
            row["question"] = None
            self._state(row, "manual")
            return
        if record.get("terminal") is True:
            ref = record.get("pnr")
            if (
                state == "completed"
                and (row.get("last_review") or {}).get("action") != "decline"
                and isinstance(ref, str)
                and PNR.fullmatch(ref)
                and minor(record.get("charged_amount")) == row["approved"]
            ):
                row.update(pnr=ref, capture=row["approved"], question=None)
                self._state(row, "completed")
            elif state == "failed" and not ref and record.get("charged_amount") in (None, 0):
                row.update(
                    released="hold was released" in str(record.get("message", "")).lower(),
                    question=None,
                )
                was_stopped = (
                    row.get("stop_status") in {"stopped", "stopping", "requested", "unconfirmed"}
                    and row["released"]
                    and "stop" in str(record.get("failure_reason", "")).lower()
                )
                self._state(row, "stopped" if was_stopped else "failed")
            else:
                self._state(row, "unverified")
            return
        if record.get("terminal") is not False or state not in {
            "authorised",
            "card_issued",
            "booking_in_progress",
            "awaiting_settlement",
        }:
            self._state(row, "unverified")
            return
        if row.get("stop_status") in {
            "requested",
            "stopping",
            "stopped",
            "unconfirmed",
            "with_a_person",
        }:
            row["question"] = None
            self._state(row, "stopping" if row["stop_status"] != "with_a_person" else "manual")
            return
        question = record.get("question")
        if not question:
            row["question"] = None
            self._state(row, "processing")
            return
        change = question.get("price_change") or {}
        rnd = question.get("round")
        if (
            question.get("kind") != "price_change"
            or type(rnd) is not int
            or rnd < 1
            or type(question.get("expires_at_ms")) is not int
            or change.get("currency") != "HKD"
            or minor(change.get("new_total")) <= minor(change.get("old_total"))
        ):
            self._state(row, "unverified")
            return
        pending = {
            "round": rnd,
            "old": minor(change["old_total"]),
            "new": minor(change["new_total"]),
            "expires": question["expires_at_ms"],
        }
        if row["state"] == "answering" and row["question"] == pending:
            if self.store.clock().timestamp() < row["answer_at"] + 20:
                return
            # The provider still needs a decision. Offer the current round again.
            row["approved"] = pending["old"]
        if pending["old"] != row["approved"]:
            raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)
        if pending != row["question"]:
            row["version"] += 1
        row["question"] = pending
        self._state(row, "reprice")

    def reopen(self, ident, principal, chat):
        owner = self.owner(principal)
        with self.lock:
            row = self._get(ident, owner, chat)
            if row.get("remote"):
                self._refresh(row, required=True)
            return public(row)

    def cancel(self, ref, principal, chat):
        owner = self.owner(principal)
        with self.lock:
            row = self._get(ref.id, owner, chat)
            if not row.get("remote"):
                raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
            if ref.version != row["version"] or ref.amount_minor != public(row)["review_minor"]:
                if not row.get("stop_status"):
                    raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
                return self.reopen(ref.id, principal, chat)
            self._refresh(row, required=True)
            if row["state"] == "completed":
                row["stop_status"] = "too_late"
                self._save(row)
                return public(row)
            if row["state"] in {"failed", "stopped", "unverified"}:
                return public(row)
            if row.get("stop_status") not in {None, "unconfirmed", "requested"}:
                return public(row)
            row.update(stop_status="requested", next_read=0, question=None)
            self._state(row, "stopping")
            self._save(row)
            try:
                answer = self.provider.stop(row["remote"])
                if (
                    answer.get("sandbox") is not True
                    or answer.get("booking_id", row["remote"]) != row["remote"]
                    or answer.get("status")
                    not in {"stopped", "stopping", "too_late", "with_a_person", "already_ended"}
                ):
                    raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)
                row["stop_status"] = answer["status"]
            except DomainError:
                row["stop_status"] = "unconfirmed"
            self._save(row)
            self._refresh(row)
            return public(row)

    def decide(self, review, principal, chat):
        owner = self.owner(principal)
        if not self.enabled:
            raise DomainError("FLIGHT_SANDBOX_DISABLED", 403)
        with self.lock:
            row = self._get(review.id, owner, chat)
            if row.get("last_review") == review.model_dump() and row["state"] != "submit_unknown":
                return public(row)
            if row["state"] == "reprice":
                self._refresh(row, required=True)
            view = public(row)
            if row["version"] != review.version or review.amount_minor != view["review_minor"]:
                if review.action == "confirm" and view.get("calendar_fit") in {
                    "conflict",
                    "unknown",
                }:
                    return view
                raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
            if row["state"] in {"quoted", "submit_unknown"}:
                if row["state"] == "quoted" and row["expires"] <= iso(self.store.clock()):
                    self._state(row, "expired")
                    self._save(row)
                    raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
                if review.action == "decline":
                    if row["state"] != "quoted":
                        raise DomainError("FLIGHT_OUTCOME_UNKNOWN", 409)
                    self._state(row, "cancelled")
                    self._save(row)
                else:
                    if not self._begin_review(
                        row,
                        review,
                        "submitting",
                        owner,
                        approved=view["review_minor"],
                        next_read=self.store.clock().timestamp() + 40,
                    ):
                        return public(row)
                    self._submit(row)
            elif row["state"] == "reprice":
                q = row["question"]
                if q["expires"] <= self.store.clock().timestamp() * 1000:
                    raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
                if not self._begin_review(
                    row,
                    review,
                    "answering",
                    owner,
                    answer_at=self.store.clock().timestamp(),
                    next_read=0,
                    approved=q["new"] if review.action == "confirm" else row["approved"],
                ):
                    return public(row)
                try:
                    answer = self.provider.answer(
                        row["remote"], q["round"], review.action == "confirm"
                    )
                    if answer.get("sandbox") is not True or answer.get("ok") is not True:
                        raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)
                except DomainError:
                    # A lost acknowledgement is ambiguous. Poll the original booking only.
                    pass
            else:
                raise DomainError("FLIGHT_REVIEW_CHANGED", 409)
            return public(row)

    def _submit(self, row):
        try:
            result = self.provider.submit(row["quote"], "fyp-flight-" + row["id"], row["scenario"])
            ident = booking_id(result.get("booking_id"))
            matched(result, ident, row["quote"])
            row["remote"] = ident
            if not result.get("duplicate"):
                held = result.get("held") or {}
                if (
                    held.get("currency") != "HKD"
                    or minor(held.get("amount")) != row["approved"]
                    or (held.get("card") or {}).get("last4") != "4242"
                    or result.get("charged") != 0
                ):
                    raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)
            self._state(row, "processing")
            row["next_read"] = 0
        except DomainError as error:
            self._state(
                row,
                "submit_unknown" if error.code == "FLIGHT_PROVIDER_UNAVAILABLE" else "unverified",
            )
        self._save(row)

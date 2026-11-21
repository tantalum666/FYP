"""Owner-reviewed test flights. LetsFG owns fulfillment; the desk records exact approvals."""

from datetime import timedelta
import os

from ..calendar import iso
from ..commerce_review import ChatReviews
from ..store import DomainError
from .calendar_fit import check_itineraries
from .timetable import departure_day
from .provider import FlightQuery, LetsFG, PNR, booking_id, matched, minor, select_fare


def _flight_identity(legs):
    return tuple((s["flight"], s["origin"], s["destination"], s["departs"][:10]) for s in legs)


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
    }


class FlightBookings(ChatReviews):
    follow_states = ("submitting", "processing", "answering", "stopping", "reprice")

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
        if "alternatives" in quote:
            return {"flight_alternatives": quote, "saved": False}
        # Keep the search limits with this local quote so an explicit request for a
        # different flight can reuse the date, party, carrier and budget.
        quote["search_terms"] = query.model_dump(mode="json", exclude_none=True)
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

    def attach(self, quote, key, principal, chat):
        row = {
            "quote": quote,
            "question": None,
            "approved": None,
            "expires": iso(self.store.clock() + timedelta(minutes=15)),
            "remote": None,
            "next_read": 0,
            "scenario": quote["scenario"],
        }
        saved = self.insert(row, key, principal, chat)
        if quote.get("avoid_calendar_conflicts"):
            return self.read(saved["id"], self.owner(principal), chat.id)
        return public(saved)

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

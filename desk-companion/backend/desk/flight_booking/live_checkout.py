"""Owner-only checkout from an original Kiwi research receipt. Models can open a review only."""

from datetime import timedelta
import hashlib
import json

from .. import browser_research
from ..calendar import iso
from ..commerce_review import ChatReviews
from ..store import DomainError
from . import checkout_source as sources
from .timetable import departure_day


PAYMENT_STATES = {
    "submitting",
    "processing",
    "held",
    "bank_approval",
    "needs_attention",
    "uncertain",
    "completed",
    "failed",
}
PUBLIC_OFFER = (
    "currency",
    "total_minor",
    "fare_minor",
    "ready",
    "reason",
    "outbound",
    "inbound",
    "passenger_count",
    "checked_bags",
    "checked_bag_kg",
    "booking_url",
    "fare_conditions",
    "conditions_source",
)
PUBLIC_RECEIPT = (
    "state",
    "held_minor",
    "charged_minor",
    "currency",
    "pnr",
    "action_url",
    "reason",
    "missing_fields",
)


class LiveFlightCheckouts(ChatReviews):
    enabled = True

    def __init__(self, runtime):
        super().__init__(runtime, "LIVE_FLIGHT")

    def forget_chat(self, principal, chat):
        from ..conversation import Conversations

        owner = Conversations.owner(principal)
        if not owner:
            return
        with self.lock, self.store.connection(write=True) as db:
            db.execute(
                "UPDATE live_flight_checkouts SET chat='',serial=serial+1 WHERE owner=? AND chat=?",
                (owner, chat),
            )
            db.execute(
                """UPDATE assistant_replies SET result='{"kind":"live_flight_checkout","retired":true}' WHERE
                json_extract(result,'$.live_scope.login')=? AND json_extract(result,'$.live_scope.chat')=?""",
                (owner, chat),
            )

    def _write(self, principal, row, **fields):
        with self.store.connection(write=True) as db:
            self.runtime.personal_context.require_owner_transaction(db, principal)
            row.update(fields, version=row["version"] + 1)
            self._write_row(db, row)
        return row

    def _rows(self, principal, chat):
        owner = self.owner(principal)
        with self.store.connection() as db:
            self.runtime.personal_context.require_owner_transaction(db, principal)
            return [
                dict(json.loads(r["data"]), _serial=r["serial"])
                for r in db.execute(
                    "SELECT data,serial FROM live_flight_checkouts WHERE owner=? AND chat=? ORDER BY rowid DESC",
                    (owner, chat),
                )
            ]

    def bind(self, principal, chat, proposal):
        if (
            not chat
            or not sources.is_kiwi(proposal)
            or not self.runtime.personal_context.visible(principal)
        ):
            return None
        owner = self.owner(principal)
        with self.store.connection() as db:
            saved = db.execute(
                "SELECT kind,data FROM assistant_proposals WHERE id=?", (proposal["id"],)
            ).fetchone()
        if not saved or not sources.is_kiwi(
            {"kind": saved["kind"], "data": json.loads(saved["data"])}
        ):
            return None
        key = f"original-kiwi/{owner}/{chat.id}/{proposal['id']}"
        with self.runtime.voice.conversations.lock:
            if self.runtime.voice.conversations.entries.get(chat.id) is not chat:
                raise DomainError("CONVERSATION_SCOPE_CHANGED", 409)
            return self.insert(
                {"proposal_id": proposal["id"], "active": False},
                key,
                principal,
                chat,
                state="research",
            )

    def last_proposal(self, chat):
        with self.store.connection() as db:
            r = db.execute(
                """SELECT p.id,p.data FROM live_flight_checkouts c
                JOIN assistant_proposals p ON p.id=json_extract(c.data,'$.proposal_id')
                JOIN sessions s ON s.token_hash=c.owner AND s.expires>?
                WHERE c.chat=? AND c.owner=? AND json_extract(c.data,'$.task_id') IS ?
                ORDER BY c.rowid DESC LIMIT 1""",
                (iso(self.store.clock()), chat.id, chat.owner, chat.task_id),
            ).fetchone()
            if not r or self.store.settings(db)["hide_private"]:
                return None
            return {"id": r["id"], "kind": "browser_research", "data": json.loads(r["data"])}

    def _account(self):
        auth = getattr(self.runtime, "letsfg_auth", None)
        return auth.account() if auth else {"connected": False}

    def _view(self, row):
        source = row.get("source")
        options = row.get("offers") or []
        return {
            "id": row["id"],
            "version": row["version"],
            "state": row["state"],
            "connected": bool(self._account().get("connected")),
            "source": (
                {k: v for k, v in source.items() if k not in {"job_id", "evidence"}}
                if source
                else None
            ),
            "choices": [
                {
                    **{k: o.get(k) for k in PUBLIC_OFFER},
                    "number": i + 1,
                    "payable": sources.payable(source, o),
                }
                for i, o in enumerate(options)
            ],
            "selected": row.get("selected"),
            "reason": row.get("reason"),
            "required_fields": row.get("required_fields", []),
            "receipt": {
                k: row["receipt"][k] for k in PUBLIC_RECEIPT if k in row.get("receipt", {})
            },
        }

    def _sync_source(self, principal, row):
        owner = self.owner(principal)
        try:
            state, source = sources.original(self.runtime, row["proposal_id"], owner)
        except DomainError as error:
            if error.code in {
                "DRAFT_NOT_FOUND",
                "COMPUTER_READBACK_CHANGED",
                "RUN_SESSION_EXPIRED",
                "PROVIDER_CONTEXT_CHANGED",
                "COMPUTER_SOURCE_CHANGED",
                "COMPUTER_CLEANUP_REQUIRED",
            }:
                state, source = "source_unavailable", None
            else:
                raise
        if source is None or (
            row.get("origin_digest") and sources.source_digest(source) != row["origin_digest"]
        ):
            state = "source_changed" if source and row.get("origin_digest") else state
            if row["state"] != state or not row.get("active"):
                self._write(
                    principal,
                    row,
                    state=state,
                    source=None,
                    active=True,
                    offers=[],
                    selected=None,
                    reason="original_result_changed" if state == "source_changed" else None,
                )
            return False
        if not row.get("source") or not row.get("active"):
            self._write(
                principal,
                row,
                source=source,
                origin_digest=sources.source_digest(source),
                active=True,
                state="source",
                reason=None,
            )
        return True

    def _choices(self, principal, chat, rows):
        options = []
        for row in rows[:5]:
            try:
                state, src = sources.original(
                    self.runtime, row["proposal_id"], self.owner(principal)
                )
            except DomainError as error:
                if error.code in {
                    "DRAFT_NOT_FOUND",
                    "COMPUTER_READBACK_CHANGED",
                    "RUN_SESSION_EXPIRED",
                    "PROVIDER_CONTEXT_CHANGED",
                    "COMPUTER_SOURCE_CHANGED",
                    "COMPUTER_CLEANUP_REQUIRED",
                }:
                    continue
                raise
            if state == "source":
                options.append(
                    {
                        "proposal_id": row["proposal_id"],
                        "request": src["request"],
                        "label": src["label"],
                        "listed_minor": src["listed_minor"],
                        "currency": src["currency"],
                    }
                )
        return {"state": "choose_source" if options else "no_source", "sources": options}

    def start(self, principal, chat, proposal_id=None):
        if not chat:
            raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
        owner = self.owner(principal)
        if chat.owner != owner:
            raise DomainError("CONVERSATION_NOT_FOUND", 404)
        with self.lock:
            rows = self._rows(principal, chat.id)
            if not rows and (ref := browser_research.current_chat_quote(self.runtime, chat)):
                if (
                    ref.get("record_verified")
                    and (ref.get("quote") or {}).get("supplier", {}).get("provider") == "Kiwi.com"
                ):
                    proposal_id = proposal_id or ref["proposal_id"]
            legacy = (
                sources.old_results(self.store, owner, chat.task_id, proposal_id)
                if not rows or proposal_id
                else []
            )
            if proposal_id:
                selected = next((r for r in rows if r["proposal_id"] == proposal_id), None)
                if not selected and any(r["proposal_id"] == proposal_id for r in legacy):
                    with self.store.connection() as db:
                        p = db.execute(
                            "SELECT data FROM assistant_proposals WHERE id=?", (proposal_id,)
                        ).fetchone()
                    selected = self.bind(
                        principal,
                        chat,
                        {
                            "kind": "browser_research",
                            "id": proposal_id,
                            "data": json.loads(p["data"]),
                        },
                    )
                if not selected:
                    raise DomainError("FLIGHT_SOURCE_NOT_FOUND", 404)
            elif len(rows) == 1:
                selected = rows[0]
            else:
                return self._choices(principal, chat, rows or legacy)
            if selected["state"] not in PAYMENT_STATES:
                self._sync_source(principal, selected)
            return self._view(selected)

    def view(self, principal, chat, ident):
        row = self._get(ident, self.owner(principal), chat)
        if not row.get("active"):
            raise DomainError("FLIGHT_CHECKOUT_NOT_FOUND", 404)
        with self.lock:
            if row["state"] in {"waiting_source", "research"}:
                self._sync_source(principal, row)
            return self._view(row)

    def _search(self, principal, row, *, poll=False):
        source = row["source"]
        if source["currency"] != "HKD":
            return self._write(
                principal,
                row,
                state="seller_only",
                reason="currency_not_supported",
                offers=[],
                selected=None,
            )
        if not self._account().get("connected"):
            return self._write(
                principal,
                row,
                state="source",
                reason="LETSFG_CONNECT_REQUIRED",
                offers=[],
                selected=None,
            )
        if (
            source["request"]["departure"]
            < departure_day(self.store.clock(), source["request"]["origin"]).isoformat()
        ):
            return self._write(
                principal,
                row,
                state="seller_only",
                reason="travel_date_passed",
                offers=[],
                selected=None,
            )
        try:
            query = sources.query_for(source)
        except ValueError:
            return self._write(
                principal,
                row,
                state="seller_only",
                reason="party_or_baggage_not_supported",
                offers=[],
                selected=None,
            )
        provider = self.runtime.live_flight_provider
        result = provider.search(
            query, principal=principal, search_id=row.get("search_id") if poll else None
        )
        offers = [o for o in result.get("offers", []) if sources.compatible(source, o)][:8]
        state = (
            "searching"
            if result["state"] == "searching"
            else ("offers" if offers else "seller_only")
        )
        return self._write(
            principal,
            row,
            state=state,
            search_id=result.get("search_id"),
            offers=offers,
            selected=None,
            receipt={},
            reason=result.get("reason")
            or (None if offers or state == "searching" else "no_matching_offer"),
        )

    def _refresh_offer(self, principal, row, number):
        if not 1 <= number <= len(row.get("offers", [])):
            raise DomainError("FLIGHT_LIVE_REVIEW_CHANGED", 409)
        old = row["offers"][number - 1]
        result = self.runtime.live_flight_provider.reprice(
            sources.query_for(row["source"]), old["search_id"], old["offer_id"], principal=principal
        )
        offer = next(
            (
                o
                for o in result.get("offers", [])
                if o.get("offer_id") == old["offer_id"]
                and o.get("search_id") == old["search_id"]
                and sources.compatible(row["source"], o)
            ),
            None,
        )
        if not offer:
            self._write(
                principal,
                row,
                state="source",
                reason="offer_expired_or_changed",
                offers=[],
                selected=None,
            )
            return None
        changed = sources.consent_terms(offer) != sources.consent_terms(old)
        if (
            not sources.payable(row["source"], offer)
            or changed
            or row.get("selected") != number
            or row["state"] != "review"
        ):
            choices = list(row["offers"])
            choices[number - 1] = offer
            state = "review" if sources.payable(row["source"], offer) else "seller_only"
            self._write(
                principal,
                row,
                state=state,
                selected=number,
                offers=choices,
                receipt={},
                reason=offer.get("reason") or ("terms_changed" if changed else None),
                expires=iso(self.store.clock() + timedelta(minutes=5)),
            )
        return offer

    def action(self, principal, chat, ident, action, version, number=None):
        with self.lock:
            row = self._get(ident, self.owner(principal), chat)
            if action == "status" and row["state"] in PAYMENT_STATES:
                return self._read_payment(principal, row)
            if row["version"] != version or row["state"] in PAYMENT_STATES or not row.get("active"):
                raise DomainError("FLIGHT_LIVE_REVIEW_CHANGED", 409)
            if not self._sync_source(principal, row):
                return self._view(row)
            if action == "search" and row["state"] in {
                "source",
                "offers",
                "seller_only",
                "review",
                "card_required",
                "missing_details",
                "reprice",
            }:
                self._search(principal, row)
            elif action == "status" and row["state"] == "searching":
                self._search(principal, row, poll=True)
            elif (
                action == "select"
                and row["state"] in {"offers", "review", "seller_only"}
                and number is not None
            ):
                self._refresh_offer(principal, row, number)
            elif action != "status":
                raise DomainError("FLIGHT_LIVE_REVIEW_CHANGED", 409)
            return self._view(row)

    def _record(self, principal, row, result, *, reread=False):
        state = result["state"]
        fields = {
            "state": state,
            "reason": result.get("reason"),
            "receipt": {k: result[k] for k in PUBLIC_RECEIPT if k in result},
        }
        if state == "completed" and not reread:
            fields.update(state="processing", receipt={})
        elif state == "completed":
            amount = row["offers"][row["selected"] - 1]["total_minor"]
            if not result.get("pnr") or (result.get("currency"), result.get("charged_minor")) != (
                row["source"]["currency"],
                amount,
            ):
                fields.update(
                    state="needs_attention", reason="capture_or_pnr_unverified", receipt={}
                )
        if state == "missing_details":
            fields["required_fields"] = result.get("missing_fields", [])
        if state in {"reprice", "unavailable"}:
            fields.update(
                state="source",
                offers=[],
                selected=None,
                reason=result.get("reason") or "offer_expired_or_changed",
            )
        return self._write(principal, row, **fields)

    def _read_payment(self, principal, row):
        if row["state"] in {"completed", "failed"}:
            return self._view(row)
        offer = row["offers"][row["selected"] - 1]
        try:
            result = self.runtime.live_flight_provider.status(
                row["approval_id"], offer, principal=principal
            )
        except DomainError as error:
            if error.code != "LETSFG_BOOKING_NOT_FOUND":
                raise
            result = {"state": "uncertain", "reason": "check_original_booking"}
        if row["state"] != result["state"] or any(
            row.get("receipt", {}).get(k) != v for k, v in result.items() if k in PUBLIC_RECEIPT
        ):
            self._record(principal, row, result, reread=True)
        return self._view(row)

    def confirm(self, principal, chat, ident, version, amount, currency, passengers, email):
        from .live_provider import LiveApprovedFare
        from .live_fares import LivePassenger, passenger_body

        with self.lock:
            row = self._get(ident, self.owner(principal), chat)
            if row["state"] in PAYMENT_STATES:
                return self._read_payment(principal, row)
            if (
                row["state"] != "review"
                or row["version"] != version
                or currency != row["source"]["currency"]
            ):
                raise DomainError("FLIGHT_LIVE_REVIEW_CHANGED", 409)
            if not self._sync_source(principal, row):
                return self._view(row)
            before = row["version"]
            number = row["selected"]
            offer = self._refresh_offer(principal, row, number)
            if row["version"] != before or offer is None:
                return self._view(row)
            if row["expires"] <= iso(self.store.clock()):
                self._write(
                    principal,
                    row,
                    expires=iso(self.store.clock() + timedelta(minutes=5)),
                    reason="review_expired",
                )
                return self._view(row)
            if not sources.payable(row["source"], offer) or amount != offer.get("total_minor"):
                raise DomainError("FLIGHT_LIVE_REVIEW_CHANGED", 409)
            if len(passengers) != row["source"]["request"]["adults"]:
                raise DomainError("FLIGHT_PASSENGER_DETAILS_REQUIRED", 422)
            try:
                people = [
                    LivePassenger.model_validate(person).model_dump(exclude_none=True)
                    for person in passengers
                ]
                passenger_body(sources.query_for(row["source"]), people, email)
            except ValueError:
                raise DomainError("FLIGHT_PASSENGER_DETAILS_REQUIRED", 422) from None
            handle = hashlib.sha256(f"owner-flight/{ident}/{version}".encode()).hexdigest()
            approval = LiveApprovedFare(
                approval_id=handle, query=sources.query_for(row["source"]), offer=offer
            )
            self._write(
                principal,
                row,
                state="submitting",
                approval_id=handle,
                approved_minor=amount,
                reason=None,
            )
            try:
                result = self.runtime.live_flight_provider.submit(
                    approval, people, email, principal=principal
                )
            except (DomainError, ValueError):
                # Only the original supplier journal may resolve an attempted submission.
                result = {"state": "uncertain", "reason": "check_original_booking"}
            self._record(principal, row, result)
            if row["state"] in {"processing", "held", "completed"}:
                return self._read_payment(principal, row)
            return self._view(row)

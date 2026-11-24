"""LetsFG's OAuth agent lane. Search, exact approval submission and status use separate operations."""

import hashlib
import json
import re
from urllib.parse import quote

import httpx

from ..conversation import Conversations
from ..store import DomainError, encode
from .timetable import departure_day, flight_window
from .live_fares import (
    SEARCH_ID,
    LiveApprovedFare,
    LiveFlightQuery,
    LivePassenger,
    minor_amount,
    official_url,
    party_matches,
    passenger_body,
    price_offer,
)

__all__ = ["LiveFlightProvider", "LiveFlightQuery", "LiveApprovedFare", "LivePassenger"]
BASE = "https://letsfg.co/api/"
_REUSABLE = {"held", "processing", "uncertain", "completed", "needs_attention", "bank_approval"}


def fingerprint(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


def terms(offer):
    # Display links can rotate. Every item that affects the authority to buy stays bound.
    return {
        key: offer.get(key)
        for key in (
            "account_version",
            "search_id",
            "offer_id",
            "currency",
            "fare_minor",
            "total_minor",
            "passenger_count",
            "outbound",
            "inbound",
            "checked_bags",
            "checked_bag_kg",
            "baggage_evidence",
            "fare_conditions",
            "conditions_source",
            "ready",
        )
    }


def record(state, ref=None, **values):
    return {"state": state, "booking_ref": ref, **values}


def read_booking(raw, offer, ref, *, final_read):
    if not isinstance(raw, dict):
        return record("uncertain", ref, reason="unverified_response")
    state = raw.get("state")
    currency = raw.get("currency")
    if state == "completed":
        pnr = raw.get("pnr")
        amount = minor_amount(raw.get("charged_amount"))
        if (
            final_read
            and isinstance(pnr, str)
            and re.fullmatch(r"[A-Z0-9]{5,8}", pnr)
            and pnr not in {"PENDING", "UNKNOWN"}
            and amount is not None
            and amount == offer["total_minor"]
            and currency == offer["currency"]
        ):
            return record("completed", ref, pnr=pnr, charged_minor=amount, currency=currency)
        return record(
            "needs_attention" if final_read else "processing",
            ref,
            reason="capture_or_pnr_unverified",
        )
    charge = raw.get("charged_amount", raw.get("charged", "absent"))
    if state == "failed":
        if final_read and charge != "absent" and (charge is None or minor_amount(charge) == 0):
            return record(
                "failed",
                ref,
                charged_minor=0,
                currency=offer["currency"],
                reason="supplier_failed_hold_released",
            )
        return record("needs_attention", ref, reason="failed_payment_unverified")
    btn = official_url(raw.get("approve_url"))
    if state in {
        "awaiting_your_approval",
        "awaiting_approval",
        "awaiting_bank_approval",
        "requires_action",
    }:
        return record("bank_approval", ref, action_url=btn, reason="complete_provider_approval")
    ask = raw.get("question") or raw.get("pending_question")
    if state == "needs_attention" or ask:
        is_price = isinstance(ask, dict) and (ask.get("type") or ask.get("kind")) == "price_change"
        return record(
            "needs_attention",
            ref,
            reason="new_price_requires_owner_review" if is_price else "supplier_review",
            action_url=btn,
        )
    if state in {"booking_in_progress", "processing", "pending", "card_issued"}:
        held = raw.get("held")
        if isinstance(held, dict):
            n = minor_amount(held.get("amount"))
            if (
                n is not None
                and n > 0
                and held.get("currency") == offer["currency"]
                and n == offer["total_minor"]
            ):
                return record(
                    "held",
                    ref,
                    held_minor=n,
                    currency=offer["currency"],
                    **({"charged_minor": 0} if minor_amount(raw.get("charged")) == 0 else {}),
                )
            return record("needs_attention", ref, reason="hold_amount_or_currency_changed")
        return record("processing", ref)
    return record("uncertain", ref, reason="supplier_state_unverified")


class LiveFlightProvider:
    def __init__(self, runtime, transport=None):
        self.runtime = runtime
        self.store = runtime.store
        self.auth = runtime.letsfg_auth
        self.transport = transport

    def _request(self, method, path, token, *, body=None):
        try:
            with httpx.Client(
                base_url=BASE,
                transport=self.transport,
                trust_env=False,
                follow_redirects=False,
                timeout=15,
            ) as client:
                res = client.request(
                    method,
                    path,
                    headers={
                        "Authorization": "Bearer " + token,
                        "User-Agent": "FYP-Desk-Companion/1.0",
                        "X-Client-Type": "fyp-desk-companion",
                        "Accept": "application/json",
                    },
                    **({"json": body} if body is not None else {}),
                )
            if len(res.content) > 5_000_000:
                raise ValueError()
            data = res.json()
            if not isinstance(data, dict):
                raise ValueError()
            return res.status_code, data
        except (ValueError, httpx.HTTPError):
            raise DomainError("LETSFG_PROVIDER_UNAVAILABLE", 503) from None

    @staticmethod
    def _success(status):
        if status == 401:
            raise DomainError("LETSFG_CONNECT_REQUIRED", 409)
        if status == 429:
            raise DomainError("LETSFG_RATE_LIMIT", 429)
        if not 200 <= status < 300:
            raise DomainError("LETSFG_PROVIDER_UNAVAILABLE", 503)

    def _search_key(self, sid):
        if not isinstance(sid, str) or not SEARCH_ID.fullmatch(sid):
            raise DomainError("LETSFG_SEARCH_NOT_FOUND", 404)
        return "letsfg-search/" + fingerprint(sid)

    def _results(self, query, sid, principal, token, version, offer_id=None):
        binding = fingerprint([Conversations.owner(principal), version, query.model_dump()])
        with self.store.connection() as db:
            row = db.execute(
                "SELECT request FROM operations WHERE id=?", (self._search_key(sid),)
            ).fetchone()
        if not row or row[0] != encode({"binding": binding}):
            raise DomainError("LETSFG_SEARCH_NOT_FOUND", 404)
        status, data = self._request("GET", "results/" + quote(sid, safe=""), token)
        result = {"search_id": sid, "offers": []}
        if status in {404, 410} or data.get("status") == "expired":
            return {**result, "state": "expired", "reason": "search_expired"}
        self._success(status)
        if data.get("search_id", sid) != sid or (
            "parsed" in data and not party_matches(data["parsed"], query)
        ):
            raise DomainError("LETSFG_OFFER_UNVERIFIED", 502)
        if data.get("status") in {"searching", "running", "pending", "in_progress"} or (
            data.get("status") == "completed"
            and (data.get("gf_enrich_pending") is True or data.get("split_ticket_pending") is True)
        ):
            return {**result, "state": "searching", "reason": "supplier_search_pending"}
        if data.get("status") != "completed" or not isinstance(data.get("offers"), list):
            raise DomainError("LETSFG_OFFER_UNVERIFIED", 502)
        rows = data["offers"]
        if offer_id is not None:
            rows = [o for o in rows if isinstance(o, dict) and o.get("id") == offer_id]
        seen, raw_seen, duplicate = {}, {}, set()
        for raw in rows:
            if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
                continue
            ident = raw["id"]
            if ident in raw_seen and raw_seen[ident] != raw:
                duplicate.add(ident)
            raw_seen[ident] = raw
            offer = price_offer(raw, query, sid, version)
            if not offer:
                continue
            ident = offer["offer_id"]
            times = flight_window(offer["outbound"])
            if times and times[0] <= self.store.clock():
                continue
            seen[ident] = offer
        candidates = sorted(
            (o for k, o in seen.items() if k not in duplicate),
            key=lambda o: (not o["ready"], o["fare_minor"], o["offer_id"]),
        )[:8]
        if not candidates:
            return {
                **result,
                "state": "no_verified_offer",
                "reason": "original_offer_unavailable" if offer_id else "no_matching_itinerary",
            }
        return {**result, "state": "offers", "offers": candidates}

    def search(self, query: LiveFlightQuery, *, principal, search_id=None):
        token, version = self.auth.grant(principal)
        if search_id is not None:
            return self._results(query, search_id, principal, token, version)
        if query.departure < departure_day(self.store.clock(), query.origin).isoformat():
            raise DomainError("LETSFG_DATE_PASSED", 409)
        status, data = self._request("POST", "search", token, body=query.search_body())
        self._success(status)
        sid = data.get("search_id")
        key = self._search_key(sid)
        if not party_matches(data.get("parsed", {}), query):
            raise DomainError("LETSFG_PARTY_UNVERIFIED", 502)
        binding = fingerprint([Conversations.owner(principal), version, query.model_dump()])
        with self.store.connection(write=True) as db:
            db.execute(
                "INSERT OR IGNORE INTO operations VALUES(?,?,?)",
                (key, encode({"binding": binding}), "{}"),
            )
        return self._results(query, sid, principal, token, version)

    def reprice(self, query: LiveFlightQuery, search_id, offer_id, *, principal):
        if not isinstance(offer_id, str) or not SEARCH_ID.fullmatch(offer_id):
            raise DomainError("LETSFG_OFFER_UNVERIFIED", 422)
        token, version = self.auth.grant(principal)
        return self._results(query, search_id, principal, token, version, offer_id)

    @staticmethod
    def _order_key(handle):
        if not isinstance(handle, str) or not re.fullmatch(r"[A-Za-z0-9_./:-]{1,128}", handle):
            raise DomainError("LETSFG_BOOKING_NOT_FOUND", 404)
        return "letsfg-live-order/" + fingerprint(handle)

    def _unseal(self, row):
        return json.loads(self.auth.vault.decrypt(json.loads(row["response"])["sealed"]))

    def _envelope(self, private):
        return encode(
            {
                "state": private["public"]["state"],
                "sealed": self.auth.vault.encrypt(encode(private)),
            }
        )

    def _existing(self, db, key, request):
        old = db.execute("SELECT request,response FROM operations WHERE id=?", (key,)).fetchone()
        if old:
            if json.loads(old["request"]) != request:
                raise DomainError("LETSFG_APPROVAL_CONFLICT", 409)
            return self._unseal(old)["public"]
        return None

    def _close_unsubmitted_review(self, key, request, result):
        # A material change invalidates this approval even if the fare later
        # returns to the same amount. A conflicting in-flight submission wins.
        with self.store.connection(write=True) as db:
            if prior := self._existing(db, key, request):
                return prior
            db.execute(
                "INSERT INTO operations VALUES(?,?,?)",
                (
                    key,
                    encode(request),
                    self._envelope({"public": result}),
                ),
            )
        return result

    def submit(self, approval: LiveApprovedFare, passengers, contact_email, *, principal):
        offer, query, handle = approval.offer, approval.query, approval.approval_id
        owner = Conversations.owner(principal or {})
        token, version = self.auth.grant(principal, offer.get("account_version"))
        if (
            not offer.get("ready")
            or type(offer.get("total_minor")) is not int
            or offer["total_minor"] <= 0
            or version != offer.get("account_version")
        ):
            return record("unavailable", reason=offer.get("reason") or "offer_not_ready")
        try:
            party = passenger_body(query, passengers, contact_email)
        except (ValueError, TypeError):
            return record("missing_details", reason="traveller_details_invalid")
        key = self._order_key(handle)
        party_hash = fingerprint(party)
        passengers_on_ticket = sorted(
            tuple(
                " ".join(p[k].casefold().split()) for k in ("given_name", "family_name", "born_on")
            )
            for p in [party["passenger"], *party.get("additional_passengers", [])]
        )
        trip = fingerprint(
            [version, offer.get("outbound"), offer.get("inbound"), passengers_on_ticket]
        )
        request = {
            "owner": owner,
            "account": version,
            "offer": fingerprint(terms(offer)),
            "travellers": party_hash,
            "trip": trip,
        }
        with self.store.connection() as db:
            prior = self._existing(db, key, request)
        if prior:
            return prior
        fresh = self._results(
            query, offer.get("search_id"), principal, token, version, offer.get("offer_id")
        )
        if not fresh["offers"]:
            unavailable = record("unavailable", reason=fresh.get("reason", "offer_unavailable"))
            if fresh["state"] in {"expired", "no_verified_offer"}:
                return self._close_unsubmitted_review(key, request, unavailable)
            return unavailable
        current = fresh["offers"][0]
        if terms(current) != terms(offer):
            return self._close_unsubmitted_review(
                key,
                request,
                record(
                    "reprice" if current["ready"] else "unavailable",
                    offer=current,
                    reason=current.get("reason") or "offer_changed",
                ),
            )
        token, _ = self.auth.grant(principal, version)
        public = record("uncertain", handle, reason="check_original_booking")
        private = {"public": public}
        # Opaque legacy operation rows are excluded before any JSON predicates.
        with self.store.connection(write=True) as db:
            if prior := self._existing(db, key, request):
                return prior
            earlier = db.execute(
                "SELECT request,response FROM operations WHERE id LIKE 'letsfg-live-order/%' AND json_extract(request,'$.trip')=?",
                (trip,),
            ).fetchall()
            for candidate in earlier:
                previous = self._unseal(candidate)["public"]
                if previous["state"] in _REUSABLE:
                    earlier_request = json.loads(candidate["request"])
                    if earlier_request != request:
                        # A previous charge or PNR belongs only to its own approved fare.
                        return record(
                            "uncertain" if previous["state"] == "uncertain" else "needs_attention",
                            reason="check_original_booking_in_original_login",
                        )
                    return previous
            db.execute(
                "INSERT INTO operations VALUES(?,?,?)",
                (key, encode(request), self._envelope(private)),
            )
        # There is no published live idempotency key or client-key lookup. The durable
        # reservation above is committed before handing a card-holding request to HTTP.
        try:
            status, raw = self._request(
                "POST",
                "agent-book",
                token,
                body={
                    "search_id": offer["search_id"],
                    "offer_id": offer["offer_id"],
                    **party,
                },
            )
            remote = raw.get("booking_ref")
            if isinstance(remote, str) and re.fullmatch(r"[A-Za-z0-9_.~-]{1,8192}", remote):
                private["remote"] = remote
            if 200 <= status < 300 and private.get("remote"):
                public = read_booking(raw, offer, handle, final_read=False)
            elif (
                status in {400, 402, 409, 422}
                and raw.get("charged") is not None
                and minor_amount(raw.get("charged")) == 0
                and not private.get("remote")
            ):
                error = raw.get("error")
                if error in {"payment_method_required", "payment_declined"}:
                    public = record(
                        "card_required",
                        handle,
                        charged_minor=0,
                        currency=query.currency,
                        action_url=official_url(raw.get("add_card_url")),
                        reason=error,
                    )
                elif error == "missing_details":
                    allowed = set(LivePassenger.model_fields) | {"contact_email"}
                    fields = raw.get("missing_fields", [])
                    public = record(
                        "missing_details",
                        handle,
                        reason=error,
                        missing_fields=[f for f in fields if isinstance(f, str) and f in allowed]
                        if isinstance(fields, list)
                        else [],
                    )
                elif error in {"offer_expired", "price_changed", "price_change"}:
                    public = record("reprice", handle, reason=error)
        except DomainError:
            pass  # Receipt lost: retain the reservation, do not invoke the charge endpoint again.
        private["public"] = public
        with self.store.connection(write=True) as db:
            db.execute(
                "UPDATE operations SET response=? WHERE id=?", (self._envelope(private), key)
            )
        return public

    def status(self, booking_ref, approved_offer, *, principal):
        key = self._order_key(booking_ref)
        token, version = self.auth.grant(principal, approved_offer.get("account_version"))
        with self.store.connection() as db:
            row = db.execute(
                "SELECT request,response FROM operations WHERE id=?", (key,)
            ).fetchone()
        if not row:
            raise DomainError("LETSFG_BOOKING_NOT_FOUND", 404)
        binding = json.loads(row["request"])
        if (
            binding["owner"] != Conversations.owner(principal)
            or binding["account"] != version
            or binding["offer"] != fingerprint(terms(approved_offer))
        ):
            raise DomainError("LETSFG_BOOKING_NOT_FOUND", 404)
        private = self._unseal(row)
        if not private.get("remote"):
            return private["public"]
        status, raw = self._request(
            "POST", "agent-book/status", token, body={"booking_ref": private["remote"]}
        )
        self._success(status)
        current = read_booking(raw, approved_offer, booking_ref, final_read=True)
        if raw.get("booking_ref", private["remote"]) != private["remote"]:
            current = record("needs_attention", booking_ref, reason="booking_reference_mismatch")
        with self.store.connection(write=True) as db:
            # Concurrent polling must not overwrite a newer confirmed PNR/capture with
            # an earlier in-flight snapshot. Terminal contradictions remain reviewable.
            latest = db.execute("SELECT response FROM operations WHERE id=?", (key,)).fetchone()
            private = self._unseal(latest)
            terminal = private.get("terminal")
            if terminal and current != terminal:
                if terminal["state"] == "completed" and current["state"] in {"processing", "held"}:
                    return {**terminal, "last_verified": True}
                current = record(
                    "needs_attention", booking_ref, reason="conflicting_terminal_receipts"
                )
            if current["state"] in {"completed", "failed"}:
                private["terminal"] = current
            private["public"] = current
            db.execute(
                "UPDATE operations SET response=? WHERE id=?", (self._envelope(private), key)
            )
        return current

    def cancellation_info(self, booking_ref, approved_offer, *, principal):
        """Live flight cancellation/refunds are supplier-managed; the published stop API is sandbox-only."""
        receipt = self.status(booking_ref, approved_offer, principal=principal)
        return {
            "state": "supplier_review_required",
            "booking_state": receipt["state"],
            "reason": "consult_original_booking_and_supplier_fare_rules",
            "policy_url": "https://letsfg.co/en/terms",
        }

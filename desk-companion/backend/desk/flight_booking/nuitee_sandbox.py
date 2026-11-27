"""Nuitée's synthetic flight inventory and traveller test-card payment.

The operator supplies a sandbox profile. The client never uses the Connect account's
card, credit line, a production key, or a card number.
"""

from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import re

from cryptography.fernet import InvalidToken
import httpx

from ..store import DomainError, encode
from ..vault import Vault
from .live_fares import minor_amount
from .live_provider import terms
from .nuitee_fares import normalize

NAME = "nuitee_sandbox"
API = "https://api.liteapi.travel/v3.0"
STRIPE = "https://api.stripe.com/v1"
ID = re.compile(r"[A-Za-z0-9_-]{1,160}")

# Official prebook OpenAPI passenger example. Only this fixture is sent from sandbox mode.
PASSENGER = {
    "firstName": "John",
    "lastName": "Doe",
    "middleName": "Joshua",
    "passengerType": 0,
    "birthday": "1996-04-28",
    "gender": "M",
    "nationality": "US",
    "documentType": "passport",
    "documentNumber": "123456789",
    "documentIssueCountry": "US",
    "documentExpiry": "2030-04-28",
}
CONTACT = {
    "firstName": "John",
    "lastName": "Doe",
    "middleName": "Joshua",
    "email": "j.doe@example.com",
    "phoneCountryCode": "1",
    "phoneNumber": "2025550147",
}


def valid_keys(data):
    return isinstance(data, dict) and all(
        isinstance(data.get(k), str) and re.fullmatch(pattern, data[k])
        for k, pattern in (
            ("private", r"sand_[A-Za-z0-9_-]{16,256}"),
            ("public", r"pk_test_[A-Za-z0-9_-]{12,256}"),
        )
    )


def credentials(directory):
    if not directory:
        return None
    p = Path(directory)
    try:
        if not p.is_absolute() or p.resolve() != p or not p.is_dir():
            return None
        for f in (p, p / "vault.key", p / "account.sealed"):
            st = f.stat()
            if f.is_symlink() or st.st_uid != os.getuid() or st.st_mode & 0o077:
                return None
        data = json.loads(Vault(p).decrypt((p / "account.sealed").read_text()))
        if valid_keys(data):
            return data
    except (OSError, TypeError, ValueError, KeyError, InvalidToken):
        pass
    return None


def _first(envelope):
    rows = envelope.get("data")
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise DomainError("FLIGHT_SUPPLIER_RECEIPT_UNVERIFIED", 502)
    return rows[0]


def _id(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise DomainError("FLIGHT_SUPPLIER_RECEIPT_UNVERIFIED", 502)
    return value


class RevisedSandboxFare(DomainError):
    def __init__(self, offer):
        super().__init__("FLIGHT_NUITEE_TERMS_CHANGED", 409)
        self.offer = offer


def order_reference(booking):
    order = booking.get("order") or {}
    reference = order.get("reference") if isinstance(order, dict) else None
    return _id(reference.get("orderId") if isinstance(reference, dict) else None)


class NuiteeSandbox:
    def __init__(self, runtime, directory=None, transport=None):
        self.store = runtime.store
        self.keys = credentials(directory or os.getenv("DESK_NUITEE_SANDBOX_PROFILE"))
        self.transport = transport

    def account(self):
        if not self.keys:
            return {"connected": False}
        return {
            "connected": True,
            "version": hashlib.sha256(self.keys["private"].encode()).hexdigest(),
        }

    def require_account(self, version=None):
        current = self.account().get("version")
        if not current or (version is not None and version != current):
            raise DomainError("FLIGHT_NUITEE_SANDBOX_DISCONNECTED", 409)
        return current

    def _request(self, method, path, body=None, *, intent_secret=None):
        self.require_account()
        if intent_secret is None:
            url = API + path
            headers = {"X-API-Key": self.keys["private"]}
            params = None
        else:
            url = STRIPE + path
            headers = {"Authorization": "Bearer " + self.keys["public"]}
            params = {"client_secret": intent_secret}
        # A transport-level request also avoids logging Stripe's client secret in an HTTP URL.
        req = httpx.Request(
            method,
            url,
            headers=headers,
            params=params,
            json=body,
            extensions={"timeout": dict.fromkeys(("connect", "read", "write", "pool"), 35.0)},
        )
        try:
            cm = (
                nullcontext(self.transport) if self.transport is not None else httpx.HTTPTransport()
            )
            with cm as http:
                response = http.handle_request(req)
                try:
                    if not 200 <= response.status_code < 300:
                        if response.status_code in (401, 403):
                            raise DomainError("FLIGHT_NUITEE_AUTH_REQUIRED", 403)
                        if response.status_code in (404, 410):
                            raise DomainError("FLIGHT_NUITEE_RECORD_EXPIRED", 409)
                        raise DomainError("FLIGHT_NUITEE_REQUEST_FAILED", 502)
                    buf = bytearray()
                    for block in response.iter_bytes():
                        if len(buf) + len(block) > 24_000_000:
                            raise DomainError("FLIGHT_SUPPLIER_RECEIPT_UNVERIFIED", 502)
                        buf.extend(block)
                    parsed = json.loads(buf)
                finally:
                    response.close()
        except (httpx.HTTPError, ValueError):
            raise DomainError("FLIGHT_NUITEE_REQUEST_FAILED", 502) from None
        if not isinstance(parsed, dict):
            raise DomainError("FLIGHT_SUPPLIER_RECEIPT_UNVERIFIED", 502)
        return parsed

    def search(self, query, *, principal, search_id=None):
        version = self.require_account()
        if query.adults != 1 or query.children or query.infants:
            raise DomainError("FLIGHT_NUITEE_TEST_PARTY", 422)
        legs = [{"origin": query.origin, "destination": query.destination, "date": query.departure}]
        if query.return_date:
            legs.append(
                {
                    "origin": query.destination,
                    "destination": query.origin,
                    "date": query.return_date,
                    "direction": "INBOUND",
                }
            )
        data = _first(
            self._request(
                "POST",
                "/flights/rates",
                {
                    "legs": legs,
                    "adults": 1,
                    "currency": query.currency,
                    "country": "HK",
                },
            )
        )
        sid = _id(data.get("searchId"))
        result = []
        for journey in data.get("journeys") or []:
            if not isinstance(journey, dict):
                continue
            for raw in journey.get("offers") or []:
                if not isinstance(raw, dict) or raw.get("searchId") != sid:
                    continue
                oid = raw.get("offerId")
                if not isinstance(oid, str) or not 1 <= len(oid) <= 8192:
                    continue
                offer = normalize(journey, raw, query, sid, oid, version, self.store.clock())
                if offer:
                    result.append(offer)
        result.sort(key=lambda o: (not o["ready"], o["fare_minor"]))
        return {
            "state": "offers" if result else "no_verified_offer",
            "offers": result[:8],
            "search_id": sid,
        }

    def reprice(self, query, search_id, offer_id, *, principal):
        version = self.require_account()
        data = _first(self._request("POST", "/flights/verify", {"offerId": offer_id}))
        journey = data.get("journey")
        if data.get("searchId") != search_id or not isinstance(journey, dict):
            return {"state": "unavailable", "offers": []}
        offer = normalize(journey, journey, query, search_id, offer_id, version, self.store.clock())
        return {"state": "offers" if offer else "unavailable", "offers": [offer] if offer else []}

    def prebook(self, query, offer):
        self.require_account(offer["account_version"])
        data = _first(
            self._request(
                "POST",
                "/flights/prebooks",
                {
                    "offerId": offer["offer_id"],
                    "contact": CONTACT,
                    "passengers": [PASSENGER],
                    "usePaymentSdk": True,
                },
            )
        )
        expiration = self._check_prebook(data, query, offer)
        client_secret = data.get("secretKey", "")
        if not isinstance(client_secret, str) or not re.fullmatch(
            r"pi_[A-Za-z0-9]+_secret_[A-Za-z0-9]+", client_secret
        ):
            raise DomainError("FLIGHT_SUPPLIER_RECEIPT_UNVERIFIED", 502)
        session = {
            "prebook": _id(data.get("prebookId")),
            "transaction": _id(data.get("transactionId")),
            "secret": client_secret,
            "expires": expiration,
            "account": offer["account_version"],
            "order_reference": order_reference(data["booking"]),
        }
        intent = self.intent(session, offer)
        if intent.get("status") != "requires_payment_method":
            raise DomainError("FLIGHT_SUPPLIER_RECEIPT_UNVERIFIED", 502)
        return session

    def _check_prebook(self, data, query, offer):
        journey = dict((data.get("booking") or {}).get("journey") or {})
        expiration = (data.get("servicesAttachable") or {}).get("expiresAt") or offer["expires_at"]
        journey.setdefault("expiration", expiration)
        snapshot = normalize(
            journey,
            journey,
            query,
            offer["search_id"],
            offer["offer_id"],
            offer["account_version"],
            self.store.clock(),
        )
        if (
            not snapshot
            or data.get("searchId") != offer["search_id"]
            or minor_amount(data.get("price")) != snapshot["fare_minor"]
            or data.get("currency") != offer["currency"]
        ):
            raise DomainError("FLIGHT_SUPPLIER_RECEIPT_UNVERIFIED", 502)
        if terms(snapshot) != terms(offer):
            raise RevisedSandboxFare(snapshot)
        if "TRANSACTION_ID" not in (data.get("paymentTypes") or []):
            raise DomainError("FLIGHT_NUITEE_TRAVELLER_CARD_UNAVAILABLE", 409)
        return expiration

    def check_session(self, session, query, offer):
        self.require_account(session["account"])
        data = _first(self._request("GET", "/flights/prebooks/" + _id(session["prebook"])))
        if (
            data.get("prebookId") != session["prebook"]
            or data.get("transactionId") != session["transaction"]
            or data.get("secretKey") != session["secret"]
            or order_reference(data.get("booking") or {}) != session["order_reference"]
        ):
            raise DomainError("FLIGHT_SUPPLIER_RECEIPT_UNVERIFIED", 502)
        self._check_prebook(data, query, offer)

    def intent(self, session, offer):
        self.require_account(session["account"])
        ref = session["secret"].partition("_secret_")[0]
        data = self._request("GET", "/payment_intents/" + _id(ref), intent_secret=session["secret"])
        if (
            data.get("livemode") is not False
            or data.get("id") != ref
            or type(data.get("amount")) is not int
            or data["amount"] != offer["total_minor"]
            or data.get("currency") != offer["currency"].lower()
        ):
            raise DomainError("FLIGHT_SUPPLIER_RECEIPT_UNVERIFIED", 502)
        return data

    def book(self, session):
        self.require_account(session["account"])
        raw = _first(
            self._request(
                "POST",
                "/flights/bookings/",
                {
                    "prebookId": session["prebook"],
                    "payment": {
                        "method": "TRANSACTION_ID",
                        "transactionId": session["transaction"],
                    },
                },
            )
        )
        # An idempotent replay may put the existing booking ID on the enclosing row.
        return _id((raw.get("booking") or raw).get("bookingId"))

    def booking(self, session):
        self.require_account(session["account"])
        data = _first(self._request("GET", "/flights/bookings/" + _id(session["booking_id"])))
        book = data.get("booking")
        if not isinstance(book, dict) or book.get("bookingId") != session["booking_id"]:
            raise DomainError("FLIGHT_SUPPLIER_RECEIPT_UNVERIFIED", 502)
        return book

    def seal(self, value):
        return Vault(self.store.directory).encrypt(encode(value))

    def unseal(self, value):
        return json.loads(Vault(self.store.directory).decrypt(value))

"""LetsFG sandbox transport. Only the published anonymous test namespace is reachable."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
import logging

import httpx
from pydantic import Field, model_validator

from ..commerce_quotes import Airport, Day
from ..schemas import StrictModel
from ..store import DomainError


BASE = "https://letsfg.co/developers/api/v1/sandbox/flights/"
BOOKING_ID = re.compile(r"sb_dev_[A-Za-z0-9_-]{1,96}")
PNR = re.compile(r"[A-Z0-9]{6}")


class FlightQuery(StrictModel):
    origin: Airport
    destination: Airport
    departure: Day
    adults: int = Field(default=1, ge=1, le=9, strict=True)
    flight_number: str | None = Field(default=None, pattern=r"^[A-Z0-9]{2}\s?[0-9]{1,4}[A-Z]?$")
    airline: str | None = Field(default=None, pattern=r"^[A-Z0-9]{2}$")
    nonstop: bool = False
    rehearse_price_change: bool = Field(
        default=False,
        description="True only when the owner explicitly requests a price-rise test scenario.",
    )
    max_hkd: float | None = Field(default=None, gt=0, le=1000000)
    checked_bag_kg: int = Field(default=0, ge=0, le=60)
    return_date: Day | None = None

    @model_validator(mode="after")
    def different_airports(self):
        if self.origin == self.destination:
            raise ValueError("Choose different airports")
        return self


def minor(value):
    try:
        amount = Decimal(str(value)) * 100
        if (
            not amount.is_finite()
            or not 0 <= amount <= 100_000_000
            or amount != amount.to_integral_value()
        ):
            raise ValueError
        return int(amount)
    except (InvalidOperation, ValueError, TypeError):
        raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502) from None


def booking_id(value):
    if not isinstance(value, str) or not BOOKING_ID.fullmatch(value):
        raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)
    return value


def _selected(offer, search_id, query):
    if offer.get("source_tier") != "sandbox" or offer.get("currency") != "HKD":
        return None
    ident = offer.get("id")
    if not isinstance(ident, str) or not re.fullmatch(r"sb_[A-Za-z0-9_-]{1,145}", ident):
        return None
    legs = (offer.get("outbound") or {}).get("segments") or []
    if not 1 <= len(legs) <= 6 or offer.get("inbound") or offer.get("availability_seats", 0) < 1:
        return None
    if legs[0]["origin"] != query.origin or legs[-1]["destination"] != query.destination:
        return None
    segments = []
    for leg in legs:
        depart, arrive = (datetime.fromisoformat(leg[k]) for k in ("departure", "arrival"))
        if (
            not re.fullmatch(r"[A-Z0-9]{2}[0-9]{1,4}[A-Z]?", leg["flight_no"])
            or not all(re.fullmatch(r"[A-Z]{3}", leg[k]) for k in ("origin", "destination"))
            or (segments and segments[-1]["destination"] != leg["origin"])
        ):
            return None
        segments.append(
            {
                "flight": leg["flight_no"],
                "origin": leg["origin"],
                "destination": leg["destination"],
                "departs": depart.isoformat(timespec="minutes"),
                "arrives": arrive.isoformat(timespec="minutes"),
            }
        )
    if (
        segments[0]["departs"][:10] != query.departure
        or (query.nonstop and len(legs) != 1)
        or (
            query.flight_number
            and (len(legs) != 1 or segments[0]["flight"] != query.flight_number.replace(" ", ""))
        )
        or (query.airline and any(leg["airline"] != query.airline for leg in legs))
    ):
        return None
    price = minor(offer["price"])
    if price <= 0 or (query.max_hkd is not None and price > minor(query.max_hkd)):
        return None
    return {
        "search_id": search_id,
        "offer_id": ident,
        "segments": segments,
        "total_minor": price,
        "currency": "HKD",
        "adults": 1,
    }


class LetsFG:
    def __init__(self, transport=None):
        self.transport = transport

    def request(self, method, path, body=None):
        try:
            with httpx.Client(
                base_url=BASE,
                timeout=httpx.Timeout(5.0, connect=3.0) if path == "search" else 10,
                trust_env=False,
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                response = client.request(
                    method, path, **({"json": body} if body is not None else {})
                )
                result = response.json()
        except (httpx.HTTPError, ValueError) as error:
            logging.getLogger(__name__).warning(
                "LetsFG sandbox %s failed: %s", method, type(error).__name__
            )
            raise DomainError("FLIGHT_PROVIDER_UNAVAILABLE", 503) from None
        if not isinstance(result, dict) or response.status_code >= 500:
            logging.getLogger(__name__).warning(
                "LetsFG sandbox %s: HTTP %s", method, response.status_code
            )
            raise DomainError("FLIGHT_PROVIDER_UNAVAILABLE", 503)
        if response.status_code not in (200, 202):
            raise DomainError("FLIGHT_PROVIDER_REFUSED", 409)
        return result

    def quote(self, query, today: date):
        if query.adults != 1 or query.checked_bag_kg or query.return_date:
            raise DomainError("FLIGHT_TEST_SCOPE", 422)
        if date.fromisoformat(query.departure) < today:
            raise DomainError("FLIGHT_PAST_DATE", 422)
        body = {
            "origin": query.origin,
            "destination": query.destination,
            "date_from": query.departure,
            "adults": 1,
            "currency": "HKD",
        }
        try:
            data = self.request("POST", "search", body)
        except DomainError as error:
            if error.code != "FLIGHT_PROVIDER_UNAVAILABLE":
                raise
            # A fare query has no order effect. Recover one transient read failure.
            data = self.request("POST", "search", body)
        sid = data.get("search_id")
        if (
            not isinstance(sid, str)
            or not re.fullmatch(r"sb_[A-Za-z0-9_-]{1,145}", sid)
            or data.get("origin") != query.origin
            or data.get("destination") != query.destination
            or data.get("currency") != "HKD"
            or not isinstance(data.get("offers"), list)
        ):
            raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)
        eligible = []
        for offer in data["offers"][:100]:
            try:
                selected = _selected(offer, sid, query)
            except (KeyError, TypeError, ValueError, AttributeError, DomainError):
                continue
            if selected:
                eligible.append(selected)
        if not eligible:
            raise DomainError("FLIGHT_NO_MATCH", 404)
        return min(eligible, key=lambda row: row["total_minor"])

    def submit(self, quote, key, scenario):
        # A single fictional adult. No user identity, wallet or card input enters this protocol.
        passenger = {
            "given_name": "Alice",
            "family_name": "Example",
            "born_on": "1990-01-15",
            "gender": "f",
            "email": "traveller@example.com",
            "phone_number": "+12025550123",
            "phone_country": "US",
            "nationality": "US",
            "address_line1": "100 Example Street",
            "address_city": "Washington",
            "address_postal": "20001",
            "address_country": "US",
            "passport_number": "999000001",
            "passport_country": "US",
            "passport_issue": "2021-05-01",
            "passport_expiry": "2031-05-01",
        }
        return self.request(
            "POST",
            "book",
            {
                "search_id": quote["search_id"],
                "offer_id": quote["offer_id"],
                "idempotency_key": key,
                "contact_email": passenger["email"],
                "passengers": [passenger],
                "want_seat": False,
                "sandbox": {
                    "scenario": scenario,
                    "speed": "realistic" if scenario == "price_change" else "fast",
                },
            },
        )

    def status(self, ident):
        return self.request("GET", "bookings/" + booking_id(ident))

    def stop(self, ident):
        return self.request("POST", "bookings/" + booking_id(ident) + "/stop", {})

    def answer(self, ident, round_number, agree):
        return self.request(
            "POST",
            "bookings/" + booking_id(ident) + "/answer",
            {"round": round_number, ("confirm" if agree else "skip"): True},
        )


def matched(record, ident, quote):
    if (
        record.get("sandbox") is not True
        or record.get("booking_id") != ident
        or not isinstance(record.get("offer"), dict)
        or any(record["offer"].get(k) != quote[k] for k in ("search_id", "offer_id"))
    ):
        raise DomainError("FLIGHT_RECEIPT_MISMATCH", 502)

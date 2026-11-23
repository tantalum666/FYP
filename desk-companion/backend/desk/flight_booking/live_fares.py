"""Commercial evidence from the public-agent offer, using airport-local dates and party prices."""

from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Annotated, Literal
from urllib.parse import unquote, urlsplit

from pydantic import Field, field_validator, model_validator

from ..commerce_quotes import Airport, Day
from ..schemas import StrictModel
from .timetable import flight_window, published_time

Country = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
Label = Annotated[str, Field(min_length=1, max_length=140)]
SEARCH_ID = re.compile(r"[A-Za-z0-9_-]{1,160}")
FLIGHT_ID = re.compile(r"[A-Z0-9]{2}[0-9]{1,4}[A-Z]?")


class LiveFlightQuery(StrictModel):
    origin: Airport
    destination: Airport
    departure: Day
    return_date: Day | None = None
    adults: int = Field(default=1, strict=True, ge=1, le=9)
    children: int = Field(default=0, strict=True, ge=0, le=8)
    infants: int = Field(default=0, strict=True, ge=0, le=8)
    currency: Literal["HKD"] = "HKD"
    checked_bags: int = Field(default=0, strict=True, ge=0, le=4)
    checked_bag_kg: int | None = Field(default=None, strict=True, ge=1, le=60)
    carrier: str | None = Field(default=None, pattern=r"^[A-Z0-9]{2}$")
    flight_number: str | None = Field(default=None, pattern=r"^[A-Z0-9]{2}[0-9]{1,4}[A-Z]?$")
    outbound_flights: list[Annotated[str, Field(pattern=r"^[A-Z0-9]{2}[0-9]{1,4}[A-Z]?$")]] = Field(
        default_factory=list, max_length=7
    )
    inbound_flights: list[Annotated[str, Field(pattern=r"^[A-Z0-9]{2}[0-9]{1,4}[A-Z]?$")]] = Field(
        default_factory=list, max_length=7
    )
    outbound_departs_at: str | None = Field(
        default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$"
    )
    outbound_arrives_at: str | None = Field(
        default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$"
    )
    inbound_departs_at: str | None = Field(
        default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$"
    )
    inbound_arrives_at: str | None = Field(
        default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$"
    )
    nonstop: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def valid_trip(self):
        if self.origin == self.destination or (
            self.return_date and self.return_date < self.departure
        ):
            raise ValueError("Choose distinct airports and chronological travel dates")
        if not self.return_date and (
            self.inbound_flights or self.inbound_departs_at or self.inbound_arrives_at
        ):
            raise ValueError("Inbound constraints require a return date")
        if self.infants > self.adults or self.adults + self.children + self.infants > 9:
            raise ValueError("Invalid travelling party")
        if self.checked_bag_kg and not self.checked_bags:
            self.checked_bags = 1
        return self

    def search_body(self):
        body = self.model_dump(
            include={
                "origin",
                "destination",
                "return_date",
                "adults",
                "children",
                "infants",
                "currency",
            },
            exclude_none=True,
        )
        body["date_from"] = self.departure
        if self.nonstop:
            body["max_stops"] = 0
        return body


class LiveApprovedFare(StrictModel):
    approval_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_./:-]+$")
    query: LiveFlightQuery
    offer: dict


class LivePassenger(StrictModel):
    given_name: Label
    family_name: Label
    born_on: Day
    gender: Literal["m", "f"]
    nationality: Country
    phone_number: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{6,14}$")
    phone_country: Country | None = None
    address_line1: Label | None = None
    address_city: Label | None = None
    address_postal: Label | None = None
    address_country: Country | None = None
    passport_number: str | None = Field(default=None, pattern=r"^[A-Za-z0-9 -]{3,40}$")
    passport_country: Country | None = None
    passport_expiry: Day | None = None
    passport_issue: Day | None = None

    @field_validator("given_name", "family_name", "address_line1", "address_city", "address_postal")
    @classmethod
    def plain_text(cls, value):
        if value is not None and (not value.strip() or not value.isprintable()):
            raise ValueError("Invalid traveller field")
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def complete_passport(self):
        values = (
            self.passport_number,
            self.passport_country,
            self.passport_expiry,
            self.passport_issue,
        )
        if any(values) and (not all(values) or self.passport_issue >= self.passport_expiry):
            raise ValueError("Complete all four passport fields or omit the passport")
        return self


def passenger_body(query, passengers, email):
    if (
        not isinstance(email, str)
        or len(email) > 254
        or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", email)
    ):
        raise ValueError("A valid traveller contact email is required")
    group = [
        p if isinstance(p, LivePassenger) else LivePassenger.model_validate(p) for p in passengers
    ]
    if not group or any(
        not getattr(group[0], k)
        for k in (
            "phone_number",
            "phone_country",
            "address_line1",
            "address_city",
            "address_postal",
            "address_country",
        )
    ):
        raise ValueError("Complete the lead traveller's contact and address fields")
    end = date.fromisoformat(query.return_date or query.departure)
    start = date.fromisoformat(query.departure)
    counts = [0, 0, 0]
    for person in group:
        birth = date.fromisoformat(person.born_on)
        if birth > start or (person.passport_expiry and person.passport_expiry < end.isoformat()):
            raise ValueError("Traveller dates do not cover the itinerary")
        age = end.year - birth.year - ((end.month, end.day) < (birth.month, birth.day))
        cat = 0 if age >= 12 else 1 if age >= 2 else 2
        if person is group[0] and cat != 0:
            raise ValueError("An adult must be the lead traveller")
        counts[cat] += 1
    if counts != [query.adults, query.children, query.infants]:
        raise ValueError("Traveller count or ages do not match the reviewed party")
    lead = group[0].model_dump(exclude_none=True)
    others = [
        p.model_dump(
            exclude_none=True,
            exclude={
                "phone_number",
                "phone_country",
                "address_line1",
                "address_city",
                "address_postal",
                "address_country",
            },
        )
        for p in group[1:]
    ]
    return {
        "contact_email": email,
        "passenger": lead,
        **({"additional_passengers": others} if others else {}),
    }


def minor_amount(value):
    if isinstance(value, bool):
        return None
    try:
        n = Decimal(str(value)) * 100
        return int(n) if n.is_finite() and 0 <= n <= 10**10 and n == n.to_integral_value() else None
    except (ValueError, InvalidOperation):
        return None


def official_url(value):
    if (
        not isinstance(value, str)
        or len(value) > 4096
        or any(ord(c) <= 32 or c == "\\" for c in unquote(value))
    ):
        return None
    try:
        p = urlsplit(value)
        if (
            p.scheme != "https"
            or p.netloc != "letsfg.co"
            or p.fragment
            or not p.path.startswith("/")
            or p.path.startswith("//")
        ):
            return None
        # Never forward a generic redirector or delegate an unvalidated external destination.
        from urllib.parse import parse_qsl

        if any(
            k.lower()
            in {"url", "redirect", "redirect_uri", "return_url", "next", "continue", "target"}
            or re.search(r"(?:https?:|//|\\)", unquote(v), re.I)
            for k, v in parse_qsl(p.query)
        ):
            return None
        return value
    except ValueError:
        return None


def party_matches(parsed, query):
    if not isinstance(parsed, dict):
        return False
    for key, want in (
        ("adults", query.adults),
        ("children", query.children),
        ("infants", query.infants),
        ("passengers", query.adults + query.children),
    ):
        if key in parsed and (type(parsed[key]) is not int or parsed[key] != want):
            return False
    if query.adults + query.children + query.infants > 1 and not all(
        k in parsed
        for k, n in (
            ("adults", query.adults),
            ("children", query.children),
            ("infants", query.infants),
        )
        if n
    ):
        return False
    for key, want in (
        ("origin", query.origin),
        ("destination", query.destination),
        ("date_from", query.departure),
        ("return_date", query.return_date),
    ):
        if key in parsed and parsed[key] != want:
            return False
    return True


def direction(raw, origin, destination, departure, query):
    if not isinstance(raw, dict):
        raise ValueError()
    segments = raw.get("segments") or []
    stops = raw.get("stops")
    if type(stops) is not int or stops < 0 or stops > 6:
        raise ValueError()
    if not segments and stops == 0:
        segments = [raw]
    if not isinstance(segments, list) or len(segments) != stops + 1 or (query.nonstop and stops):
        raise ValueError()
    out = []
    for item in segments:
        if not isinstance(item, dict):
            raise ValueError()
        frm, to = item.get("origin"), item.get("destination")
        d, a = item.get("departure_time"), item.get("arrival_time")
        carrier = item.get("airline_code")
        flight = re.sub(r"\s+", "", str(item.get("flight_number") or "")).upper()
        if (
            not all(isinstance(i, str) for i in (frm, to, d, a, carrier))
            or not re.fullmatch(r"[A-Z]{3}", frm)
            or not re.fullmatch(r"[A-Z]{3}", to)
            or not re.fullmatch(r"[A-Z0-9]{2}", carrier)
        ):
            raise ValueError()
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", d) or not re.match(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", a
        ):
            raise ValueError()
        d, a = published_time(d, frm), published_time(a, to)
        if flight.isdigit():
            flight = carrier + flight
        if (flight and not FLIGHT_ID.fullmatch(flight)) or (
            query.carrier and query.carrier != carrier
        ):
            raise ValueError()
        if out and out[-1]["destination"] != frm:
            raise ValueError()
        out.append(
            {
                "origin": frm,
                "destination": to,
                "departs": d,
                "arrives": a,
                "carrier": carrier,
                "flight": flight or None,
            }
        )
    if (
        out[0]["origin"] != origin
        or out[-1]["destination"] != destination
        or out[0]["departs"][:10] != departure
    ):
        raise ValueError()
    return out


_ALLOWANCE = re.compile(
    r"(\d{1,2}) checked bags? (?:of|up to) (\d{1,2})\s*kg(?: each)? (per passenger|for the (?:whole|entire) party) included (?:on|for) all (?:flights|segments)",
    re.I,
)


def price_offer(raw, query, search_id, version):
    """The published PFS fare is per seat for the whole trip. A bags_price map has no weight guarantee."""
    ident = raw.get("id") if isinstance(raw, dict) else None
    if (
        not isinstance(ident, str)
        or not SEARCH_ID.fullmatch(ident)
        or raw.get("currency") != query.currency
    ):
        return None
    price = minor_amount(raw.get("price"))
    if not price:
        return None
    try:
        out = direction(raw, query.origin, query.destination, query.departure, query)
        inbound = (
            direction(raw.get("inbound"), query.destination, query.origin, query.return_date, query)
            if query.return_date
            else []
        )
        if (not query.return_date and raw.get("inbound")) or (
            query.flight_number and out[0]["flight"] != query.flight_number
        ):
            return None
        for legs, flights, departure_at, arrival_at in [
            (out, query.outbound_flights, query.outbound_departs_at, query.outbound_arrives_at),
            (inbound, query.inbound_flights, query.inbound_departs_at, query.inbound_arrives_at),
        ]:
            if flights and [segment["flight"] for segment in legs] != flights:
                return None
            if departure_at and legs[0]["departs"][11:16] != departure_at:
                return None
            if arrival_at and legs[-1]["arrives"][11:16] != arrival_at:
                return None
    except (TypeError, ValueError, IndexError, KeyError):
        return None
    seats = query.adults + query.children
    reason, bag_count, kg, evidence = None, None, None, None
    outbound_window = flight_window(out)
    inbound_window = flight_window(inbound) if inbound else None
    if not outbound_window or (
        inbound and (not inbound_window or inbound_window[0] < outbound_window[1])
    ):
        reason = "itinerary_times_unverified"
    if any(not s["flight"] for s in out + inbound):
        reason = "flight_number_unverified"
    breakdown = raw.get("trip_breakdown") or []
    if not isinstance(breakdown, list) or any(not isinstance(t, dict) for t in breakdown):
        return None
    if any(str(t.get("leg", "")) not in {"outbound", "inbound"} for t in breakdown) or len(
        breakdown
    ) > (2 if inbound else 1):
        reason = "separate_tickets_need_review"
    conditions = raw.get("conditions")
    rules = conditions.get("baggage") if isinstance(conditions, dict) else None
    # Only the supplier's own unqualified whole-itinerary inclusion statement can
    # establish weight, per-passenger coverage and no extra fee at the same time.
    verified_rules = raw.get("conditions_source") in {"airline", "supplier", "provider"}
    match = (
        _ALLOWANCE.fullmatch(rules.strip().rstrip("."))
        if verified_rules and isinstance(rules, str)
        else None
    )
    fare_conditions = {
        k: conditions[k]
        for k in ("refundable", "changeable")
        if isinstance(conditions, dict)
        and isinstance(conditions.get(k), str)
        and len(conditions[k]) <= 240
    }
    if match:
        pieces, weight, coverage = match.groups()
        bag_count = int(pieces) * (seats if coverage.casefold() == "per passenger" else 1)
        kg = int(weight)
        evidence = rules
    if query.checked_bags and (
        not match
        or bag_count < query.checked_bags
        or (query.checked_bag_kg and kg < query.checked_bag_kg)
    ):
        reason = "checked_baggage_unverified"
    return {
        "search_id": search_id,
        "offer_id": ident,
        "account_version": version,
        "currency": query.currency,
        "fare_minor": price * seats,
        "total_minor": None if reason == "checked_baggage_unverified" else price * seats,
        "passenger_count": seats + query.infants,
        "outbound": out,
        "inbound": inbound,
        "checked_bags": bag_count,
        "checked_bag_kg": kg,
        "baggage_evidence": evidence,
        "fare_conditions": fare_conditions,
        "conditions_source": raw.get("conditions_source")
        if raw.get("conditions_source") in {"airline", "supplier", "provider", "estimate"}
        else None,
        "booking_url": official_url(raw.get("booking_url")),
        "next_action": "confirm_allowance_and_all_in_fare_with_original_supplier"
        if reason == "checked_baggage_unverified"
        else None,
        "ready": reason is None,
        "reason": reason,
    }

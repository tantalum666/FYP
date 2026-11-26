"""Expand an owner's airport choices into exact, read-only LetsFG searches."""

from datetime import datetime, timedelta
from itertools import product
import re
from typing import Annotated

from pydantic import BeforeValidator, Field, model_validator

from ..calendar import iso
from ..commerce_quotes import Airport, Day
from ..schemas import StrictModel
from ..store import DomainError
from .live_fares import LiveFlightQuery
from .provider import FlightNumber, HKDLimit, minor

_SEPARATOR = r"\s*(?:/|,|，|、|\bor\b|\band\b|或|和)\s*"
_CODES = r"[A-Za-z]{3}(?:" + _SEPARATOR + r"[A-Za-z]{3})*"
SEARCH_WINDOW = timedelta(minutes=3)
_TEST = re.compile(
    r"沙盒|(?:测试|測試|模拟|模擬)(?:航班|机票|機票|订票|訂票|单|單|环境|環境)|\b(?:sandbox|rehearsal|fictional flight|test (?:flight|booking|ticket|mode))\b",
    re.I,
)
_REAL = re.compile(
    r"真实|真實|实单|實單|(?:不要|不用|别用|別用)(?:\s*(?:Nuit[ée]e|LetsFG)\s*|.{0,3})(?:测试|測試|沙盒|sandbox)|\b(?:real|live) (?:flight|fare|booking)|\bnot (?:a )?(?:test|sandbox)",
    re.I,
)
_FLIGHT = re.compile(r"机票|機票|航班|机场|機場|\b(?:flights?|airports?|airfare|tickets?)\b", re.I)
_EITHER = re.compile(
    r"(?:两个|兩個|两个机场|兩個機場|这两个|這兩個|两边|兩邊)?(?:都行|都可以|没偏好|沒偏好|都查)|(?:either|both)(?: airports?)?(?: (?:is fine|are fine|works?|work for me))?",
    re.I,
)


def explicit_test(message, chat):
    if _REAL.search(message):
        return False
    if _TEST.search(message):
        return True
    if _FLIGHT.search(message):
        return False
    for item in reversed(getattr(chat, "items", ())):
        text = item.get("text", "")
        if item.get("role") == "user" and _FLIGHT.search(text):
            return bool(_TEST.search(text))
    return False


def nuitee_test_requested(message, chat):
    """A test account must never substitute for a real travel request."""
    for text in [message, *(item.get("text", "") for item in reversed(getattr(chat, "items", ())) if item.get("role") == "user")]:
        if _REAL.search(text):
            return False
        if re.search(r"(?<![A-Za-z])nuit[ée]e(?![A-Za-z])", text, re.I) and _TEST.search(text):
            return True
        if _FLIGHT.search(text) or _TEST.search(text):
            return False
    return False


def accepted_airports(arguments, message, chat):
    """Keep both explicitly offered airports if the model narrowed an either/or answer."""
    if not _EITHER.fullmatch(message.strip().strip("。.!！")):
        return arguments
    previous = next(
        (i["text"] for i in reversed(getattr(chat, "items", ())) if i.get("role") == "assistant"),
        "",
    )
    question = re.split(r"[。.!！\n]", previous.strip())[-1].strip()
    if not question.endswith(("?", "？")):
        return arguments
    named = list(re.finditer(r"[(（]([A-Z]{3})[)）]", question))
    if len(named) == 2 and re.search(
        r"还是|還是|或者|或|\bor\b|/", question[named[0].end() : named[1].start()], re.I
    ):
        codes = [m[1] for m in named]
    else:
        pair = re.search(
            r"(?<![A-Z])([A-Z]{3})\s*(?:还是|還是|或|or|/)\s*([A-Z]{3})(?![A-Z])", question
        )
        codes = list(pair.groups()) if pair else []
    if len(set(codes)) != 2:
        return arguments
    sides = [side for side in ("origin", "destination") if set(arguments[side]) & set(codes)]
    if len(sides) == 1 and set(arguments[sides[0]]) <= set(codes):
        other = "origin" if sides[0] == "destination" else "destination"
        if len(arguments[other]) * len(codes) > 4:
            raise DomainError("FLIGHT_DIFFERENT_SEARCH_TERMS", 422)
        return {**arguments, sides[0]: codes}
    return arguments


def airport_codes(value):
    # Older function calls sometimes put the display label around the IATA list.
    # Parse a full code list, never guess codes from place names or arbitrary prose.
    if isinstance(value, str):
        label = re.fullmatch(r"[^()（）]{1,80}\s*[(（]([^()（）]+)[)）]", value.strip())
        codes = label[1] if label else value.strip()
        if re.fullmatch(_CODES, codes, re.I):
            value = re.split(_SEPARATOR, codes, flags=re.I)
    if isinstance(value, list) and all(isinstance(s, str) for s in value):
        return list(dict.fromkeys(s.strip().upper() for s in value))
    return value


Airports = Annotated[
    list[Airport], Field(min_length=1, max_length=4), BeforeValidator(airport_codes)
]


class MarketFlightRequest(StrictModel):
    origin: Airports = Field(description="All accepted departure airport IATA codes as an array.")
    destination: Airports = Field(
        description="All accepted arrival airport IATA codes as an array. For either of two airports include BOTH codes, never a city label."
    )
    departure: Day
    return_date: Day | None = None
    adults: int = Field(default=1, ge=1, le=9, strict=True)
    checked_bag_kg: int = Field(
        default=0,
        ge=0,
        le=60,
        strict=True,
        description="Required checked baggage per adult in kilograms.",
    )
    nonstop: bool = Field(default=False, strict=True)
    flight_number: FlightNumber | None = None
    airline: str | None = Field(default=None, pattern=r"^[A-Z0-9]{2}$")
    max_hkd: HKDLimit | None = None
    avoid_calendar_conflicts: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def itinerary(self):
        if (
            set(self.origin) & set(self.destination)
            or len(self.origin) * len(self.destination) > 4
            or self.return_date
            and self.return_date < self.departure
        ):
            raise ValueError(
                "Choose distinct routes, chronological dates and up to four airport pairs"
            )
        return self

    def routes(self):
        return [
            dict(origin=a, destination=b, state="queued")
            for a, b in product(self.origin, self.destination)
        ]

    def query(self, route):
        return LiveFlightQuery(
            origin=route["origin"],
            destination=route["destination"],
            departure=self.departure,
            return_date=self.return_date,
            adults=self.adults,
            checked_bags=self.adults if self.checked_bag_kg else 0,
            checked_bag_kg=self.checked_bag_kg or None,
            nonstop=self.nonstop,
            carrier=self.airline,
            flight_number=self.flight_number.replace(" ", "") if self.flight_number else None,
        )


TOOL = {
    "name": "live_flight_search",
    "description": "Search passenger fares at the desk-selected supplier in this chat. The desk selects sandbox inventory only for an explicit test. Adult travelers only. Carry dates, party, baggage and every airport the owner accepts from the preceding turns. Either airport means search both. Read-only: never books, holds or pays.",
    "parameters": MarketFlightRequest.model_json_schema(),
}


def combine(left, right):
    """Two read calls may describe the same search, one airport per call."""
    left = MarketFlightRequest.model_validate(left).model_dump()
    right = MarketFlightRequest.model_validate(right).model_dump()
    sides = {"origin", "destination"}
    if any(left[k] != right[k] for k in left.keys() - sides):
        raise DomainError("FLIGHT_DIFFERENT_SEARCH_TERMS", 422)
    origin, destination = (
        list(dict.fromkeys(left[k] + right[k])) for k in ("origin", "destination")
    )
    requested = set(product(left["origin"], left["destination"])) | set(
        product(right["origin"], right["destination"])
    )
    if (
        len(requested) > 4
        or set(product(origin, destination)) != requested
        or set(origin) & set(destination)
    ):
        raise DomainError("FLIGHT_DIFFERENT_SEARCH_TERMS", 422)
    return {**left, "origin": origin, "destination": destination}


def route_for(row, offer):
    # Search IDs may be cached by the supplier. The verified route is part of the binding.
    first, last = offer["outbound"][0], offer["outbound"][-1]
    for route in row["route_searches"]:
        if (route.get("search_id"), route["origin"], route["destination"]) == (
            offer["search_id"],
            first["origin"],
            last["destination"],
        ):
            return route
    raise DomainError("FLIGHT_LIVE_REVIEW_CHANGED", 409)


def source_for(row, offer):
    request = MarketFlightRequest.model_validate(row["market"])
    route = route_for(row, offer)
    spec = {
        "kind": "flight",
        "origin": route["origin"],
        "destination": route["destination"],
        "adults": request.adults,
        "departure": request.departure,
        "return_date": request.return_date,
        "checked_bag_kg": request.checked_bag_kg,
        "nonstop": request.nonstop,
        "currency": "HKD",
        "budget_minor": minor(request.max_hkd) if request.max_hkd is not None else None,
    }
    return {
        "provider": row.get("provider", "letsfg"),
        "label": "Nuitée Sandbox" if row.get("provider") == "nuitee_sandbox" else "LetsFG",
        "request": spec,
        "currency": "HKD",
        "listed_minor": offer["fare_minor"],
        "url": offer.get("booking_url"),
        "bags": request.adults if request.checked_bag_kg else 0,
        "bag_kg": None,
        "outbound": offer["outbound"],
        "inbound": offer["inbound"],
    }


def calendar_clear(store, offer):
    from .calendar_fit import check_itineraries

    sectors = [{"segments": legs} for legs in (offer["outbound"], offer["inbound"]) if legs]
    with store.connection() as db:
        return all(state == "clear" for state in check_itineraries(store, db, sectors))


def poll(service, principal, row):
    request = MarketFlightRequest.model_validate(row["market"])
    routes = [dict(part) for part in row["route_searches"]]
    deadline = datetime.fromisoformat(row["search_deadline"])
    for route in routes:
        if route["state"] not in {"queued", "searching"}:
            continue
        if service.store.clock() >= deadline:
            route.update(state="unavailable", reason="supplier_timeout")
            continue
        query = request.query(route)
        try:
            result = service.provider_for(row).search(
                query, principal=principal, search_id=route.get("search_id")
            )
        except DomainError as error:
            if error.code in {
                "OWNER_SIGN_IN_REQUIRED",
                "PRIVATE_CONTEXT_HIDDEN",
                "LETSFG_ACCOUNT_CHANGED",
            }:
                raise
            route.update(state="unavailable", reason=error.code)
            continue
        route.update(
            state=result["state"], search_id=result.get("search_id"), reason=result.get("reason")
        )
        offers = result.get("offers", [])
        if request.max_hkd is not None:
            offers = [o for o in offers if o["fare_minor"] <= minor(request.max_hkd)]
        if request.avoid_calendar_conflicts:
            offers = [o for o in offers if calendar_clear(service.store, o)]
        route["offers"] = offers
        if route["state"] == "offers" and not offers:
            route.update(state="no_verified_offer", reason="no_matching_itinerary")
    # Give every successful airport a place even when all its fares are more expensive.
    groups = [route.get("offers", []) for route in routes]
    offers = sorted(
        (group[0] for group in groups if group), key=lambda o: (not o["ready"], o["fare_minor"])
    )
    remaining = sorted(
        (o for group in groups for o in group[1:]), key=lambda o: (not o["ready"], o["fare_minor"])
    )
    offers.extend(remaining[: 8 - len(offers)])
    pending = any(r["state"] == "searching" for r in routes)
    state = "searching" if pending else ("offers" if offers else "market_empty")
    if service._sync_source(principal, row):
        service._write(
            principal, row, route_searches=routes, state=state, offers=offers, selected=None
        )


def initial(request, now):
    return {
        "market": request.model_dump(mode="json"),
        "active": True,
        "route_searches": request.routes(),
        "search_deadline": iso(now + SEARCH_WINDOW),
        "offers": [],
        "selected": None,
        "receipt": {},
    }

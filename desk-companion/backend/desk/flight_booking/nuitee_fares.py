"""Translate Nuitée Air's structured sandbox fares into the existing flight review."""

from datetime import datetime

from .live_fares import direction, minor_amount
from .timetable import flight_window


def legs(journey, query):
    parts = {"OUTBOUND": [], "INBOUND": []}
    for raw in journey["segments"]:
        carrier = raw["carrier"]
        # The supplier documents Nuitée Air as its synthetic end-to-end inventory.
        if carrier["marketingName"] != "Nuitée Air" or raw.get("stopCount", 0):
            raise ValueError("unsupported test itinerary")
        parts[raw["direction"]].append(
            {
                "origin": raw["originCode"],
                "destination": raw["destinationCode"],
                "departure_time": raw["departureTime"],
                "arrival_time": raw["arrivalTime"],
                "airline_code": carrier["marketingCode"],
                "flight_number": raw["flight"]["marketingNumber"],
            }
        )

    def validated(items, origin, destination, day):
        return direction(
            {"segments": items, "stops": len(items) - 1}, origin, destination, day, query
        )

    outbound = validated(parts["OUTBOUND"], query.origin, query.destination, query.departure)
    if bool(parts["INBOUND"]) != bool(query.return_date):
        raise ValueError("return itinerary differs")
    inbound = (
        validated(parts["INBOUND"], query.destination, query.origin, query.return_date)
        if parts["INBOUND"]
        else []
    )
    if query.flight_number and outbound[0]["flight"] != query.flight_number:
        raise ValueError("different flight")
    return outbound, inbound


def _included_bag(offer, currency):
    # This sandbox books one documented adult. Only a whole-offer, free allowance
    # establishes the checked weight. Never combine a paid option with a base fare.
    bag = offer.get("baggage") or {}
    if (
        bag.get("hasCheckedBag") is not True
        or (offer.get("fare") or {}).get("mixedFareFamily") is True
    ):
        return 0, 0
    choices = []
    for item in bag.get("included") or []:
        price = (item.get("pricing") or {}).get("display") or {}
        pieces, kg = item.get("pieces"), item.get("weightKg")
        if (
            item.get("bagType") == "checked"
            and item.get("passengerType") in {"ALL", "ADT"}
            and price.get("currency") == currency
            and minor_amount(price.get("amount")) == 0
            and type(pieces) is int
            and pieces > 0
            and type(kg) is int
            and kg > 0
        ):
            choices.append((kg, pieces))
    kg, pieces = max(choices, default=(0, 0))
    return pieces, kg


def normalize(journey, offer, query, search_id, offer_id, account_version, now):
    """Return only a verified route/party, retaining an explicit missing-bag state."""
    try:
        if query.adults != 1 or query.children or query.infants:
            return None
        if "passengers" in journey:
            party = journey["passengers"]
            if (party.get("adults"), party.get("children", 0), party.get("infants", 0)) != (
                1,
                0,
                0,
            ):
                return None
        outbound, inbound = legs(journey, query)
        departure = flight_window(outbound)
        if not departure or departure[0] <= now:
            return None
        if inbound and (not (ret := flight_window(inbound)) or ret[0] < departure[1]):
            return None
        for key, segments in (("outbound", outbound), ("inbound", inbound)):
            exact = getattr(query, key + "_flights")
            if exact and [s["flight"] for s in segments] != exact:
                return None
        display = offer["pricing"]["display"]
        fare = minor_amount(display["total"])
        if display["currency"] != query.currency or not fare:
            return None
        expiration = offer.get("expiration") or journey.get("expiration")
        ends = datetime.fromisoformat(expiration)
        if not ends.tzinfo or ends <= now:
            return None
        pieces, kg = _included_bag(offer, query.currency)
        ready = pieces >= query.checked_bags and kg >= (query.checked_bag_kg or 0)
        terms = offer.get("terms") or {}
        conditions = {}
        for field in ("refundable", "changeable", "hasChangeFee"):
            if type(terms.get(field)) is bool:
                conditions[field] = "Yes" if terms[field] else "No"
        family = (offer.get("fare") or {}).get("family")
        if isinstance(family, str) and len(family) <= 90:
            conditions["family"] = family
        return {
            "account_version": account_version,
            "search_id": search_id,
            "offer_id": offer_id,
            "outbound": outbound,
            "inbound": inbound,
            "currency": query.currency,
            "fare_minor": fare,
            "total_minor": fare if ready else None,
            "ready": ready,
            "reason": None if ready else "checked_baggage_unverified",
            "passenger_count": 1,
            "checked_bags": pieces,
            "checked_bag_kg": kg or None,
            "baggage_evidence": f"{pieces} × {kg} kg" if pieces else None,
            "fare_conditions": conditions,
            "conditions_source": "provider",
            "expires_at": expiration,
        }
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        return None

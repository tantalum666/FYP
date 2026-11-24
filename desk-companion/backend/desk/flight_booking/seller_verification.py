"""Verify a particular seller listing using the desk's existing read-only managed research."""

import re
from urllib.parse import parse_qs, urlsplit

from .. import browser_research
from ..store import DomainError
from . import checkout_source


def target(row, number, original=False):
    source = row["source"]
    offers = row.get("offers") or []
    if number is not None and not 1 <= number <= len(offers):
        raise DomainError("FLIGHT_LIVE_REVIEW_CHANGED", 409)
    offer = offers[number - 1] if number is not None else None
    if not original and offer and offer.get("booking_url"):
        from .live_fares import official_url

        url = official_url(offer["booking_url"])
        if url:
            parts = urlsplit(url)
            query = parse_qs(parts.query)
            search_matches = "sid" not in query or query["sid"] == [offer["search_id"]]
            offer_matches = offer["offer_id"] in parts.path.split("/") or any(
                query.get(key) == [offer["offer_id"]] for key in ("offer", "offer_id")
            )
            if search_matches and offer_matches:
                return "LetsFG", url, offer
    return "Kiwi.com", source["url"], offer


def begin(runtime, principal, row, number, *, original=False):
    source = row["source"]
    spec = source["request"]
    seller, url, offer = target(row, number, original)
    prior = row.get("seller_check") or {}
    identity = (offer["search_id"], offer["offer_id"]) if offer else (None, None)
    if (prior.get("url"), prior.get("search_id"), prior.get("offer_id")) == (
        url,
        *identity,
    ) and prior.get("status") == "running":
        return prior
    fragments = []
    for side in ("outbound", "inbound"):
        legs = offer[side] if offer else source[side]
        if legs:
            fragments.append(
                side
                + " "
                + ", ".join(
                    f"{leg.get('flight') or '?'} {leg.get('origin', '')}–{leg.get('destination', '')} {leg.get('departs') or ''}"
                    for leg in legs
                )
            )
    reference = offer["offer_id"] if seller == "LetsFG" and offer else "original Kiwi listing"
    goal = (
        f"Read this exact {seller} listing ({reference}) for {spec['origin']} to {spec['destination']} on {spec['departure']}, "
        f"return {spec.get('return_date') or 'none'}, {spec['adults']} adults, {source['currency']}. {'; '.join(fragments)}. "
        f"Verify {source['bags'] if source['bags'] is not None else spec['adults']} checked bag(s) and at least {spec['checked_bag_kg']} kg per adult on every ticketed sector. "
        "Report an all-in price, including mandatory taxes, fees and required luggage, only if the exact offer states it. "
        "Include all ticketed_sectors in both directions with operating_carrier, the flight numbers in the label, seller_offer_reference, included_checked_bags_for_party, baggage_coverage and a short baggage_evidence excerpt. Cite this exact listing for price and extras. "
        "Leave unverified amounts or weights null. A generic fare-family policy or a different flight is insufficient. "
        "Use public read-only information. Do not supply passenger data, sign in, reserve, click a purchase/hold/payment action, or accept a changed date or airport."
    )
    request = {
        k: spec[k]
        for k in (
            "kind",
            "origin",
            "destination",
            "departure",
            "return_date",
            "adults",
            "checked_bag_kg",
            "currency",
            "budget_minor",
        )
        if spec.get(k) is not None
    }
    request["currency"] = source["currency"]
    location = urlsplit(url)
    draft = {
        "title": f"{seller} · {spec['origin']}–{spec['destination']} · baggage and final total",
        "engine": "managed",
        "goal": goal,
        "start_url": url,
        "allowed_origins": [f"https://{location.netloc}"],
        "quote_request": request,
    }
    if row.get("task_id"):
        with runtime.store.connection() as db:
            task = runtime.tasks.get(db, row["task_id"])
        draft.update(task_id=task["id"], task_version=task["version"])
    key = f"flight-seller-verification/{row['id']}/{row['version']}"
    prepared = browser_research.prepare(runtime, draft, key + "/draft")["proposal"]
    # The dedicated owner action explicitly consents to viewing this exact public seller page.
    decision = runtime.assistant.decide(
        prepared["id"], "confirm", key + "/start", principal=principal, share_screen=True
    )
    return {
        "proposal_id": prepared["id"],
        "job_id": decision["job"]["id"],
        "seller": seller,
        "url": url,
        "status": "running",
        "search_id": identity[0],
        "offer_id": identity[1],
        "number": number,
        "source_digest": checkout_source.source_digest(source),
    }


def _same_ticket(page, source, offer):
    sectors = page.get("ticketed_sectors") or []
    spec = source["request"]
    for side, origin, destination, day in (
        ("outbound", spec["origin"], spec["destination"], spec["departure"]),
        ("inbound", spec["destination"], spec["origin"], spec.get("return_date")),
    ):
        legs = [leg for leg in sectors if leg["direction"] == side]
        if not day:
            if legs:
                return False
            continue
        if (
            not legs
            or legs[0]["origin"] != origin
            or legs[-1]["destination"] != destination
            or legs[0]["departs"][:10] != day
            or any(not leg["operating_carrier"].strip() for leg in legs)
            or any(left["destination"] != right["origin"] for left, right in zip(legs, legs[1:]))
        ):
            return False
        known = (offer or source)[side]
        if known and (
            len(known) != len(legs)
            or any(
                any(
                    old.get(k) and old[k] != current[k] for k in ("origin", "destination", "flight")
                )
                for old, current in zip(known, legs)
            )
        ):
            return False
    return True


def read(runtime, row, owner):
    check = row["seller_check"]
    selected = row["source"]
    spec = selected["request"]
    try:
        result = browser_research.status(
            runtime, {"proposal_id": check["proposal_id"]}, session_hash=owner
        )
    except DomainError as error:
        if error.code in {
            "DRAFT_NOT_FOUND",
            "COMPUTER_READBACK_CHANGED",
            "COMPUTER_SOURCE_CHANGED",
            "PROVIDER_CONTEXT_CHANGED",
            "COMPUTER_CLEANUP_REQUIRED",
        }:
            return {**check, "status": "unverified"}
        raise
    state = (result.get("job") or {}).get("state", result.get("draft_state"))
    if state in {"pending", "review", "queued", "running", "verifying"}:
        return None
    updated = {**check, "status": "unverified"}
    if not result.get("record_verified") or check["source_digest"] != checkout_source.source_digest(
        selected
    ):
        return updated
    quote = result.get("quote") or {}
    offered = quote.get("offer") or {}
    reviewed = quote.get("request") or {}
    number = check.get("number")
    stored = row["offers"][number - 1] if number else None
    if stored and (stored["search_id"], stored["offer_id"]) != (
        check["search_id"],
        check["offer_id"],
    ):
        return updated
    names = [
        leg.get("flight")
        for side in ("outbound", "inbound")
        for leg in (stored[side] if stored else selected[side])
        if leg.get("flight")
    ]

    designators = {
        t.replace(" ", "")
        for t in re.findall(
            r"(?<![A-Za-z0-9])[A-Z0-9]{2,3}\s?\d{1,5}[A-Z]?(?![A-Za-z0-9])",
            str(offered.get("label", "")),
        )
    }
    if (
        any(
            reviewed.get(k) != spec.get(k)
            for k in (
                "origin",
                "destination",
                "departure",
                "return_date",
                "adults",
                "checked_bag_kg",
            )
        )
        or not _same_ticket(offered, selected, stored)
        or offered.get("seller_offer_reference")
        != (
            check["offer_id"]
            if check["seller"] == "LetsFG"
            else urlsplit(check["url"]).path.rstrip("/").split("/")[-1]
        )
        or offered.get("baggage_coverage") != "all_ticketed_segments_for_every_traveller"
        or not offered.get("baggage_evidence")
        or type(offered.get("included_checked_bags_for_party")) is not int
        or offered["included_checked_bags_for_party"]
        < max(selected.get("bags") or 0, spec["adults"] if spec["checked_bag_kg"] else 0)
        or offered.get("currency") != selected["currency"]
        or offered.get("source_url") != check["url"]
        or offered.get("extras_source_url") != check["url"]
        or not names
        or not all(n in designators for n in names)
        or type(quote.get("total_minor")) is not int
        or type(offered.get("checked_bag_kg_per_adult")) is not int
        or offered["checked_bag_kg_per_adult"] < spec["checked_bag_kg"]
    ):
        return updated
    return {
        **updated,
        "status": "page_verified",
        "observed_at": quote["observed_at"],
        "page_total_minor": quote["total_minor"],
        "page_weight_kg": offered["checked_bag_kg_per_adult"],
    }

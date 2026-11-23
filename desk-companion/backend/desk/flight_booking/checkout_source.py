"""Bind a verified Kiwi listing and its reviewed travel requirements to a seller search."""

from datetime import datetime
import hashlib
import json
import re
from urllib.parse import urlsplit

from .. import browser_research
from ..commerce_quotes import FlightRequest
from ..store import encode


def purchase_intent(message):
    text = message.strip().casefold().rstrip("。.!！?？ ")
    return bool(
        re.fullmatch(
            r"(?:请|請)?(?:帮我|幫我|替我|麻烦你|麻煩你|我想|我要|我想要)?\s*(?:购买|購買|买下|買下|买|買|预订|預訂|订|訂)\s*"
            r"(?:下|了|一下)?\s*(?:刚才[的那]*|剛才[的那]*|上面[的那]*|这个|這個|這一|这一|这|這|那|该|該)?\s*"
            r"(?:张|張|个|個|班|趟|程)?\s*(?:往返)?(?:的)?(?:机票|機票|航班|飞机票|飛機票)(?:吧|呀|啊)?"
            r"|(?:please )?(?:(?:can|could) you |help me |i(?:'d| would) like to )?(?:book|buy|purchase) "
            r"(?:me )?(?:this|that|the (?:quoted|original|selected)) (?:return |round.trip )?(?:ticket|flight|fare|itinerary)"
            r"|(?:please )?(?:book|buy) (?:this|that) one",
            text,
        )
    )


def is_kiwi(proposal):
    if not proposal or proposal.get("kind") != "browser_research":
        return False
    request = proposal.get("data", {}).get("browser", {}).get("quote_request") or {}
    return request.get("kind") == "flight" and request.get("provider") == "kiwi"


def old_results(store, owner, task, proposal_id=None):
    # Old builds retained the original verified job and login but did not always retain
    # the chat link. The owner must select one of these originals to establish that link.
    with store.connection() as db:
        rows = db.execute(
            """SELECT p.id, j.request FROM assistant_proposals p
               JOIN operations o ON o.id='browser-research/prepare/' || p.id
               JOIN computer_jobs j ON j.id=json_extract(o.response,'$.job.id')
               WHERE p.kind='browser_research' AND j.state='succeeded'
                 AND json_extract(j.request,'$.session_hash')=? AND json_extract(j.request,'$.task_id') IS ?
                 AND json_extract(j.request,'$.quote_request.provider')='kiwi' AND (? IS NULL OR p.id=?)
                 AND NOT EXISTS (SELECT 1 FROM live_flight_checkouts c
                     WHERE json_extract(c.data,'$.proposal_id')=p.id)
               ORDER BY j.updated_at DESC LIMIT 12""",
            (owner, task, proposal_id, proposal_id),
        ).fetchall()
    return [
        {"proposal_id": r["id"], "request": json.loads(r["request"])["quote_request"]} for r in rows
    ]


def original(runtime, proposal_id, owner):
    checked = browser_research.status(runtime, {"proposal_id": proposal_id}, session_hash=owner)
    job = checked.get("job") or {}
    if not checked.get("record_verified"):
        return (
            "waiting_source"
            if (
                job.get("state") in {"review", "queued", "running", "verifying"}
                or (not job and checked["draft_state"] == "pending")
            )
            else "source_unavailable"
        ), None
    quote = checked.get("quote") or {}
    offer, proof = quote.get("offer") or {}, quote.get("supplier") or {}
    if not offer or proof.get("provider") != "Kiwi.com" or not proof.get("tool_result_sha256"):
        return "source_unavailable", None
    spec = FlightRequest.model_validate(quote["request"])
    link = urlsplit(offer.get("source_url") or "")
    if not (
        spec.provider == "kiwi"
        and link.scheme == "https"
        and link.netloc in {"kiwi.com", "www.kiwi.com"}
        and re.fullmatch(r"/u/[A-Za-z0-9_-]{1,100}/?", link.path)
        and not link.query
        and not link.fragment
    ):
        return "source_unavailable", None
    if (
        offer.get("origin"),
        offer.get("destination"),
        offer.get("departure"),
        offer.get("return_date"),
        offer.get("priced_units"),
    ) != (spec.origin, spec.destination, spec.departure, spec.return_date, spec.adults):
        return "source_unavailable", None
    source = {
        "request": spec.model_dump(exclude_none=True),
        "vendor": "Kiwi.com",
        "url": link.geturl(),
        "label": offer["label"],
        "currency": offer["currency"],
        "listed_minor": offer["price_minor"],
        "bags": proof.get("checked_bags_for_party"),
        "bag_kg": offer.get("checked_bag_kg_per_adult"),
        "outbound": proof.get("outbound") or [],
        "inbound": proof.get("inbound") or [],
        "observed_at": quote["observed_at"],
        "job_id": job["id"],
        "evidence": proof["tool_result_sha256"],
    }
    if not source["outbound"]:
        # Earlier verified Kiwi reports retained outbound flight numbers in this fixed label.
        prefix = f"{spec.origin}–{spec.destination} "
        if source["label"].startswith(prefix):
            codes = source["label"][len(prefix) :].split(" / ")
            if all(re.fullmatch(r"[A-Z0-9]{2,3}\s?\d{1,5}[A-Z]?", code) for code in codes):
                source["outbound"] = [{"flight": code.replace(" ", "")} for code in codes]
                times = (offer.get("price_evidence") or "").rsplit(" · ", 1)[-1].split(" → ")
                if len(times) == 2 and all(_wall(value) is not None for value in times):
                    source["outbound"][0]["departs"] = times[0]
                    source["outbound"][-1]["arrives"] = times[1]
    return "source", source


def source_digest(source):
    return hashlib.sha256(encode(source).encode()).hexdigest()


def query_for(source):
    from .live_provider import LiveFlightQuery

    spec = source["request"]
    filters = {}
    for side in ("outbound", "inbound"):
        legs = source[side]
        if legs and all(leg.get("flight") for leg in legs):
            filters[side + "_flights"] = [leg["flight"] for leg in legs]
        if legs and (departure := _wall(legs[0].get("departs"))):
            filters[side + "_departs_at"] = departure.strftime("%H:%M")
        if legs and (arrival := _wall(legs[-1].get("arrives"))):
            filters[side + "_arrives_at"] = arrival.strftime("%H:%M")
    return LiveFlightQuery(
        origin=spec["origin"],
        destination=spec["destination"],
        departure=spec["departure"],
        return_date=spec.get("return_date"),
        adults=spec["adults"],
        currency=source["currency"],
        checked_bags=max(source.get("bags") or 0, spec["adults"] if spec["checked_bag_kg"] else 0),
        checked_bag_kg=max(spec["checked_bag_kg"], source.get("bag_kg") or 0) or None,
        nonstop=spec.get("nonstop", False),
        **filters,
    )


def _wall(value):
    try:
        return datetime.fromisoformat(value).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def compatible(source, offer):
    spec = source["request"]
    if (
        offer.get("currency") != source["currency"]
        or offer.get("passenger_count") != spec["adults"]
    ):
        return False
    for direction, origin, destination, day in (
        ("outbound", spec["origin"], spec["destination"], spec["departure"]),
        ("inbound", spec["destination"], spec["origin"], spec.get("return_date")),
    ):
        legs, known = offer.get(direction) or [], source[direction]
        if not day:
            if legs:
                return False
            continue
        if (
            not legs
            or legs[0].get("origin") != origin
            or legs[-1].get("destination") != destination
            or str(legs[0].get("departs"))[:10] != day
            or (spec.get("nonstop") and len(legs) != 1)
        ):
            return False
        if known:
            if len(known) != len(legs):
                return False
            for old, new in zip(known, legs, strict=True):
                if any(
                    old.get(k) and old[k] != new.get(k) for k in ("origin", "destination", "flight")
                ):
                    return False
                if any(
                    old.get(k) and (_wall(old[k]) is None or _wall(old[k]) != _wall(new.get(k)))
                    for k in ("departs", "arrives")
                ):
                    return False
    return True


def payable(source, offer):
    spec = source["request"]
    total = offer.get("total_minor")
    bags = max(source.get("bags") or 0, spec["adults"] if spec["checked_bag_kg"] else 0)
    kilograms = max(spec["checked_bag_kg"], source.get("bag_kg") or 0)
    return (
        compatible(source, offer)
        and offer.get("ready") is True
        and type(total) is int
        and total > 0
        and (spec.get("budget_minor") is None or total <= spec["budget_minor"])
        and (not bags or (type(offer.get("checked_bags")) is int and offer["checked_bags"] >= bags))
        and (
            not kilograms
            or (type(offer.get("checked_bag_kg")) is int and offer["checked_bag_kg"] >= kilograms)
        )
    )


def consent_terms(offer):
    from .live_provider import terms

    return terms(offer)

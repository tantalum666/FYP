"""Read-only shopping and flight quotes from an owner-admitted hosted browser."""

from datetime import date
import ipaddress
import re
from typing import Annotated, Literal
from urllib.parse import unquote

from pydantic import AfterValidator, Field, model_validator

from . import hkd
from .browser_policy import canonical_https
from .purchase_cards import offer_total
from .schemas import StrictModel


def _calendar_day(value: str) -> str:
    date.fromisoformat(value)
    return value


Day = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$"), AfterValidator(_calendar_day)]
Airport = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
Currency = Literal["HKD", "USD", "SGD", "CNY", "JPY", "GBP", "EUR", "AUD", "TWD"]
Money = Annotated[int, Field(strict=True, ge=0, le=10**9)]
ShortText = Annotated[str, Field(min_length=1, max_length=320)]


class QuoteRequestBase(StrictModel):
    currency: Currency | None = None
    budget_minor: Money | None = None

    @model_validator(mode="after")
    def budget_currency(self):
        if self.budget_minor is not None and self.currency is None:
            raise ValueError("A budget requires its currency")
        return self


class ShoppingRequest(QuoteRequestBase):
    kind: Literal["shopping"]
    product: ShortText
    quantity: int = Field(ge=1, le=99, strict=True, description="Number of retail selling units")
    fulfilment: Literal["delivery", "pickup"]


class FlightRequest(QuoteRequestBase):
    kind: Literal["flight"]
    provider: Literal["kiwi"] | None = Field(default=None, exclude_if=lambda value: value is None)
    nonstop: bool = Field(default=False, strict=True, exclude_if=lambda value: not value,
                         description="Set for a requested nonstop Kiwi connector search")
    origin: Airport
    destination: Airport
    departure: Day
    return_date: Day | None = None
    adults: int = Field(ge=1, le=9, strict=True)
    checked_bag_kg: int = Field(ge=0, le=60, strict=True, description="Per adult")

    @model_validator(mode="after")
    def itinerary(self):
        if self.nonstop and self.provider != "kiwi":
            raise ValueError("Use the flight connector for a structured nonstop filter")
        if self.origin == self.destination or (
            self.return_date and self.return_date < self.departure
        ):
            raise ValueError("Choose distinct airports and chronological dates")
        return self


QuoteRequest = ShoppingRequest | FlightRequest


class ListedPrice(StrictModel):
    label: ShortText
    source_url: str = Field(min_length=1, max_length=2000)
    currency: Currency
    price_minor: Money
    priced_units: int = Field(
        ge=1, le=99, strict=True, description="Retail packs or adults in the displayed price"
    )
    basis: Literal["listed", "from", "conditional", "quantity_offer"]
    price_evidence: ShortText
    availability: Literal["available", "unavailable", "unknown"]
    extras_minor: Money | None = Field(
        description="All mandatory extras for this full request, including delivery or taxes and required bags. Null unless explicit."
    )
    extras_evidence: ShortText | None
    extras_source_url: str | None = Field(max_length=2000)
    conditions: ShortText | None


class RetailPrice(ListedPrice):
    product_matches: Literal["yes", "no", "unknown"]
    fulfilment: Literal["delivery", "pickup", "unknown"]


class Airfare(ListedPrice):
    origin: Airport | None
    destination: Airport | None
    departure: Day | None
    journey: Literal["one_way", "round_trip", "unknown"]
    return_date: Day | None
    checked_bag_kg_per_adult: int | None = Field(ge=0, le=100, strict=True)


class RetailPage(StrictModel):
    offer: RetailPrice | None
    note: ShortText


class FlightPage(StrictModel):
    offer: Airfare | None
    note: ShortText


class FlightSupplier(StrictModel):
    provider: Literal["Kiwi.com"]
    matching_offers: int = Field(ge=0, le=500, strict=True)
    tool_result_sha256: str = Field(pattern="^[a-f0-9]{64}$")
    checked_bags_for_party: int | None = Field(ge=0, le=18, strict=True)
    terms_url: Literal["https://www.kiwi.com/en/pages/content/legal/"]
    airline_bag_rules: Literal["https://www.hkexpress.com/plan-your-trip/baggage/baggage-fees-for-agent-bookings"] | None


class ConnectorFlightPage(FlightPage):
    supplier: FlightSupplier | None = None


QUOTE_INSTRUCTIONS = (
    " For this public quote, stop at any sign-in or challenge and return offer=null with a brief note. "
    "Use the structured quote format. Only return an offer actually seen on the admitted public site. "
    "Cite a stable public HTTPS product or route page without a query or fragment; never cite an account "
    "or checkout. Quote a short visible price excerpt. Use ISO currency minor units (JPY whole yen). "
    "Use basis=quantity_offer for a bulk price whose only purchase condition is the displayed lot size "
    "(while stocks last is an availability caveat). Use conditional if a coupon, membership, minimum "
    "spend or other unverified condition is needed. '2 for $34' has priced_units=2 and price_minor=3400 "
    "for a two-decimal currency. Do not confuse a selling pack with pieces inside it. Mark historical, "
    "calendar or advertised minimum fares as from. Do not extrapolate a single traveler's price to a party. "
    "Never infer stock or seat availability from a listing alone. Leave extras_minor null unless ALL "
    "mandatory fees for the entire requested order, delivery or taxes and requested baggage are explicit; "
    "when known, cite the page and short text establishing them. Unknown is never zero. "
    "Record missing fees and fare-change/refund restrictions in conditions or note. Use the owner's language."
)


def page_model(kind):
    return RetailPage if kind == "shopping" else FlightPage


def quote_link(url, origins):
    parsed = canonical_https(url)
    if not parsed or parsed.query or parsed.fragment or f"https://{parsed.hostname}" not in origins:
        raise ValueError("Quote source is outside approved public pages")
    host = parsed.hostname
    if (
        "." not in host
        or host.endswith((".localhost", ".local", ".internal"))
        or host.replace(".", "").isdigit()
    ):
        raise ValueError("Use a public website for quote links")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("Use a website name for quote links")
    if re.search(r"(?:^|/)(?:checkout|logout|signout|payment)(?:/|$)", unquote(parsed.path), re.I):
        raise ValueError("Use a public listing or fee terms page")
    return url


def read_quote(request, raw_report, observed_at):
    spec = request["quote_request"]
    retail = spec["kind"] == "shopping"
    report_type = ConnectorFlightPage if spec.get("provider") == "kiwi" else page_model(spec["kind"])
    page = report_type.model_validate_json(raw_report)
    card = {
        "request": spec,
        "observed_at": observed_at,
        "note": page.note,
        "offer": None,
        "subtotal_minor": None,
        "total_minor": None,
        "budget_status": "unknown",
    }
    if isinstance(page, ConnectorFlightPage) and page.supplier:
        card["supplier"] = page.supplier.model_dump()
    if start := canonical_https(request["start_url"]):
        origin = f"https://{start.hostname}"
        card["approved_page"] = quote_link(
            origin if start.query or start.fragment else request["start_url"],
            request["allowed_origins"],
        )
    offer = page.offer
    if offer is None:
        return card
    quote_link(offer.source_url, request["allowed_origins"])
    if offer.extras_source_url:
        quote_link(offer.extras_source_url, request["allowed_origins"])
    if offer.extras_minor is not None and not (offer.extras_evidence and offer.extras_source_url):
        raise ValueError("Mandatory fees need source evidence")
    card["offer"] = offer.model_dump()
    if retail:
        quantity = spec["quantity"]
        matches = offer.product_matches == "yes" and offer.priced_units in {1, quantity}
        lots = quantity if offer.priced_units == 1 else 1
        fulfils = offer.fulfilment == spec["fulfilment"]
    else:
        matches = (
            (offer.origin, offer.destination, offer.departure, offer.return_date)
            == (spec["origin"], spec["destination"], spec["departure"], spec.get("return_date"))
            and offer.journey == ("round_trip" if spec.get("return_date") else "one_way")
            and offer.priced_units == spec["adults"]
        )
        lots = 1
        fulfils = not spec["checked_bag_kg"] or (
            offer.checked_bag_kg_per_adult is not None
            and offer.checked_bag_kg_per_adult >= spec["checked_bag_kg"]
        )
    quantity_offer = (
        retail and offer.basis == "quantity_offer" and offer.priced_units == spec["quantity"]
    )
    if (
        not matches
        or (offer.basis != "listed" and not quantity_offer)
        or offer.availability == "unavailable"
    ):
        return card
    card["subtotal_minor"] = offer_total(lots, offer.price_minor, 0)
    if spec.get("currency") == offer.currency and spec.get("budget_minor") is not None:
        if card["subtotal_minor"] > spec["budget_minor"]:
            card["budget_status"] = "over"
    if fulfils and offer.extras_minor is not None and offer.availability == "available":
        card["total_minor"] = offer_total(lots, offer.price_minor, offer.extras_minor)
        if spec.get("currency") == offer.currency and spec.get("budget_minor") is not None:
            card["budget_status"] = (
                "within" if card["total_minor"] <= spec["budget_minor"] else "over"
            )
    return card


def kiwi_hkd_price(quote):
    """Only a verified provider quote can give a price to the local chat/voice renderer."""
    if not isinstance(quote, dict):
        return None
    request = quote.get("request") or {}
    supplier = quote.get("supplier") or {}
    offer = quote.get("offer") or quote  # Full stored receipt or its bounded projection.
    if not all(isinstance(part, dict) for part in (request, supplier, offer)):
        return None
    if (
        request.get("kind") != "flight" or request.get("provider") != "kiwi"
        or supplier.get("provider") != "Kiwi.com" or offer.get("currency") != "HKD"
        or offer.get("basis") != "listed" or type(offer.get("price_minor")) is not int
        or offer["price_minor"] != quote.get("subtotal_minor") or not isinstance(offer.get("label"), str)
    ):
        return None
    return hkd.amount(quote.get("subtotal_minor"))


def kiwi_fare_reply(quote):
    price = kiwi_hkd_price(quote)
    if not price:
        return None
    offer = quote.get("offer") or quote
    display = price["display"]
    label = offer["label"]
    details = []
    if (quote.get("request") or {}).get("checked_bag_kg") and offer.get("checked_bag_kg_per_adult") is None:
        details.append("托运行李重量未确认")
    total = hkd.amount(quote.get("total_minor"))
    if total:
        details.append(f"已核实的总额为 {total['display']}")
    else:
        details.append("最终应付金额仍待卖家确认")
    suffix = "，".join(details) + "。" if details else ""
    return {
        "kind": "reply", "mode": "local_rules", "saved": False,
        "message": f"Kiwi.com 列出的 {label} 票价是 {display}。{suffix}",
    }


def brief_quote(quote):
    """Keep the price basis and unanswered questions together in bounded model context."""
    offer = quote["offer"] or {}
    summary = {
        **{k: quote[k] for k in ("observed_at", "subtotal_minor", "total_minor", "budget_status")},
        **{
            k: offer[k]
            for k in (
                "label",
                "basis",
                "currency",
                "price_minor",
                "priced_units",
                "extras_minor",
                "availability",
            )
            if k in offer
        },
        "request": quote["request"],
        "note": quote["note"],
        "transaction_confirmed": False,
    }
    if len(offer.get("source_url", "")) <= 512 and offer.get("source_url"):
        summary["source_url"] = offer["source_url"]
    if supplier := quote.get("supplier"):
        summary["supplier"] = {k:supplier[k] for k in ("provider", "checked_bags_for_party", "terms_url", "airline_bag_rules")}
    if price := kiwi_hkd_price(quote):
        summary["price_display"] = price["display"]
        if total := hkd.amount(quote.get("total_minor")):
            summary["total_display"] = total["display"]
    return summary

"""Commercial terms shared by the Woo cart, owner review and merchant readback."""

import html
import re
from typing import Annotated, Literal

from pydantic import Field, ValidationError, model_validator

from ..commerce_quotes import QuoteRequestBase
from ..commerce_review import ReviewRef
from ..schemas import StrictModel
from ..store import DomainError


MAX_LINES = 8
MAX_QUANTITY = 99
Quantity = Annotated[int, Field(strict=True, ge=1, le=MAX_QUANTITY)]
ProductName = Annotated[str, Field(min_length=1, max_length=140)]
Minor = Annotated[int, Field(strict=True, ge=0, lt=10**11)]


class ShopItem(StrictModel):
    product: ProductName
    quantity: Quantity
    alternative_search: ProductName | None = Field(
        default=None, description="Same product family to search if the exact item is unavailable."
    )
    allowed_quantities: list[Quantity] = Field(
        default_factory=list, max_length=8, description="Other selling-unit counts explicitly allowed by the owner."
    )
    required_attributes: dict[ProductName, ProductName] = Field(
        default_factory=dict, max_length=8, description="Required concrete variant attributes, e.g. Color: Blue."
    )


class ShopQuery(QuoteRequestBase):
    """Send all requested selling units in items, or use product and quantity for one item."""

    product: ProductName | None = None
    quantity: Quantity | None = None
    items: list[ShopItem] | None = Field(default=None, min_length=1, max_length=MAX_LINES)

    @model_validator(mode="after")
    def complete_request(self):
        if self.items and self.product is None and self.quantity is None:
            return self
        if self.items is None and self.product and self.quantity:
            return self
        raise ValueError("Specify every product and quantity in one request")

    def requested_items(self):
        return self.items or [ShopItem(product=self.product, quantity=self.quantity)]


class ShopReviewRef(ReviewRef):
    # A set of suggestions has no selected cart or payable amount.
    amount_minor: int | None = Field(gt=0, strict=True)


class ItemUnavailable(DomainError):
    def __init__(self, product_id):
        super().__init__("SHOP_ITEM_UNAVAILABLE", 409)
        self.product_id = product_id


class CheckoutItemsChanged(DomainError):
    """The merchant's pre-payment guard rejected these final order lines."""

    def __init__(self, approved, actual, names):
        super().__init__("SHOP_CHECKOUT_ITEMS_CHANGED", 409)
        before, after = selection(approved), selection(actual)

        def changed(lines, other):
            result = []
            for ident, (sku, quantity) in lines.items():
                if (sku, quantity) == other.get(ident):
                    continue
                name = names.get((ident, sku))
                label = f"{name} ({sku})" if name and name != sku else sku
                result.append(f"{label} × {quantity}")
            return result

        self.change = {
            "removed": changed(before, after),
            "added": changed(after, before),
            "total_minor": actual["total_minor"],
        }


class OrderLine(StrictModel):
    # Woo cart IDs identify the concrete variation when one is selected.
    product_id: Annotated[int, Field(strict=True, gt=0)]
    sku: Annotated[str, Field(min_length=1)]
    quantity: Quantity
    subtotal_minor: Minor
    discount_minor: Minor
    subtotal_tax_minor: Minor
    tax_minor: Minor


class OrderFee(StrictModel):
    name: str
    total_minor: Minor
    tax_minor: Minor


class BasketTerms(StrictModel):
    items: list[OrderLine] = Field(min_length=1, max_length=MAX_LINES)
    currency: Literal["HKD"]
    subtotal_minor: Minor
    discount_minor: Minor
    fees: list[OrderFee]
    fees_minor: Minor
    shipping_minor: Minor
    shipping_tax_minor: Minor
    tax_minor: Minor
    total_minor: Minor
    rate_id: str


def minor(value):
    if not re.fullmatch(r"[0-9]{1,11}", str(value)):
        raise DomainError("SHOP_UNVERIFIED", 502)
    return int(value)


def checked_terms(raw):
    """Normalize only ordering. Every amount must reconcile to the merchant's full cart."""
    try:
        t = BasketTerms.model_validate(raw, strict=True)
    except ValidationError:
        raise DomainError("SHOP_UNVERIFIED", 502) from None
    if (
        len({i.product_id for i in t.items}) != len(t.items)
        or len({i.sku.casefold() for i in t.items}) != len(t.items)
        or any(
            i.subtotal_minor % i.quantity or i.discount_minor > i.subtotal_minor for i in t.items
        )
        or sum(i.subtotal_minor for i in t.items) != t.subtotal_minor
        or sum(i.discount_minor for i in t.items) != t.discount_minor
        or sum(f.total_minor for f in t.fees) != t.fees_minor
        or sum(i.tax_minor for i in t.items)
        + sum(f.tax_minor for f in t.fees)
        + t.shipping_tax_minor
        != t.tax_minor
        or (not t.rate_id and (t.shipping_minor or t.shipping_tax_minor))
        or t.total_minor <= 0
        or t.subtotal_minor - t.discount_minor + t.fees_minor + t.shipping_minor + t.tax_minor
        != t.total_minor
    ):
        raise DomainError("SHOP_UNVERIFIED", 502)
    t.items.sort(key=lambda i: i.product_id)
    t.fees.sort(key=lambda f: (f.name, f.total_minor, f.tax_minor))
    return t.model_dump()


def selection(terms):
    return {i["product_id"]: (i["sku"], i["quantity"]) for i in terms["items"]}


def money_block(block):
    if block.get("currency_code") != "HKD" or block.get("currency_minor_unit") != 2:
        raise DomainError("SHOP_UNVERIFIED", 502)
    return block


def cart_quote(cart, requested, quantity=None):
    """Match the final addressed cart, including its single selected delivery rate."""
    try:
        return _cart_quote(cart, requested, quantity)
    except (KeyError, TypeError, AttributeError):
        raise DomainError("SHOP_UNVERIFIED", 502) from None


def _cart_quote(cart, requested, quantity):
    if cart.get("errors"):
        raise DomainError("SHOP_ITEM_UNAVAILABLE", 409)
    totals = money_block(cart["totals"])
    if "stripe_cc" not in cart["payment_methods"]:
        raise DomainError("SHOP_UNVERIFIED", 502)
    packages = cart["shipping_rates"]
    rates = [r for p in packages for r in p["shipping_rates"] if r["selected"] is True]
    needs_shipping = cart["needs_shipping"]
    if needs_shipping is True:
        if cart["has_calculated_shipping"] is not True or len(packages) != 1 or len(rates) != 1:
            raise DomainError("SHOP_DELIVERY_UNAVAILABLE", 409)
    elif needs_shipping is not False or rates:
        raise DomainError("SHOP_UNVERIFIED", 502)
    # Woo can leave both delivery amounts null when the cart is entirely virtual.
    shipping, shipping_tax = (
        0 if needs_shipping is False and totals[key] is None else minor(totals[key])
        for key in ("total_shipping", "total_shipping_tax")
    )
    rate = money_block(rates[0]) if rates else None
    if rate and (
        not rate["rate_id"]
        or minor(rate["price"]) != shipping
        or minor(rate["taxes"]) != shipping_tax
    ):
        raise DomainError("SHOP_UNVERIFIED", 502)

    lines, names = [], {}
    for item in cart["items"]:
        values = money_block(item["totals"])
        subtotal = minor(values["line_subtotal"])
        unit = minor(money_block(item["prices"])["price"])
        if unit * item["quantity"] != subtotal:
            raise DomainError("SHOP_UNVERIFIED", 502)
        lines.append(
            {
                "product_id": item["id"],
                "sku": item["sku"],
                "quantity": item["quantity"],
                "subtotal_minor": subtotal,
                "discount_minor": subtotal - minor(values["line_total"]),
                "subtotal_tax_minor": minor(values["line_subtotal_tax"]),
                "tax_minor": minor(values["line_total_tax"]),
            }
        )
        names[str(item["id"])] = html.unescape(item["name"])
    fees = []
    for fee in cart["fees"]:
        values = money_block(fee["totals"])
        fees.append(
            {
                "name": html.unescape(fee["name"]),
                "total_minor": minor(values["total"]),
                "tax_minor": minor(values["total_tax"]),
            }
        )
    subtotal_tax = sum(line["subtotal_tax_minor"] for line in lines)
    if (
        subtotal_tax != minor(totals["total_items_tax"])
        or subtotal_tax - sum(line["tax_minor"] for line in lines)
        != minor(totals["total_discount_tax"])
        or sum(fee["tax_minor"] for fee in fees) != minor(totals["total_fees_tax"])
    ):
        raise DomainError("SHOP_UNVERIFIED", 502)
    terms = checked_terms(
        {
            "items": lines,
            "currency": "HKD",
            "subtotal_minor": minor(totals["total_items"]),
            "discount_minor": minor(totals["total_discount"]),
            "fees": fees,
            "fees_minor": minor(totals["total_fees"]),
            "shipping_minor": shipping,
            "shipping_tax_minor": shipping_tax,
            "tax_minor": minor(totals["total_tax"]),
            "total_minor": minor(totals["total_price"]),
            "rate_id": rate["rate_id"] if rate else "",
        }
    )
    quote = {
        "terms": terms,
        "item_names": names,
        "shipping_name": html.unescape(rate["name"]) if rate else "",
        "destination": "HK" if rate else None,
    }
    if quantity is not None:
        # Rebuild old pending carts by stored ID. The richer terms get a fresh review.
        if len(lines) != 1 or (lines[0]["product_id"], lines[0]["quantity"]) != (
            requested,
            quantity,
        ):
            raise DomainError("SHOP_UNVERIFIED", 502)
    elif selection(terms) != requested:
        raise DomainError("SHOP_UNVERIFIED", 502)
    return quote


def checkout_revision(basis, revised):
    """Accept merchant-only pricing changes for exactly the requested goods and quantities."""
    original = basis["terms"]
    raw = revised.get("terms") if isinstance(revised, dict) else None
    if not isinstance(raw, dict) or not isinstance(revised.get("shipping_name"), str):
        raise DomainError("SHOP_UNVERIFIED", 502)
    quote = {
        **basis,
        "shipping_name": html.unescape(revised["shipping_name"]),
        "checkout_basis": basis,
    }
    if "items" in original:
        terms = checked_terms(raw)
        if selection(terms) != selection(original) or bool(terms["rate_id"]) != bool(
            original["rate_id"]
        ):
            raise DomainError("SHOP_UNVERIFIED", 502)
        return {**quote, "terms": terms}

    if raw.keys() != original.keys() or any(
        raw[k] != original[k] for k in ("product_id", "sku", "quantity", "currency")
    ):
        raise DomainError("SHOP_UNVERIFIED", 502)
    amounts = {k: minor(v) for k, v in raw.items() if k.endswith("_minor")}
    total = (
        amounts["subtotal_minor"]
        - amounts["discount_minor"]
        + amounts["shipping_minor"]
        + amounts["fees_minor"]
        + amounts["tax_minor"]
    )
    if (
        total != amounts["total_minor"]
        or total <= 0
        or amounts["subtotal_minor"] % raw["quantity"]
        or not isinstance(raw["rate_id"], str)
        or bool(raw["rate_id"]) != bool(original["rate_id"])
    ):
        raise DomainError("SHOP_UNVERIFIED", 502)
    return {
        **quote,
        "terms": {**raw, **amounts},
        "unit_minor": amounts["subtotal_minor"] // raw["quantity"],
    }

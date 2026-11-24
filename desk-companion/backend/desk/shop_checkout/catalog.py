"""Resolve exact Woo products and price owner-selectable alternatives as whole carts."""

import html

from ..store import DomainError
from .terms import ItemUnavailable, MAX_QUANTITY, selection


def response_json(response):
    if not response.is_success:
        raise DomainError("SHOP_PROVIDER_UNAVAILABLE", 503)
    try:
        return response.json()
    except ValueError:
        raise DomainError("SHOP_PROVIDER_UNAVAILABLE", 503) from None


def normalized(value):
    return " ".join(html.unescape(value).casefold().split())


def products(shop, *, unique=False, **filters):
    response = shop.get("wc/store/v1/products", params={**filters, "per_page": 20})
    rows = response_json(response)
    if not isinstance(rows, list) or any(
        not isinstance(p, dict) or type(p.get("id")) is not int or p["id"] <= 0
        or not isinstance(p.get("name"), str) or not isinstance(p.get("sku"), str)
        for p in rows
    ):
        raise DomainError("SHOP_UNVERIFIED", 502)
    if unique and response.headers.get("X-WP-TotalPages", "1") not in {"0", "1"}:
        raise DomainError("SHOP_AMBIGUOUS", 409)
    return rows


def lookup(shop, label):
    """A single fuzzy search result is still a suggestion, never an exact match."""
    for param, field in (("sku", "sku"), ("search", "name")):
        matches = {
            p["id"]: p
            for kind in ({}, {"type": "variation"})
            for p in products(shop, unique=True, **{param: label}, **kind)
            if normalized(p[field]) == normalized(label)
        }
        if len(matches) > 1:
            raise DomainError("SHOP_AMBIGUOUS", 409)
        if matches:
            match = next(iter(matches.values()))
            if match.get("type") == "variable":
                raise DomainError("SHOP_AMBIGUOUS", 409)
            return match
    return None


def attributes(product):
    # Multiple advertised values belong to a parent or a configurable product.
    # Only a concrete value is evidence of the requested variant.
    result = {}
    for attr in product.get("attributes") or []:
        terms = attr.get("terms") or []
        if attr.get("name") and len(terms) == 1 and terms[0].get("name"):
            result[normalized(attr["name"])] = normalized(terms[0]["name"])
    variation = product.get("variation")
    if isinstance(variation, str):
        for pair in html.unescape(variation).split(","):
            name, sep, value = pair.partition(":")
            if sep and name.strip() and value.strip():
                result[normalized(name)] = normalized(value)
    return result


def available(product, required):
    return bool(
        product and product.get("type") in {"simple", "variation"} and product["sku"].strip()
        and product.get("is_purchasable") is True and product.get("is_in_stock") is True
        and product.get("is_on_backorder") is not True
        and required.items() <= attributes(product).items()
    )


def with_limits(quote, limits):
    budget = limits.get("budget_minor")
    if budget is not None and quote["terms"]["total_minor"] > budget:
        raise DomainError("SHOP_OVER_BUDGET", 409)
    return {**quote, "limits": limits} if limits else quote


def verify_products(shop, wanted, limits):
    for ident, (sku, _) in wanted.items():
        product = lookup(shop, sku)
        required = limits.get("attributes", {}).get(str(ident), {})
        if not available(product, required) or product["id"] != ident or product["sku"] != sku:
            raise ItemUnavailable(ident)


def requote(shop, quote, cart):
    wanted = selection(quote["terms"])
    limits = quote.get("limits", {})
    verify_products(shop, wanted, limits)
    return with_limits(cart(shop, wanted)[0], limits)


def price_basket(shop, cart, lines, counts, requirements, budget):
    wanted, bindings = {}, {}
    for product, quantity, required in zip(lines, counts, requirements, strict=True):
        ident, sku = product["id"], product["sku"]
        prior_sku, prior_count = wanted.get(ident, (sku, 0))
        if prior_sku != sku:
            raise DomainError("SHOP_UNVERIFIED", 502)
        if quantity + prior_count > MAX_QUANTITY:
            raise DomainError("SHOP_QUANTITY_LIMIT", 409)
        wanted[ident] = (sku, quantity + prior_count)
        if required:
            bindings.setdefault(str(ident), {}).update(required)
    limits = {"budget_minor": budget} if budget is not None else {}
    if bindings:
        limits["attributes"] = bindings
    return with_limits(cart(shop, wanted)[0], limits)


def quote_query(shop, query, cart):
    items = query.requested_items()
    lines = [lookup(shop, item.product.strip()) for item in items]
    requirements = [
        {normalized(k): normalized(v) for k, v in item.required_attributes.items()} for item in items
    ]
    for index, product in enumerate(lines):
        if product and product.get("type") == "variation":
            variant = attributes(product)
            required = requirements[index]
            if any(key in variant and variant[key] != value for key, value in required.items()):
                raise DomainError("SHOP_AMBIGUOUS", 409)
            requirements[index] = {**variant, **required}

    result = quote_or_suggest(shop, cart, items, lines, requirements, query.budget_minor)
    # Preserve concrete SKU attributes for a later owner-requested search, even
    # if the original variation has since disappeared from the catalog.
    result["request"] = {
        **query.model_dump(include={"currency", "budget_minor"}, exclude_none=True),
        "items": [
            {**item.model_dump(exclude_defaults=True), "required_attributes": required}
            for item, required in zip(items, requirements, strict=True)
        ],
    }
    return result


def quote_or_suggest(shop, cart, items, lines, requirements, budget):
    counts = [item.quantity for item in items]
    missing = [i for i, p in enumerate(lines) if not available(p, requirements[i])]
    if not missing:
        try:
            return price_basket(shop, cart, lines, counts, requirements, budget)
        except ItemUnavailable as error:
            missing = [i for i, p in enumerate(lines) if p["id"] == error.product_id]
        except DomainError as error:
            # Some addressed carts report insufficient stock without a line ID.
            if len(items) != 1 or error.code != "SHOP_ITEM_UNAVAILABLE":
                raise
            missing = [0]
    if len(missing) != 1:
        raise DomainError("SHOP_ITEM_UNAVAILABLE", 409)

    index = missing[0]
    item, exact = items[index], lines[index]
    search = item.alternative_search or (html.unescape(exact["name"]) if exact else item.product)
    candidates = [exact] if exact else []
    required = requirements[index]
    if not exact or exact.get("type") != "variation" or required:
        for filters in ({"search": search}, {"search": search, "type": "variation"}):
            candidates.extend(products(shop, **filters))
    quantities = list(dict.fromkeys([item.quantity, *item.allowed_quantities]))
    options, seen = [], set()
    for candidate in candidates:
        if candidate["id"] in seen or not available(candidate, required):
            continue
        seen.add(candidate["id"])
        for quantity in quantities:
            if exact and candidate["id"] == exact["id"] and quantity == item.quantity:
                continue
            lines[index], counts[index] = candidate, quantity
            try:
                quote = price_basket(shop, cart, lines, counts, requirements, budget)
            except DomainError as error:
                if error.code in {
                    "SHOP_ITEM_UNAVAILABLE", "SHOP_OVER_BUDGET", "SHOP_DELIVERY_UNAVAILABLE",
                    "SHOP_QUANTITY_LIMIT",
                }:
                    continue
                raise
            options.append({
                "name": quote["item_names"][str(candidate["id"])], "sku": candidate["sku"],
                "quantity": quantity, "quote": quote,
            })
            if len(options) == 3:
                break
        if len(options) == 3:
            break
    if not options:
        raise DomainError("SHOP_ITEM_UNAVAILABLE" if exact else "SHOP_NO_MATCH", 409 if exact else 404)
    return {"unavailable_product": item.product, "alternatives": options}

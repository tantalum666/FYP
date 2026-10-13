"""Small audited JSON Schema subset; no reference fetches, regexes or coercion."""

import hashlib
import json
import math

from ..store import DomainError


class ConnectorError(DomainError):
    pass


def canonical(value, *, limit=32768):
    count = [0]

    def visit(item, depth):
        count[0] += 1
        if depth > 16 or count[0] > 4096:
            raise ConnectorError("CONNECTOR_DATA_LIMIT", 422)
        if item is None or type(item) is bool:
            return
        if type(item) in (int, float):
            if abs(item) > 1e100 or (type(item) is float and not math.isfinite(item)):
                raise ConnectorError("CONNECTOR_DATA_INVALID", 422)
        elif type(item) is str:
            if len(item) > 65536:
                raise ConnectorError("CONNECTOR_DATA_LIMIT", 422)
        elif type(item) is list:
            if len(item) > 256:
                raise ConnectorError("CONNECTOR_DATA_LIMIT", 422)
            for entry in item:
                visit(entry, depth + 1)
        elif type(item) is dict:
            if len(item) > 128 or any(type(k) is not str or len(k) > 256 for k in item):
                raise ConnectorError("CONNECTOR_DATA_LIMIT", 422)
            for entry in item.values():
                visit(entry, depth + 1)
        else:
            raise ConnectorError("CONNECTOR_DATA_INVALID", 422)

    visit(value, 0)
    try:
        raw = json.dumps(
            value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
    except (ValueError, UnicodeError, OverflowError):
        raise ConnectorError("CONNECTOR_DATA_INVALID", 422) from None
    if len(raw) > limit:
        raise ConnectorError("CONNECTOR_DATA_LIMIT", 422)
    return raw


def digest(value):
    return hashlib.sha256(canonical(value, limit=131072)).hexdigest()


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw,
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        canonical(value, limit=131072)
        return value
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise ConnectorError("CONNECTOR_JSON_INVALID", 502) from None


def check_schema(schema, *, root=True, depth=0):
    canonical(schema, limit=16384)
    if type(schema) is not dict or depth > 8:
        raise ConnectorError("CONNECTOR_SCHEMA_UNSUPPORTED", 422)
    kind = schema.get("type")
    common = {"type", "title", "description", "default", "examples", "enum", "const", "$schema"}
    extras = {
        "object": {
            "properties",
            "required",
            "additionalProperties",
            "minProperties",
            "maxProperties",
        },
        "array": {"items", "minItems", "maxItems"},
        "string": {"minLength", "maxLength"},
        "number": {"minimum", "maximum"},
        "integer": {"minimum", "maximum"},
        "boolean": set(),
        "null": set(),
    }
    if type(kind) is not str or kind not in extras or set(schema) - common - extras[kind]:
        raise ConnectorError("CONNECTOR_SCHEMA_UNSUPPORTED", 422)
    if root and kind != "object":
        raise ConnectorError("CONNECTOR_SCHEMA_UNSUPPORTED", 422)
    if "$schema" in schema and schema["$schema"] != "https://json-schema.org/draft/2020-12/schema":
        raise ConnectorError("CONNECTOR_SCHEMA_UNSUPPORTED", 422)
    if "enum" in schema and (type(schema["enum"]) is not list or not schema["enum"]):
        raise ConnectorError("CONNECTOR_SCHEMA_UNSUPPORTED", 422)
    for key in ("minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties"):
        if key in schema and (type(schema[key]) is not int or not 0 <= schema[key] <= 65536):
            raise ConnectorError("CONNECTOR_SCHEMA_UNSUPPORTED", 422)
    for key in ("minimum", "maximum"):
        if key in schema and type(schema[key]) not in (int, float):
            raise ConnectorError("CONNECTOR_SCHEMA_UNSUPPORTED", 422)
    for low, high in (
        ("minimum", "maximum"),
        ("minLength", "maxLength"),
        ("minItems", "maxItems"),
        ("minProperties", "maxProperties"),
    ):
        if low in schema and high in schema and schema[low] > schema[high]:
            raise ConnectorError("CONNECTOR_SCHEMA_UNSUPPORTED", 422)
    if kind == "object":
        properties, required = schema.get("properties", {}), schema.get("required", [])
        if (
            type(properties) is not dict
            or len(properties) > 64
            or type(required) is not list
            or any(type(v) is not str for v in required)
            or len(set(required)) != len(required)
            or not set(required) <= set(properties)
            or schema.get("additionalProperties", False) is not False
        ):
            raise ConnectorError("CONNECTOR_SCHEMA_UNSUPPORTED", 422)
        for child in properties.values():
            check_schema(child, root=False, depth=depth + 1)
    if kind == "array":
        check_schema(schema.get("items"), root=False, depth=depth + 1)


def validate(schema, value):
    """Validate an admitted schema. Unknown properties are always rejected."""
    canonical(value)
    kind = schema["type"]
    types = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    if (kind == "number" and type(value) not in (int, float)) or (
        kind != "number" and type(value) is not types[kind]
    ):
        raise ConnectorError("CONNECTOR_ARGUMENT_INVALID", 422)
    if "const" in schema and canonical(value) != canonical(schema["const"]):
        raise ConnectorError("CONNECTOR_ARGUMENT_SCOPE", 403)
    if "enum" in schema and canonical(value) not in [canonical(v) for v in schema["enum"]]:
        raise ConnectorError("CONNECTOR_ARGUMENT_SCOPE", 403)
    for low, high, actual in (
        ("minLength", "maxLength", len(value) if kind == "string" else None),
        ("minItems", "maxItems", len(value) if kind == "array" else None),
        ("minProperties", "maxProperties", len(value) if kind == "object" else None),
        ("minimum", "maximum", value if kind in {"integer", "number"} else None),
    ):
        if actual is not None and (
            actual < schema.get(low, -1e101) or actual > schema.get(high, 1e101)
        ):
            raise ConnectorError("CONNECTOR_ARGUMENT_INVALID", 422)
    if kind == "object":
        properties = schema.get("properties", {})
        if set(value) - set(properties) or not set(schema.get("required", [])) <= set(value):
            raise ConnectorError("CONNECTOR_ARGUMENT_INVALID", 422)
        for key, child in value.items():
            validate(properties[key], child)
    if kind == "array":
        for child in value:
            validate(schema["items"], child)

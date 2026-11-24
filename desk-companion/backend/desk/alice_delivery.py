"""Presentation metadata from the same ordinary Session that writes Alice's reply."""

from pydantic_core import from_json

DELIVERIES = (
    "neutral",
    "celebrate",
    "comfort",
    "appreciate",
    "surprised",
    "amused",
    "curious",
    "encourage",
    "relieved",
    "bashful",
    "apologetic",
)
ANSWER_LIMIT = 8000
# A supplementary Unicode character can be represented as two JSON escape sequences.
WIRE_LIMIT = ANSWER_LIMIT * 12 + 256
TEXT_FORMAT = {
    "format": {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {
                "delivery": {"type": "string", "enum": list(DELIVERIES)},
                "message": {"type": "string"},
            },
            "required": ["delivery", "message"],
            "additionalProperties": False,
        },
    }
}
INSTRUCTIONS = (
    "\nReturn your normal answer in message. Choose delivery for how Alice responds to this "
    "particular exchange. Celebrate an actual success, comfort a disappointment, appreciate "
    "personal thanks, be amused by shared humor, or encourage an effort. Use curious or "
    "surprised only when the exchange calls for it. Use relieved when a specific worry has "
    "just been resolved, bashful for a warm personal compliment, and apologetic when you "
    "are acknowledging your own mistake. For routine tasks, mixed or ambiguous news, "
    "and results of tools, prefer neutral. Respect negation, quoted speech and who it happened to. "
    "Do not describe the gesture, label the user's feelings or alter the factual answer."
)


def read_delivery(raw: str, *, complete: bool) -> dict:
    if not raw.lstrip().startswith("{"):
        message, delivery = raw, None  # Existing plain-text responses and provider refusals.
    else:
        try:
            data = from_json(raw, allow_partial=False if complete else "trailing-strings")
        except ValueError:
            if complete:
                raise
            return {"message": ""}
        if "delivery" not in data:
            # A legacy answer can itself be JSON, including a "message" key.
            message, delivery = (raw if complete else ""), None
        else:
            message, delivery = data.get("message", ""), data.get("delivery")
    if (
        not isinstance(message, str)
        or len(message) > ANSWER_LIMIT
        or (complete and not message.strip())
    ):
        raise ValueError("Invalid visible Session answer")
    return {"message": message, **({"delivery": delivery} if delivery in DELIVERIES else {})}

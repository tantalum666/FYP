"""One-line JSON logs. Secret-bearing fields and query values are redacted."""

import json
import logging
import re
import sys

SECRET_KEYS = {
    "password",
    "api_key",
    "apikey",
    "token",
    "authorization",
    "secret",
    "cookie",
    "credential",
    "code",
    "state",
}
_QUERY = re.compile(
    r"(?i)(^|&)(password|api_key|apikey|token|code|secret|authorization|state|cookie)=([^&]*)"
)
_BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+=*")

logger = logging.getLogger("desk")
_configured = False


def redact_text(value: str) -> str:
    value = _QUERY.sub(lambda match: f"{match.group(1)}{match.group(2)}=[redacted]", value)
    return _BEARER.sub("Bearer [redacted]", value)


def redact(value):
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if str(key).lower() in SECRET_KEYS:
                redacted[key] = "[redacted]"
            elif str(key).lower() == "query" and isinstance(item, str):
                redacted[key] = redact_text(item)
            else:
                redacted[key] = redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def configure() -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    _configured = True


def log_event(event: str, **fields) -> None:
    configure()
    payload = {"event": event, **redact(fields)}
    logger.info(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str))

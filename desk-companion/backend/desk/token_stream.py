"""Pull the assistant message out of a partial JSON plan.

Providers stream raw JSON. The owner should see the message text as it grows,
not the braces. If the buffer is not that JSON shape, the caller keeps the
bytes and falls back to the finished plan.
"""


def extract_message(raw: str) -> str | None:
    """Decoded `message` so far.

    "" means the field has not started. None means the buffer is not a plan.
    """
    text = raw.lstrip()
    if not text:
        return ""
    if text[0] != "{":
        return None
    key = text.find('"message"')
    if key < 0:
        return ""
    rest = text[key + len('"message"') :].lstrip()
    if not rest:
        return ""
    if rest[0] != ":":
        return ""
    rest = rest[1:].lstrip()
    if not rest:
        return ""
    if rest[0] != '"':
        return None
    return _string_prefix(rest[1:])


def _string_prefix(body: str) -> str | None:
    out: list[str] = []
    index = 0
    while index < len(body):
        char = body[index]
        if char == '"':
            return "".join(out)
        if char == "\\":
            if index + 1 >= len(body):
                return "".join(out)
            nxt = body[index + 1]
            mapped = {
                '"': '"',
                "\\": "\\",
                "/": "/",
                "b": "\b",
                "f": "\f",
                "n": "\n",
                "r": "\r",
                "t": "\t",
            }.get(nxt)
            if mapped is not None:
                out.append(mapped)
                index += 2
                continue
            if nxt == "u":
                hexpart = body[index + 2 : index + 6]
                if len(hexpart) < 4:
                    return "".join(out)
                try:
                    out.append(chr(int(hexpart, 16)))
                except ValueError:
                    return None
                index += 6
                continue
            return None
        if ord(char) < 32:
            return None
        out.append(char)
        index += 1
    return "".join(out)

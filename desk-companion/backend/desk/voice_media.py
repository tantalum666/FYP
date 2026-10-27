"""Bounded JPEG frame validation. Images remain in memory and are never saved."""

import base64
import binascii

from .store import DomainError

MAX_IMAGE_BASE64 = 256 * 1024


def jpeg_image(value):
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_IMAGE_BASE64:
        raise DomainError("INVALID_VOICE_IMAGE", 422)
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise DomainError("INVALID_VOICE_IMAGE", 422) from None
    if len(raw) > 192 * 1024 or not raw.startswith(b"\xff\xd8") or not raw.endswith(b"\xff\xd9"):
        raise DomainError("INVALID_VOICE_IMAGE", 422)
    offset, dimensions = 2, None
    while offset < len(raw) - 2:
        if raw[offset] != 0xFF:
            raise DomainError("INVALID_VOICE_IMAGE", 422)
        while offset < len(raw) and raw[offset] == 0xFF:
            offset += 1
        if offset >= len(raw):
            break
        marker = raw[offset]
        offset += 1
        if marker == 0xDA:  # Compressed image data follows the start-of-scan header.
            break
        if marker in {0xD8, 0xD9, 0x00} or 0xD0 <= marker <= 0xD7:
            raise DomainError("INVALID_VOICE_IMAGE", 422)
        length = int.from_bytes(raw[offset : offset + 2], "big")
        if length < 2 or offset + length > len(raw):
            raise DomainError("INVALID_VOICE_IMAGE", 422)
        if marker in {0xC0, 0xC1, 0xC2}:
            if length < 8 or dimensions is not None:
                raise DomainError("INVALID_VOICE_IMAGE", 422)
            height = int.from_bytes(raw[offset + 3 : offset + 5], "big")
            width = int.from_bytes(raw[offset + 5 : offset + 7], "big")
            if not (1 <= min(width, height) <= 1080 and max(width, height) <= 1920):
                raise DomainError("INVALID_VOICE_IMAGE", 422)
            dimensions = (width, height)
        offset += length
    if dimensions is None:
        raise DomainError("INVALID_VOICE_IMAGE", 422)
    return raw

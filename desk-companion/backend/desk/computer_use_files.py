"""Fixed private slots for screen observations and browser continuation state."""

import os
import re

from .computer import exclusive_write, open_owner_directory


def write_file(directory, name, body):
    if not (
        name in {"receipt.json", "browser-state.json", "source-state.json", "cleanup-required"}
        or re.fullmatch(r"screen-[0-9]{1,2}\.png", name)
    ):
        raise ValueError("Unknown computer-use file slot")
    limit = 128000 if name == "receipt.json" else 2_000_000
    if len(body) > limit:
        raise ValueError("Computer evidence exceeds its bound")
    handle = open_owner_directory(directory)
    try:
        exclusive_write(handle, name, body)
    finally:
        os.close(handle)

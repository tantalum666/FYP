"""Fixed private slots for screen observations and browser continuation state."""

import os
import re

from .computer import exclusive_write, open_owner_directory


REFRESHABLE = {"browser-state.json", "owner-wall.json", "wall-evidence.json", "latest.json"}


def refresh_file(directory, name, body):
    """Replace one evidence file on the same job. Screens stay unique."""
    if name not in REFRESHABLE or len(body) > 2_000_000:
        raise ValueError("Unknown computer-use file slot")
    temporary = directory / f".{name}.new"
    with temporary.open("wb") as file:
        file.write(body)
        file.flush()
        os.fsync(file.fileno())
    temporary.replace(directory / name)
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def write_file(directory, name, body):
    if not (
        name
        in {
            "receipt.json",
            "browser-state.json",
            "source-state.json",
            "cleanup-required",
            "navigation.json",
            "owner-wall.json",
            "wall-evidence.json",
            "latest.json",
        }
        or re.fullmatch(r"screen-[0-9]{1,2}\.png", name)
    ):
        raise ValueError("Unknown computer-use file slot")
    limit = 2000 if name == "navigation.json" else 128000 if name == "receipt.json" else 2_000_000
    if len(body) > limit:
        raise ValueError("Computer evidence exceeds its bound")
    handle = open_owner_directory(directory)
    try:
        exclusive_write(handle, name, body)
    finally:
        os.close(handle)

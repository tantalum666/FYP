"""Explicit, private provider credential-file loading; no shell evaluation or output."""

import os
import re
import stat
from pathlib import Path


def _private_env_key(path: str, name: str, *, private_parent=True) -> str:
    target = Path(path).expanduser()
    if not target.is_absolute() or ".." in target.parts:
        raise ValueError("VOICE_CREDENTIALS_INVALID")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(target.anchor, flags)
    try:
        for part in target.parent.parts[1:]:
            child = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        parent = os.fstat(directory)
        if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) & (0o077 if private_parent else 0o022):
            raise ValueError("VOICE_CREDENTIALS_INVALID")
        fd = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        with os.fdopen(fd, "rb") as file:
            info = os.fstat(file.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size > 8192
            ):
                raise ValueError("VOICE_CREDENTIALS_INVALID")
            values = [
                line.partition("=")[2]
                for line in file.read().decode("utf-8").splitlines()
                if line.startswith(name + "=")
            ]
            if len(values) != 1 or not re.fullmatch(r"[A-Za-z0-9_.-]{16,512}", values[0]):
                raise ValueError("VOICE_CREDENTIALS_INVALID")
            return values[0]
    finally:
        os.close(directory)


def qwen_key(path: str) -> str:
    return _private_env_key(path, "DASHSCOPE_API_KEY")


def openai_key(path: str) -> str:
    return _private_env_key(path, "OPENAI_API_KEY", private_parent=False)

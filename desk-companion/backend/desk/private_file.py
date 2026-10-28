"""Create secret files at mode 0600 before any bytes are written.

`Path.write_text` creates the file as 0666 masked by umask, then chmod. With umask 0
that leaves a window where another process of the same user can read the password.
"""

import os
from pathlib import Path

_CREATE = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)


def write_private(path, payload: str | bytes) -> None:
    path = Path(path)
    data = payload.encode() if isinstance(payload, str) else payload
    fd = os.open(path, _CREATE, 0o600)
    try:
        os.write(fd, data)
    except BaseException:
        os.close(fd)
        path.unlink(missing_ok=True)
        raise
    os.close(fd)
    os.chmod(path, 0o600)


def reserve_private(path) -> None:
    """Create an empty file at 0600 so SQLite does not invent a wider mode."""
    path = Path(path)
    try:
        fd = os.open(path, _CREATE, 0o600)
    except FileExistsError:
        return
    os.close(fd)
    os.chmod(path, 0o600)

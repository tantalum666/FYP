"""A private app-only browser profile with password saving disabled.

The local display trusts the OS user and stores application grants in FYP's vault.
It must not adopt an ordinary browser profile or require a GUI keyring on boot.
"""

import json
import os
from pathlib import Path
import sys
import tempfile


def prepare(root: Path):
    if not root.is_absolute() or root.name != "kiosk" or root.is_symlink():
        raise ValueError("Use the dedicated kiosk profile")
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    root.chmod(0o700)
    default = root / "Default"
    if default.is_symlink():
        raise ValueError("Invalid kiosk profile")
    default.mkdir(mode=0o700, exist_ok=True)
    target = default / "Preferences"
    if target.is_symlink():
        raise ValueError("Invalid kiosk preferences")
    data = json.loads(target.read_text()) if target.exists() else {}
    data["credentials_enable_service"] = False
    data["credentials_enable_autosignin"] = False
    data.setdefault("profile", {})["password_manager_enabled"] = False
    descriptor, name = tempfile.mkstemp(prefix=".preferences-", dir=default)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w") as file:
            json.dump(data, file)
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return root


if __name__ == "__main__":
    prepare(Path(sys.argv[1]))

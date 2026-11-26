"""Enroll the two Nuitée sandbox keys on an owner-operated desk."""

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
import tempfile

from desk.flight_booking.nuitee_sandbox import valid_keys
from desk.vault import Vault


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--replace", action="store_true", help="replace an existing sandbox profile"
    )
    args = parser.parse_args()
    os.umask(0o077)
    directory = args.directory.expanduser().absolute()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (
        directory.resolve() != directory
        or directory.stat().st_mode & 0o077
        or directory.stat().st_uid != os.getuid()
    ):
        raise SystemExit("Choose an owner-only directory (0700) outside the repository.")
    target = directory / "account.sealed"
    for path in (target, directory / "vault.key"):
        if path.is_symlink() or (
            path.exists()
            and (
                not path.is_file()
                or path.stat().st_uid != os.getuid()
                or path.stat().st_mode & 0o077
            )
        ):
            raise SystemExit("Existing credential files must be owner-only regular files.")
    if target.exists() and not args.replace:
        raise SystemExit("A profile already exists. Use --replace only when rotating its keys.")
    bundle = {
        "private": getpass("Sandbox API key: ").strip(),
        "public": getpass("Sandbox Stripe publishable key: ").strip(),
    }
    if not valid_keys(bundle):
        raise SystemExit("Expected a sand_ API key and a pk_test_ payment key.")
    vault = Vault(directory)
    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as temp:
        temp.write(vault.encrypt(json.dumps(bundle)).encode())
    staged = Path(temp.name)
    try:
        if args.replace:
            os.replace(staged, target)
        else:
            os.link(staged, target)
    finally:
        staged.unlink(missing_ok=True)
    print("Sandbox profile saved. Set DESK_NUITEE_SANDBOX_PROFILE to its directory.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build a pinned owner-side SSH route from a private relay configuration."""

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex


def proxy_command(path):
    path = Path(path)
    info = path.lstat()
    if path.is_symlink() or not path.is_file() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("Use an owner-private relay configuration")
    config = json.loads(path.read_text())
    expected = {"version", "host", "port", "user", "host_key_alias", "known_hosts_file", "remote_port"}
    if set(config) != expected or type(config["version"]) is not int or config["version"] != 1:
        raise ValueError("Unsupported owner relay configuration")
    host = ipaddress.IPv4Address(config["host"])
    if not host.is_global:
        raise ValueError("The selected VPS must have a public IPv4 address")
    for key in ("port", "remote_port"):
        if type(config[key]) is not int or not 1 <= config[key] <= 65535:
            raise ValueError("Invalid relay port")
    if not isinstance(config["user"], str) or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", config["user"]):
        raise ValueError("Invalid relay username")
    alias = config["host_key_alias"]
    if not isinstance(alias, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", alias):
        raise ValueError("Invalid pinned VPS alias")
    known = Path(config["known_hosts_file"])
    # OpenSSH expands tokens in ProxyCommand itself, before a shell sees quoting.
    if not known.is_absolute() or known.is_symlink() or not known.is_file() or "%" in str(known):
        raise ValueError("Use an existing absolute VPS known-hosts file without SSH tokens")
    return shlex.join([
        "/usr/bin/ssh", "-F", "/dev/null", "-a", "-T",
        "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
        "-o", "HostKeyAlias=" + alias, "-o", "UserKnownHostsFile=" + str(known),
        "-o", "UpdateHostKeys=no", "-o", "ProxyCommand=none",
        "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3", "-o", "LogLevel=ERROR",
        "-p", str(config["port"]), "-W", "127.0.0.1:" + str(config["remote_port"]),
        config["user"] + "@" + str(host),
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    try:
        print(proxy_command(args.config))
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise SystemExit("Cannot load the private owner relay: " + str(error)) from None


if __name__ == "__main__":
    main()

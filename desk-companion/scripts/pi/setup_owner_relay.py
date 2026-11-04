#!/usr/bin/python3
"""Optional owner-hosted reverse SSH; keeps Pi identity/auth and app listeners intact."""

import base64
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import socket
import subprocess
import time

CONFIG = Path("/etc/desk-owner-relay.json")
ROOT = Path("/home/desk/.config/desk-companion/owner-relay")
KEY = ROOT / "id_ed25519"
KNOWN = ROOT / "known_hosts"
SCRIPT = "/usr/local/lib/desk-owner-relay-setup.py"
UNIT_NAME = "desk-owner-relay.service"
UNIT = Path("/etc/systemd/system") / UNIT_NAME
BOOT_STATUS = Path("/boot/firmware/desk-owner-relay-status.json")
HOST_ALIAS = "desk-owner-relay-vps"


def validate(config):
    host = ipaddress.ip_address(config["host"])
    if host.is_loopback or host.is_multicast or host.is_unspecified or "%" in str(host):
        raise ValueError("Select the explicit relay host address")
    if not re.fullmatch(r"fyp-[a-z0-9-]{1,24}", config["user"]):
        raise ValueError("A dedicated FYP relay user is required")
    for key, minimum in [("port", 1), ("remote_port", 1024)]:
        value = config[key]
        if type(value) is not int or not minimum <= value <= 65535:
            raise ValueError("Invalid relay port")
    parts = config["server_host_key"].split()
    if len(parts) != 2 or parts[0] != "ssh-ed25519" or "\n" in config["server_host_key"]:
        raise ValueError("One pinned Ed25519 server host key is required")
    decoded = base64.b64decode(parts[1], validate=True)
    if len(decoded) != 51 or decoded[:19] != b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20":
        raise ValueError("Invalid Ed25519 host key")


def private_file(path):
    path = Path(path)
    info = path.lstat()
    if (
        path.is_symlink()
        or not path.is_file()
        or info.st_mode & 0o077
        or info.st_uid != os.getuid()
    ):
        raise ValueError("Relay input must be an owner-private regular file")
    return path.read_text()


def seed_files(bundle_path, trial_id):
    bundle = json.loads(private_file(bundle_path))
    config = {
        key: bundle[key] for key in ("host", "port", "user", "remote_port", "server_host_key")
    }
    validate(config)
    config["trial_id"] = trial_id
    private_key = private_file(bundle["private_key_file"])
    # Validate with the actual SSH parser; never expose private-key contents or prompts.
    parsed = subprocess.run(
        ["ssh-keygen", "-y", "-P", "", "-f", bundle["private_key_file"]],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if parsed.returncode or not parsed.stdout.startswith("ssh-ed25519 "):
        raise ValueError("A usable dedicated Ed25519 relay key is required")
    return [
        (str(CONFIG), json.dumps(config) + "\n", "0600"),
        (str(KEY), private_key, "0600"),
        (str(KNOWN), HOST_ALIAS + " " + config["server_host_key"] + "\n", "0600"),
        (SCRIPT, Path(__file__).read_text(), "0700"),
    ]


def service_text(config):
    validate(config)
    command = [
        "/usr/bin/ssh",
        "-N",
        "-T",
        "-a",
        "-F",
        "/dev/null",
        "-i",
        str(KEY),
        "-p",
        str(config["port"]),
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "IdentityAgent=none",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "UserKnownHostsFile=" + str(KNOWN),
        "-o",
        "HostKeyAlias=" + HOST_ALIAS,
        "-o",
        "UpdateHostKeys=no",
        "-o",
        "ProxyCommand=none",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ServerAliveInterval=20",
        "-o",
        "ServerAliveCountMax=3",
        "-R",
        f"127.0.0.1:{config['remote_port']}:127.0.0.1:22",
        config["user"] + "@" + config["host"],
    ]
    return f"""[Unit]
Description=Desk Companion owner-hosted SSH relay
Wants=network-online.target
After=network-online.target ssh.service
StartLimitIntervalSec=0
[Service]
Type=simple
User=desk
Group=desk
ExecStart={shlex.join(command)}
Restart=on-failure
RestartSec=30
TimeoutStopSec=10
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
[Install]
WantedBy=multi-user.target
"""


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=20, check=True)


def install(config, access):
    validate(config)
    if not Path("/var/lib/desk-companion-provisioned").is_file():
        raise RuntimeError("Existing paired Pi installation required")
    access.check_owner_auth()
    owner = pwd.getpwnam("desk")
    for path in (ROOT, KEY, KNOWN):
        if path.is_symlink() or not path.exists():
            raise ValueError("Relay seed files are missing or unsafe")
        os.chown(path, owner.pw_uid, owner.pw_gid)
        path.chmod(0o700 if path.is_dir() else 0o600)
    access.atomic_write(UNIT, service_text(config), 0o644)
    run("systemctl", "daemon-reload")
    run("systemctl", "enable", "--now", UNIT_NAME)
    state = {
        "trial_id": config["trial_id"],
        "utc_unix": time.time(),
        "phase": "relay_service_started",
        "authenticated_pi_access_verified": False,
    }
    try:
        with socket.create_connection((config["host"], config["port"]), timeout=4):
            state["vps_tcp"] = "reachable"
    except OSError as error:
        state["vps_tcp"] = type(error).__name__
    time.sleep(12)
    state["unit_state"] = run(
        "systemctl",
        "show",
        UNIT_NAME,
        "-p",
        "ActiveState",
        "-p",
        "SubState",
        "-p",
        "ExecMainStatus",
        "-p",
        "NRestarts",
    ).stdout.splitlines()
    journal = run("journalctl", "-u", UNIT_NAME, "-n", "12", "--no-pager", "-o", "cat").stdout
    state["error_hints"] = [
        hint
        for hint in (
            "Connection timed out",
            "Network is unreachable",
            "Permission denied",
            "Host key verification failed",
            "remote port forwarding failed",
            "Connection refused",
        )
        if hint in journal
    ]
    access.atomic_write(BOOT_STATUS, json.dumps(state) + "\n")


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run only on the paired Pi as root")
    spec = importlib.util.spec_from_file_location(
        "desk_access", "/usr/local/lib/desk-classroom-access.py"
    )
    access = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(access)
    config = json.loads(CONFIG.read_text())
    try:
        install(config, access)
    except Exception as error:
        access.atomic_write(
            BOOT_STATUS,
            json.dumps(
                {
                    "trial_id": config.get("trial_id"),
                    "phase": "relay_setup_failed",
                    "error_type": type(error).__name__,
                    "utc_unix": time.time(),
                }
            )
            + "\n",
        )
        raise SystemExit("Owner relay setup failed; inspect nonsecret boot status.") from None


if __name__ == "__main__":
    main()

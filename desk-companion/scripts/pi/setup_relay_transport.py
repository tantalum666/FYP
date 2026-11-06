#!/usr/bin/python3
"""Optional fixed-destination 443 transport; no TUN, DNS or general proxy changes."""

import gzip
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import platform
import pwd
import re
import socket
import struct
import subprocess
import tempfile
import time
import uuid

SCRIPT = "/usr/local/lib/desk-relay-transport-setup.py"
CONFIG = Path("/etc/desk-relay-transport.json")
ARCHIVE_NAME = "desk-relay-mihomo.gz"
BINARY = Path("/opt/desk-companion-relay/mihomo")
USER_DIR = Path("/home/desk/.config/desk-companion/owner-relay")
RUNTIME_CONFIG = USER_DIR / "transport.json"
DATA = Path("/home/desk/.local/state/desk-relay-transport")
UNIT_NAME = "desk-relay-transport.service"
UNIT = Path("/etc/systemd/system") / UNIT_NAME
STATUS = Path("/boot/firmware/desk-relay-transport-status.json")
LOCAL_PORT = 22422


def validate(config):
    host = str(ipaddress.IPv4Address(config["relay_host"]))
    runtime = config["runtime_config"]
    required = {
        "port": 0,
        "socks-port": 0,
        "mixed-port": 0,
        "allow-lan": False,
        "bind-address": "127.0.0.1",
        "mode": "rule",
        "log-level": "error",
        "ipv6": False,
        "tun": {"enable": False},
        "dns": {"enable": False},
        "external-controller": "",
        "external-controller-unix": "",
        "find-process-mode": "off",
        "geo-auto-update": False,
        "profile": {"store-selected": False, "store-fake-ip": False},
        "rules": ["MATCH,REJECT"],
    }
    if set(runtime) != set(required) | {"proxies", "tunnels"}:
        raise ValueError("Unexpected relay transport setting")
    if any(runtime.get(key) != value for key, value in required.items()):
        raise ValueError("Transport must remain local, fixed-destination and non-TUN")
    if len(runtime["proxies"]) != 1:
        raise ValueError("Exactly one owned transport node is required")
    node = runtime["proxies"][0]
    allowed = {
        "name",
        "type",
        "server",
        "port",
        "uuid",
        "network",
        "tls",
        "flow",
        "servername",
        "client-fingerprint",
        "reality-opts",
        "udp",
        "packet-encoding",
    }
    if not set(node) <= allowed or node.get("name") != "FYP-RELAY" or node.get("type") != "vless":
        raise ValueError("Unexpected transport node")
    if node.get("server") != host or node.get("port") != 443 or node.get("tls") is not True:
        raise ValueError("Use only the selected owned VPS on encrypted port443")
    if node.get("network", "tcp") != "tcp" or not isinstance(node.get("reality-opts"), dict):
        raise ValueError("A tested TCP Reality node is required")
    if not set(node["reality-opts"]) <= {
        "public-key",
        "short-id",
        "support-x25519mlkem768",
    } or not node["reality-opts"].get("public-key"):
        raise ValueError("Only the client Reality public parameters are accepted")
    if (
        "support-x25519mlkem768" in node["reality-opts"]
        and type(node["reality-opts"]["support-x25519mlkem768"]) is not bool
    ):
        raise ValueError("Unexpected Reality capability flag")
    if node.get("packet-encoding", "") not in ("", "xudp", "packetaddr"):
        raise ValueError("Unexpected packet encoding")
    uuid.UUID(node["uuid"])
    expected = [
        {
            "network": ["tcp"],
            "address": f"127.0.0.1:{LOCAL_PORT}",
            "target": host + ":22",
            "proxy": "FYP-RELAY",
        }
    ]
    if runtime["tunnels"] != expected:
        raise ValueError("Transport may forward only loopback to the owned VPS SSH")
    if config["archive_name"] != ARCHIVE_NAME:
        raise ValueError("Unexpected offline archive path")
    for name in ["archive_sha256", "binary_sha256"]:
        if not re.fullmatch("[0-9a-f]{64}", config[name]):
            raise ValueError("Pinned artifact digests are required")
    if (
        type(config["binary_size"]) is not int
        or not 64 <= config["binary_size"] <= 128 * 1024 * 1024
    ):
        raise ValueError("Invalid bounded transport binary size")


def seed_files(bundle, trial_id, relay_host):
    from setup_owner_relay import private_file

    manifest = json.loads(private_file(bundle["transport_manifest_file"]))
    runtime = json.loads(private_file(bundle["transport_config_file"]))
    config = {
        "trial_id": trial_id,
        "relay_host": relay_host,
        "runtime_config": runtime,
        "archive_name": ARCHIVE_NAME,
        **{k: manifest[k] for k in ["archive_sha256", "binary_sha256", "binary_size", "version"]},
    }
    validate(config)
    return [
        (str(CONFIG), json.dumps(config) + "\n", "0600"),
        (SCRIPT, Path(__file__).read_text(), "0700"),
    ]


def archive_input(bundle):
    from setup_owner_relay import private_file

    manifest = json.loads(private_file(bundle["transport_manifest_file"]))
    path = Path(manifest["archive_file"])
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Invalid transport archive")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest["archive_sha256"]:
        raise ValueError("Transport archive digest mismatch")
    return content


def install_binary(config, archive, target=BINARY):
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("Invalid offline archive")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != config["archive_sha256"]:
        raise ValueError("Offline archive integrity failed")
    if target.is_symlink():
        raise ValueError("Transport binary must not be a symlink")
    if (
        target.is_file()
        and hashlib.sha256(target.read_bytes()).hexdigest() == config["binary_sha256"]
    ):
        target.chmod(0o755)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".transport-", dir=target.parent)
    try:
        digest = hashlib.sha256()
        size = 0
        header = b""
        with os.fdopen(fd, "wb") as output, gzip.open(archive, "rb") as source:
            while chunk := source.read(1024 * 1024):
                if not header:
                    header = chunk[:64]
                size += len(chunk)
                if size > config["binary_size"]:
                    raise ValueError("Oversized transport binary")
                digest.update(chunk)
                output.write(chunk)
            if size != config["binary_size"] or digest.hexdigest() != config["binary_sha256"]:
                raise ValueError("Transport binary integrity failed")
            if header[:6] != b"\x7fELF\x02\x01" or struct.unpack("<H", header[18:20])[0] != 183:
                raise ValueError("Transport is not a Linux AArch64 binary")
            output.flush()
            os.fchmod(output.fileno(), 0o755)
            os.fsync(output.fileno())
        os.replace(temp, target)
        os.sync()
        if hashlib.sha256(target.read_bytes()).hexdigest() != config["binary_sha256"]:
            raise OSError("Transport readback mismatch")
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def unit_text():
    return f"""[Unit]
Description=Fixed owner SSH transport over the existing encrypted VPS connection
Wants=network-online.target
After=network-online.target
[Service]
Type=simple
User=desk
Group=desk
ExecStart={BINARY} -d {DATA} -f {RUNTIME_CONFIG}
Restart=on-failure
RestartSec=15
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths={DATA}
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK
[Install]
WantedBy=multi-user.target
"""


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30)


def install(config, access):
    validate(config)
    if platform.machine() != "aarch64" or not Path("/var/lib/desk-companion-provisioned").is_file():
        raise RuntimeError("Existing paired ARM64 Pi required")
    access.check_owner_auth()
    install_binary(config, Path("/boot/firmware") / ARCHIVE_NAME)
    owner = pwd.getpwnam("desk")
    if DATA.is_symlink():
        raise ValueError("Unexpected transport directory symlink")
    run("runuser", "-u", "desk", "--", "mkdir", "-p", str(DATA))
    for directory in [USER_DIR, DATA]:
        if directory.is_symlink():
            raise ValueError("Unexpected transport directory symlink")
        directory.mkdir(parents=True, exist_ok=True)
        os.chown(directory, owner.pw_uid, owner.pw_gid)
        directory.chmod(0o700)
    access.atomic_write(RUNTIME_CONFIG, json.dumps(config["runtime_config"]) + "\n")
    os.chown(RUNTIME_CONFIG, owner.pw_uid, owner.pw_gid)
    run(
        "runuser", "-u", "desk", "--", str(BINARY), "-t", "-d", str(DATA), "-f", str(RUNTIME_CONFIG)
    )
    access.atomic_write(UNIT, unit_text(), 0o644)
    run("systemctl", "daemon-reload")
    run("systemctl", "enable", "--now", UNIT_NAME)
    state = {
        "trial_id": config["trial_id"],
        "phase": "transport_configured",
        "utc_unix": time.time(),
        "binary_sha256": config["binary_sha256"],
        "global_proxy_or_routes_changed": False,
        "authenticated_vps": False,
    }
    time.sleep(2)
    try:
        with socket.create_connection(("127.0.0.1", LOCAL_PORT), timeout=3) as peer:
            peer.settimeout(8)
            state["ssh_banner_observed"] = peer.recv(256).startswith(b"SSH-")
    except OSError as error:
        state["transport_error_type"] = type(error).__name__
    access.atomic_write(STATUS, json.dumps(state) + "\n")


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
            STATUS,
            json.dumps(
                {
                    "trial_id": config.get("trial_id"),
                    "phase": "transport_setup_failed",
                    "error_type": type(error).__name__,
                    "utc_unix": time.time(),
                }
            )
            + "\n",
        )
        raise SystemExit("Fixed relay transport setup failed; inspect boot status.") from None


if __name__ == "__main__":
    main()

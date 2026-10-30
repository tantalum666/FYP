#!/usr/bin/python3
"""Portable Pi networking: home/classroom Wi-Fi and wired DHCP.

Run on the existing paired Pi. Never recreate users/keys, alter app data, or
publish the app/VNC. The owned SSH guard follows admitted, connected LANs.
"""

import argparse
import fcntl
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import time

CONFIG = Path("/etc/desk-network-policy.json")
SCRIPT = "/usr/local/lib/desk-network-access.py"
STATE = Path("/var/lib/desk-companion/network-status.json")
BOOT_STATE = Path("/boot/firmware/desk-network-status.json")
LOCK = Path("/run/desk-network-guard.lock")
HOME_UUID = "bda2a174-f4d8-4b9a-a397-04b3094eda80"
WIRED_UUID = "927041fb-75ab-4d5d-a4d5-cf5e0280c708"
CLASSROOM_UUID = "c3a1aa85-7e29-4d91-9e97-6733a2c20226"
STUDENT_UUID = "c0a12d72-834c-4b80-b454-70f9adac9137"
HALLS_UUID = "6285ca25-f2bd-48cf-a04c-18f70748d405"
PROFILE_ROOT = Path("/etc/NetworkManager/system-connections")


def helper():
    spec = importlib.util.spec_from_file_location(
        "desk_existing_access", "/usr/local/lib/desk-classroom-access.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(*args, timeout=12, check=True, **kwargs):
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=check,
        env={**os.environ, "LC_ALL": "C"},
        **kwargs,
    )


def private_lan(value):
    network = ipaddress.IPv4Network(value, strict=False)
    ranges = [ipaddress.IPv4Network(v) for v in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    if network.prefixlen < 20 or not any(network.subnet_of(v) for v in ranges):
        raise ValueError("Only directly connected private /20 or smaller LANs are admitted")
    return str(network)


def admitted_networks(interfaces, active):
    """Ignore down, public, link-local, oversized and unselected Wi-Fi networks."""
    result = []
    for interface in interfaces:
        name = interface.get("ifname")
        if name not in ("eth0", "wlan0") or "LOWER_UP" not in interface.get("flags", []):
            continue
        if name == "wlan0" and active.get(name) not in (HOME_UUID, CLASSROOM_UUID, STUDENT_UUID):
            continue
        for address in interface.get("addr_info", []):
            if address.get("family") != "inet" or address.get("scope") != "global":
                continue
            try:
                subnet = private_lan(f"{address['local']}/{address['prefixlen']}")
            except (KeyError, ValueError, TypeError):
                continue
            if (name, subnet) not in result:
                result.append((name, subnet))
    return sorted(result)


def rules_for(networks):
    admitted = []
    for name, subnet in networks:
        if name not in ("eth0", "wlan0"):
            raise ValueError("Unexpected interface")
        admitted.append(
            f'    tcp dport 22 iifname "{name}" ip saddr {private_lan(subnet)} counter accept\n'
        )
    return (
        """table inet desk_usb_ssh {
  chain input {
    type filter hook input priority -5; policy accept;
    tcp dport 22 iifname "lo" counter accept
    tcp dport 22 iifname "usb0" counter accept
"""
        + "".join(sorted(set(admitted)))
        + """    tcp dport 22 counter drop
  }
}
"""
    )


def network_state():
    interfaces = json.loads(run("ip", "-j", "-4", "address", "show").stdout)
    active = {}
    for name in ("eth0", "wlan0"):
        reply = run("nmcli", "-g", "GENERAL.CON-UUID", "device", "show", name, check=False)
        active[name] = reply.stdout.strip() if reply.returncode == 0 else None
    return interfaces, active


def apply_guard(access):
    # Dispatcher and boot invocations serialize only local guard work, never Wi-Fi activation.
    with LOCK.open("w") as lock:
        os.chmod(LOCK, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        access.check_owner_auth()
        interfaces, active = network_state()
        networks = admitted_networks(interfaces, active)
        rules = rules_for(networks)
        previous = run("nft", "list", "table", "inet", "desk_usb_ssh", check=False)
        if previous.returncode and "No such file or directory" not in previous.stderr:
            raise RuntimeError("Cannot inspect the owned firewall table")
        batch = ("delete table inet desk_usb_ssh\n" if previous.returncode == 0 else "") + rules
        run("nft", "--check", "-f", "-", input=batch)
        run("nft", "-f", "-", input=batch)
        access.atomic_write(access.GUARD, rules)
    return networks


def public_status(policy, phase, **extra):
    interfaces, active = network_state()
    addresses = [
        {
            "name": i["ifname"],
            "ipv4": [a["local"] for a in i.get("addr_info", []) if a.get("family") == "inet"],
        }
        for i in interfaces
        if i.get("ifname") in ("eth0", "wlan0", "usb0")
    ]
    return {
        "trial_id": policy["trial_id"],
        "phase": phase,
        "utc_unix": time.time(),
        "interfaces": addresses,
        "active_profiles": active,
        "key_only_ssh": True,
        "app_and_vnc": "unchanged_loopback",
        **extra,
    }


def save_status(access, state):
    for path in (STATE, BOOT_STATE):
        access.atomic_write(path, json.dumps(state) + "\n")


def notify_owner(policy, state):
    host = ipaddress.IPv4Address(policy["owner_host"])
    private_lan(str(host) + "/32")
    payload = json.dumps(state).encode()
    if len(payload) > 4096:
        raise ValueError("Diagnostic packet too large")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(payload, (str(host), policy.get("owner_port", 8892)))


def install(policy, access):
    if not Path("/var/lib/desk-companion-provisioned").is_file():
        raise RuntimeError("An existing Desk Companion installation is required")
    access.check_owner_auth()
    for path in (access.GUARD, access.UNIT):
        backup = path.with_name(path.name + ".before-portable-network")
        if path.exists() and not backup.exists():
            access.atomic_write(backup, path.read_text())
    access.atomic_write(
        access.UNIT,
        f"""[Unit]
Description=Desk Companion owner-key SSH on connected admitted LANs
After=NetworkManager.service
Before=ssh.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {SCRIPT} --guard
RemainAfterExit=yes
""",
        0o644,
    )
    access.atomic_write(
        Path("/etc/NetworkManager/dispatcher.d/70-desk-network-guard"),
        f"""#!/bin/sh
case "$1:$2" in
  eth0:up|eth0:down|eth0:dhcp4-change|eth0:reapply|wlan0:up|wlan0:down|wlan0:dhcp4-change|wlan0:reapply)
    exec /usr/bin/python3 {SCRIPT} --guard ;;
esac
exit 0
""",
        0o700,
    )
    run("systemctl", "daemon-reload")
    apply_guard(access)
    run("systemctl", "enable", "--now", "ssh.service")
    for name in ("FYP-Home", "FYP-Wired"):
        path = PROFILE_ROOT / (name + ".nmconnection")
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise RuntimeError("Private root-owned connection profile required")
        run("nmcli", "connection", "load", str(path))
    # Keep old credentials for manual diagnosis; stop the failed dorm Wi-Fi trials.
    known = set(run("nmcli", "-t", "-f", "UUID", "connection", "show").stdout.splitlines())
    for identifier in (STUDENT_UUID, HALLS_UUID):
        if identifier in known:
            run("nmcli", "connection", "modify", identifier, "connection.autoconnect", "no")
    if CLASSROOM_UUID in known:
        run(
            "nmcli",
            "connection",
            "modify",
            CLASSROOM_UUID,
            "connection.autoconnect",
            "yes",
            "ipv4.route-metric",
            "600",
            "ipv6.route-metric",
            "600",
        )
    country = policy.get("country", "CN")
    if country not in ("CN", "HK"):
        raise ValueError("Select an explicit supported location")
    country_result = run(
        "raspi-config", "nonint", "do_wifi_country", country, check=False, timeout=20
    )
    run("rfkill", "unblock", "wifi")
    run("nmcli", "radio", "wifi", "on")
    save_status(
        access, public_status(policy, "profiles_loaded", country_exit=country_result.returncode)
    )
    try:
        has_carrier = Path("/sys/class/net/eth0/carrier").read_text().strip() == "1"
    except OSError:
        has_carrier = False
    if has_carrier:
        run(
            "nmcli", "--wait", "30", "connection", "up", "uuid", WIRED_UUID, timeout=35, check=False
        )
    home = run(
        "nmcli", "--wait", "40", "connection", "up", "uuid", HOME_UUID, timeout=45, check=False
    )
    for _ in range(30):
        admitted = apply_guard(access)
        state = public_status(
            policy,
            "network_ready" if admitted else "waiting_for_network",
            home_activation_exit=home.returncode,
            country_exit=country_result.returncode,
            allowed_lans=admitted,
            classroom_wifi_retained=CLASSROOM_UUID in known,
        )
        save_status(access, state)
        try:
            notify_owner(policy, state)
        except OSError:
            pass
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guard", action="store_true")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Run only as root on the paired Pi")
    access = helper()
    if args.guard:
        apply_guard(access)
        return
    policy = json.loads(CONFIG.read_text())
    try:
        install(policy, access)
    except Exception as error:
        state = {
            "trial_id": policy.get("trial_id"),
            "phase": "setup_failed",
            "error_type": type(error).__name__,
            "utc_unix": time.time(),
        }
        save_status(access, state)
        raise SystemExit("Network setup stopped; inspect the nonsecret boot status.") from None


if __name__ == "__main__":
    main()

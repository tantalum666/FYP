#!/usr/bin/python3
"""Durably restore this paired Pi's network seed and resume an interrupted setup.

Embedded as nonsecret Python in cloud-init bootcmd/runcmd. Credentials are read
from the mounted seed, never from command arguments. No whole-OS provisioning.
"""

import hashlib
import errno
import http.client
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

BOOT = Path("/boot/firmware")
INSTANCE_ROOT = Path("/var/lib/cloud/instances")
CURRENT_INSTANCE = Path("/var/lib/cloud/instance")
STATE = Path("/var/lib/desk-companion/network-recovery-completed.json")
STATUS = BOOT / "desk-network-bootstrap-status.json"
NETWORK = "/usr/local/lib/desk-network-access.py"
RELAY = "/usr/local/lib/desk-owner-relay-setup.py"
TRANSPORT = "/usr/local/lib/desk-relay-transport-setup.py"
POLICY = "/etc/desk-network-policy.json"
CORE = {
    NETWORK: "0700",
    POLICY: "0600",
    "/etc/NetworkManager/system-connections/FYP-Home.nmconnection": "0600",
    "/etc/NetworkManager/system-connections/FYP-Wired.nmconnection": "0600",
}
RELAY_FILES = {
    RELAY: "0700",
    "/etc/desk-owner-relay.json": "0600",
    "/home/desk/.config/desk-companion/owner-relay/id_ed25519": "0600",
    "/home/desk/.config/desk-companion/owner-relay/known_hosts": "0600",
}
TRANSPORT_FILES = {TRANSPORT: "0700", "/etc/desk-relay-transport.json": "0600"}


def atomic_write(path, content, mode=0o600):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Managed recovery files must not be symlinks")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".desk-recovery-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            try:
                os.fsync(directory)
            except OSError as error:
                if error.errno not in (errno.EINVAL, errno.ENOTSUP):
                    raise
                os.sync()
        finally:
            os.close(directory)
        if path.read_bytes() != content:
            raise OSError("Recovery file readback mismatch")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_plan(boot=BOOT):
    document = json.loads((boot / "user-data").read_text().split("\n", 1)[1])
    entries = document["write_files"]
    paths = [row["path"] for row in entries]
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate recovery path")
    if TRANSPORT in paths and RELAY not in paths:
        raise ValueError("Fixed transport requires the owner relay")
    expected = {
        **CORE,
        **(RELAY_FILES if RELAY in paths else {}),
        **(TRANSPORT_FILES if TRANSPORT in paths else {}),
    }
    if set(paths) != set(expected):
        raise ValueError("Recovery seed contains an unexpected path")
    for row in entries:
        if (
            row.get("owner") != "root:root"
            or row.get("permissions") != expected[row["path"]]
            or not isinstance(row.get("content"), str)
            or not row["content"]
        ):
            raise ValueError("Recovery payload is empty or has unexpected permissions")
    policy = json.loads(next(row["content"] for row in entries if row["path"] == POLICY))
    trial = policy["trial_id"]
    if not re.fullmatch(r"[0-9a-f]{32}", trial):
        raise ValueError("Invalid recovery instance")
    if (
        json.loads((boot / "meta-data").read_text())["instance-id"]
        != "desk-portable-network-" + trial
    ):
        raise ValueError("Recovery seed/instance mismatch")
    digest = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    relay_host = None
    if RELAY in paths:
        relay = json.loads(
            next(row["content"] for row in entries if row["path"] == "/etc/desk-owner-relay.json")
        )
        address = ipaddress.ip_address(relay["host"])
        if address.is_loopback or address.is_multicast or address.is_unspecified:
            raise ValueError("Invalid owner relay diagnostic host")
        relay_host = str(address)
    return {
        "trial_id": trial,
        "digest": digest,
        "entries": entries,
        "relay_host": relay_host,
        "commands": [[sys.executable, NETWORK]]
        + ([[sys.executable, TRANSPORT]] if TRANSPORT in paths else [])
        + ([[sys.executable, RELAY]] if RELAY in paths else []),
    }


def restore_files(plan, root=Path("/")):
    for row in plan["entries"]:
        target = root / row["path"].lstrip("/")
        wanted = row["content"].encode()
        if target.is_symlink():
            raise ValueError("Managed recovery files must not be symlinks")
        if not target.is_file() or target.read_bytes() != wanted:
            atomic_write(target, wanted, int(row["permissions"], 8))
        else:
            target.chmod(int(row["permissions"], 8))
    for row in plan["entries"]:
        if (root / row["path"].lstrip("/")).read_bytes() != row["content"].encode():
            raise OSError("Incomplete recovery payload")
    os.sync()


def completed(plan, state=STATE):
    try:
        saved = json.loads(state.read_text())
    except (OSError, ValueError):
        return False
    return saved.get("trial_id") == plan["trial_id"] and saved.get("digest") == plan["digest"]


def retry_this_instance(plan, current=CURRENT_INSTANCE, instances=INSTANCE_ROOT):
    expected = instances / ("desk-portable-network-" + plan["trial_id"])
    if current.resolve() != expected.resolve() or not expected.is_dir():
        raise ValueError("Refusing to reset a different cloud-init instance")
    # Only this owned seed's command generation/execution, never users/keys/packages.
    for name in ("config_runcmd", "config_scripts_user"):
        target = expected / "sem" / name
        if target.is_symlink():
            raise ValueError("Unexpected cloud-init semaphore symlink")
        target.unlink(missing_ok=True)


def status(plan, phase, **extra):
    atomic_write(
        STATUS,
        (
            json.dumps(
                {"trial_id": plan["trial_id"], "phase": phase, "utc_unix": time.time(), **extra}
            )
            + "\n"
        ).encode(),
    )
    # A nonsecret, unauthenticated progress hint through the owner's existing
    # HTTP access log. No credentials, addresses, response commands or redirects.
    # Pinned SSH remains the only acceptance/authentication mechanism.
    if plan.get("relay_host"):
        suffix = phase
        if extra.get("component") == Path(RELAY).name:
            suffix += "-relay"
        elif extra.get("component") == Path(TRANSPORT).name:
            suffix += "-transport"
        elif extra.get("component") == Path(NETWORK).name:
            suffix += "-network"
        connection = http.client.HTTPConnection(plan["relay_host"], 80, timeout=2)
        try:
            connection.request("GET", "/fyp-recovery/" + plan["trial_id"] + "/" + suffix)
            connection.getresponse().close()
        except (OSError, http.client.HTTPException):
            pass
        finally:
            connection.close()


def recover(
    plan,
    mode,
    *,
    root=Path("/"),
    state=STATE,
    runner=None,
    report=status,
    retry=retry_this_instance,
):
    if mode not in ("boot", "run"):
        raise ValueError("Invalid recovery stage")
    if completed(plan, state):
        return  # Later legitimate software updates must not be overwritten by an old seed.
    report(plan, "restoring_verified_files")
    restore_files(plan, root)
    if mode == "boot":
        retry(plan)
        report(plan, "waiting_for_verified_setup")
        return
    if runner is None:

        def runner(command):
            subprocess.run(command, check=True, timeout=900)
            relay = command[1] == RELAY
            transport = command[1] == TRANSPORT
            receipt_path = (
                "/boot/firmware/desk-relay-transport-status.json"
                if transport
                else "/boot/firmware/desk-owner-relay-status.json"
                if relay
                else "/var/lib/desk-companion/network-status.json"
            )
            receipt = json.loads((root / receipt_path.lstrip("/")).read_text())
            accepted = (
                {"transport_configured"}
                if transport
                else {"relay_service_started"}
                if relay
                else {"network_ready", "waiting_for_network"}
            )
            if receipt.get("trial_id") != plan["trial_id"] or receipt.get("phase") not in accepted:
                raise RuntimeError("Setup command did not produce a current valid receipt")
            if relay:
                reachable = receipt.get("dial_tcp", receipt.get("vps_tcp")) == "reachable"
                report(plan, "relay_tcp_reachable" if reachable else "relay_tcp_unreachable")
            if transport:
                report(
                    plan,
                    "transport_ssh_banner"
                    if receipt.get("ssh_banner_observed")
                    else "transport_path_waiting",
                )

    for command in plan["commands"]:
        report(plan, "running_setup", component=Path(command[1]).name)
        runner(command)
    # Completion is recorded only after actual setup commands return successfully.
    result = {"trial_id": plan["trial_id"], "digest": plan["digest"], "utc_unix": time.time()}
    atomic_write(state, (json.dumps(result) + "\n").encode())
    os.sync()
    report(plan, "setup_completed", connection_acceptance_pending=True)


def verify_pair(expected_fingerprint, *, check_policy):
    if os.geteuid() != 0 or not Path("/var/lib/desk-companion-provisioned").is_file():
        raise RuntimeError("Existing paired Pi installation required")
    if expected_fingerprint != "-":
        reply = subprocess.run(
            ["ssh-keygen", "-lf", "/etc/ssh/ssh_host_ed25519_key.pub"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if reply.stdout.split()[1] != expected_fingerprint:
            raise RuntimeError("Pi host identity does not match the paired device")
    if check_policy:
        # bootcmd can precede sshd's runtime directory. No network rule/service is
        # changed there; enforce the full original policy before running setup.
        spec = importlib.util.spec_from_file_location(
            "desk_access", "/usr/local/lib/desk-classroom-access.py"
        )
        access = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(access)
        access.check_owner_auth()


def main():
    mode, fingerprint = sys.argv[1:3]
    if mode not in ("boot", "run"):
        raise SystemExit("Invalid recovery stage")
    verify_pair(fingerprint, check_policy=False)
    plan = read_plan()
    try:
        if mode == "run":
            verify_pair(fingerprint, check_policy=True)
        recover(plan, mode)
    except Exception as error:
        status(
            plan,
            "setup_failed",
            stage=mode,
            error_type=type(error).__name__,
            error_detail=str(error)[:400],
        )
        raise SystemExit("Verified network setup failed; inspect bootstrap status.") from None


if __name__ == "__main__":
    main()

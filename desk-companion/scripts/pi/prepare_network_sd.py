#!/usr/bin/env python3
"""Network-only NoCloud update for an identified existing Pi card.

Private credential-file input; --apply writes only user-data and meta-data after
backing up and checking the removable card. Never writes the Linux partition.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
from uuid import uuid4

from setup_classroom_access import atomic_write
from setup_network_access import CONFIG, HOME_UUID, PROFILE_ROOT, SCRIPT, WIRED_UUID, private_lan


def secret_file(path):
    info = path.lstat()
    if (
        path.is_symlink()
        or not path.is_file()
        or info.st_mode & 0o077
        or info.st_uid != os.getuid()
    ):
        raise ValueError("Credential input must be an owner-private regular file")
    value = json.loads(path.read_text())
    ssid, password = value["ssid"], value["password"]
    if (
        not isinstance(ssid, str)
        or not 1 <= len(ssid.encode()) <= 32
        or any(ord(c) < 32 or ord(c) == 127 for c in ssid)
    ):
        raise ValueError("A bounded Wi-Fi SSID is required")
    if (
        not isinstance(password, str)
        or not password.isascii()
        or not 8 <= len(password) <= 63
        or any(ord(c) < 32 or ord(c) == 127 for c in password)
    ):
        raise ValueError("A WPA personal passphrase is required")
    return ssid, password


def key_value(value):
    return value.replace("\\", "\\\\").replace(" ", "\\s")


def profiles(ssid, password):
    home = f"""[connection]
id=FYP-Home
uuid={HOME_UUID}
type=wifi
interface-name=wlan0
autoconnect=true
autoconnect-priority=300

[wifi]
mode=infrastructure
ssid={key_value(ssid)}
powersave=2

[wifi-security]
key-mgmt=wpa-psk
psk={key_value(password)}
psk-flags=0

[ipv4]
method=auto
route-metric=50

[ipv6]
method=auto
route-metric=50
"""
    wired = f"""[connection]
id=FYP-Wired
uuid={WIRED_UUID}
type=ethernet
interface-name=eth0
autoconnect=true
autoconnect-priority=200

[ethernet]
auto-negotiate=true

[ipv4]
method=auto
route-metric=100

[ipv6]
method=auto
route-metric=100
"""
    return home, wired


def render(ssid, password, owner_host, trial_id):
    private_lan(str(ipaddress.IPv4Address(owner_host)) + "/32")
    home, wired = profiles(ssid, password)
    source = Path(__file__).with_name("setup_network_access.py").read_text()
    policy = {
        "version": 1,
        "trial_id": trial_id,
        "country": "CN",
        "owner_host": owner_host,
        "owner_port": 8892,
    }
    files = [
        (SCRIPT, source, "0700"),
        (str(CONFIG), json.dumps(policy) + "\n", "0600"),
        (str(PROFILE_ROOT / "FYP-Home.nmconnection"), home, "0600"),
        (str(PROFILE_ROOT / "FYP-Wired.nmconnection"), wired, "0600"),
    ]
    data = {
        "hostname": "desk-companion",
        "preserve_hostname": True,
        "manage_etc_hosts": False,
        "users": [],
        "ssh_deletekeys": False,
        "ssh_pwauth": False,
        "enable_ssh": True,
        "package_update": False,
        "package_upgrade": False,
        "write_files": [
            {"path": p, "owner": "root:root", "permissions": mode, "content": body}
            for p, body, mode in files
        ],
        "runcmd": [["/usr/bin/python3", SCRIPT]],
    }
    user = "#cloud-config\n" + json.dumps(data, indent=2) + "\n"
    meta = (
        json.dumps(
            {
                "instance-id": "desk-portable-network-" + trial_id,
                "local-hostname": "desk-companion",
            },
            indent=2,
        )
        + "\n"
    )
    return user, meta


def disk_info(target):
    return plistlib.loads(
        subprocess.check_output(["/usr/sbin/diskutil", "info", "-plist", str(target)], timeout=10)
    )


def verify_target(boot, identity, inspect=disk_info):
    if boot.is_symlink() or not boot.is_dir():
        raise ValueError("A mounted regular boot volume is required")
    volume = inspect(boot)
    whole = inspect(volume["ParentWholeDisk"])
    if (
        volume.get("MountPoint") != str(boot)
        or volume.get("VolumeName") != "bootfs"
        or volume.get("Content") != "Windows_FAT_32"
        or volume.get("VolumeUUID") != identity["volume_uuid"]
        or not whole.get("RemovableMedia")
        or whole.get("TotalSize") != identity["capacity"]
    ):
        raise ValueError("The card identity does not match the recorded Pi")
    root = re.search(r"\broot=PARTUUID=([^\s]+)", (boot / "cmdline.txt").read_text())
    if not root or root[1] != identity["root_partuuid"]:
        raise ValueError("The Linux root partition identity does not match")
    return {
        "device": whole["DeviceIdentifier"],
        "capacity": whole["TotalSize"],
        "volume_uuid": volume["VolumeUUID"],
        "root_partuuid": root[1],
    }


def prepare(boot, private, identity, credentials, owner_host, *, apply=False):
    verified = verify_target(boot, identity)
    ssid, password = secret_file(credentials)
    if private.is_symlink():
        raise ValueError("Private output must not be a symlink")
    private.mkdir(mode=0o700, parents=True, exist_ok=True)
    private.chmod(0o700)
    trial = uuid4().hex
    directory = private / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + trial[:8])
    directory.mkdir(mode=0o700)
    user, meta = render(ssid, password, owner_host, trial)
    for name, text in [("user-data", user), ("meta-data", meta)]:
        atomic_write(directory / name, text)
    original = {}
    for name in ("user-data", "meta-data", "network-config", "config.txt", "cmdline.txt"):
        if (boot / name).is_symlink():
            raise ValueError("Boot files must be regular files")
        content = (boot / name).read_bytes()
        original[name] = content
        path = directory / ("before-" + name)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
    if apply:
        verify_target(boot, identity)
        try:
            for name, content in [("user-data", user), ("meta-data", meta)]:
                atomic_write(boot / name, content)
                if (boot / name).read_bytes() != content.encode():
                    raise RuntimeError("Boot file readback mismatch")
            for name in ("network-config", "config.txt", "cmdline.txt"):
                if (boot / name).read_bytes() != original[name]:
                    raise RuntimeError("An unrelated boot file changed")
        except BaseException:
            for name in ("user-data", "meta-data"):
                atomic_write(boot / name, original[name].decode())
            raise
    result = {
        **verified,
        "trial_id": trial,
        "applied": apply,
        "backup_directory": str(directory),
        "owner_host": owner_host,
        "owner_port": 8892,
        "changed_boot_files": ["user-data", "meta-data"] if apply else [],
        "linux_partition_written_by_mac": False,
        "preserved_boot_hashes": {
            name: hashlib.sha256(original[name]).hexdigest()
            for name in ("network-config", "config.txt", "cmdline.txt")
        },
    }
    atomic_write(private / "current.json", json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boot", type=Path, default=Path("/Volumes/bootfs"))
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--identity-file", type=Path, required=True)
    parser.add_argument("--credentials-file", type=Path, required=True)
    parser.add_argument("--owner-host", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = prepare(
        args.boot,
        args.private_dir,
        json.loads(args.identity_file.read_text()),
        args.credentials_file,
        args.owner_host,
        apply=args.apply,
    )
    print(
        json.dumps(
            {
                "prepared": True,
                "applied": result["applied"],
                "changed_boot_files": result["changed_boot_files"],
                "linux_partition_written_by_mac": False,
            }
        )
    )


if __name__ == "__main__":
    main()

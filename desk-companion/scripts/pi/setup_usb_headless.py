#!/usr/bin/python3
"""Optional, owner-requested Mac-to-Pi USB setup before offline installation.

The ordinary image keeps SSH off. This opt-in exposes key-only SSH on usb0;
VNC and the application stay on loopback and are reached through SSH tunnels.
"""

import json
import os
from pathlib import Path
import pwd
import secrets
import subprocess


def run(*args):
    subprocess.run(args, check=True)


def write(path, text, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)


def configure_vnc(home):
    # macOS Screen Sharing requires VNC authentication even inside SSH.
    # Legacy VNC uses only 8 characters; the key-only SSH tunnel supplies
    # actual transport encryption and remains the network access boundary.
    credentials = home / ".config/desk-companion/desktop-login.json"
    password = (
        json.loads(credentials.read_text())["password"]
        if credentials.exists()
        else secrets.token_urlsafe(6)
    )
    if len(password) != 8 or not all(c.isascii() and (c.isalnum() or c in "-_") for c in password):
        raise ValueError("Invalid local desktop password format")
    write(credentials, json.dumps({"password": password}) + "\n", 0o600)
    config = home / ".config/desk-companion/wayvnc.conf"
    write(
        config,
        "address=127.0.0.1\nport=5900\nenable_auth=true\n"
        "relax_encryption=true\nallow_broken_crypto=true\n"
        f"password={password}\n",
        0o600,
    )
    return config, credentials


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run on the Pi as root after the owner account is created")
    account = pwd.getpwnam("desk")
    home = Path(account.pw_dir)
    os.umask(0o077)
    for path in [
        home / ".config",
        home / ".config/desk-companion",
        home / ".config/systemd",
        home / ".config/systemd/user",
        home / ".config/autostart",
    ]:
        path.mkdir(parents=True, exist_ok=True)
        os.chown(path, account.pw_uid, account.pw_gid)
        path.chmod(0o700)
    authorized = home / ".ssh/authorized_keys"
    if not authorized.is_file() or not authorized.read_text().strip():
        raise SystemExit("No owner SSH public key; refusing remote access")

    # Separate table, no flush of system or NetworkManager firewall rules.
    # The same rule covers IPv4 and IPv6. A failed guard prevents SSH startup.
    write(
        "/etc/desk-usb-ssh.nft",
        """table inet desk_usb_ssh {
  chain input {
    type filter hook input priority -5; policy accept;
    tcp dport 22 iifname != "usb0" iifname != "lo" drop
  }
}
""",
    )
    write(
        "/etc/systemd/system/desk-usb-ssh-guard.service",
        """[Unit]
Description=Limit Desk Companion SSH to its physical USB network
Before=ssh.service

[Service]
Type=oneshot
ExecStart=/usr/sbin/nft -f /etc/desk-usb-ssh.nft
RemainAfterExit=yes
""",
    )
    write(
        "/etc/systemd/system/ssh.service.d/desk-usb-only.conf",
        """[Unit]
Requires=desk-usb-ssh-guard.service
After=desk-usb-ssh-guard.service
""",
    )
    write(
        "/etc/ssh/sshd_config.d/00-desk-usb.conf",
        """PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthenticationMethods publickey
PubkeyAuthentication yes
AllowUsers desk
AllowAgentForwarding no
X11Forwarding no
GatewayPorts no
AllowTcpForwarding local
PermitOpen 127.0.0.1:5900 127.0.0.1:8831
""",
        0o600,
    )
    run("ssh-keygen", "-A")
    run("/usr/sbin/sshd", "-t")

    config, desktop_credentials = configure_vnc(home)
    unit = home / ".config/systemd/user/desk-vnc.service"
    write(
        unit,
        f"""[Unit]
Description=Desk Companion desktop inside the owner SSH tunnel

[Service]
Type=simple
ExecStart=/usr/bin/wayvnc -C {config} -f 20
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
UMask=0077
""",
    )
    launcher = Path("/usr/local/bin/desk-usb-desktop")
    write(
        launcher,
        """#!/bin/sh
set -eu
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_SESSION_TYPE DBUS_SESSION_BUS_ADDRESS
dbus-update-activation-environment --systemd DISPLAY WAYLAND_DISPLAY XDG_SESSION_TYPE
systemctl --user start desk-vnc.service
""",
        0o755,
    )
    entry = home / ".config/autostart/desk-usb-desktop.desktop"
    write(
        entry,
        """[Desktop Entry]
Type=Application
Name=Desk Companion USB desktop
Exec=/usr/local/bin/desk-usb-desktop
Terminal=false
X-GNOME-Autostart-enabled=true
""",
    )
    for path in [config, desktop_credentials, unit, entry]:
        os.chown(path, account.pw_uid, account.pw_gid)

    # Use the vendor package already installed in this exact OS image.
    # Its watcher supports either host Internet Sharing or Pi-provided DHCP.
    run("rpi-usb-gadget", "on")
    run("systemctl", "daemon-reload")
    run("systemctl", "start", "desk-usb-ssh-guard.service")
    subprocess.run(["systemctl", "disable", "--now", "ssh.socket"], check=False)
    run("systemctl", "enable", "--now", "ssh.service")
    subprocess.run(
        ["raspi-config", "nonint", "do_boot_behaviour", "B4"],
        check=True,
        env={**os.environ, "SUDO_USER": "desk"},
    )
    write("/var/lib/desk-companion-usb-ready", "usb0 key-only SSH; loopback desktop\n", 0o600)
    print("USB remote desktop configured; reboot to activate the USB controller")


if __name__ == "__main__":
    main()

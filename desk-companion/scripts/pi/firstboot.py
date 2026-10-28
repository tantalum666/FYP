#!/usr/bin/python3
"""Install a verified offline payload on the owner's Raspberry Pi OS image.

Invoked once by cloud-init with the expected payload SHA256. No network fetches,
microphone/camera activation, or actuator startup occurs here.
"""

import hashlib
import importlib.util
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tarfile

APP = Path("/opt/desk-companion")
HOME_DIR = Path("/home/desk")
STATE = HOME_DIR / ".local/share/desk-companion"
DONE = Path("/var/lib/desk-companion-provisioned")
WIFI_UUID = "c0a12d72-834c-4b80-b454-70f9adac9137"
USB_READY = Path("/var/lib/desk-companion-usb-ready")


def configure_wifi_country(cmdline=Path("/boot/firmware/cmdline.txt")):
    """Set the regulatory domain without sending notifications to a GUI bus.

    raspi-config's country helper ends by calling wfpanelctl if a panel exists.
    During cloud-init that panel belongs to another session, so its notification
    can fail even after the regulatory settings succeeded.
    """
    text = cmdline.read_text().strip()
    if not text or "\n" in text:
        raise RuntimeError("Expected a single kernel command line")
    arguments = [x for x in text.split() if not x.startswith("cfg80211.ieee80211_regdom=")]
    arguments.append("cfg80211.ieee80211_regdom=HK")
    cmdline.write_text(" ".join(arguments) + "\n")
    run("iw", "reg", "set", "HK")
    run("rfkill", "unblock", "wifi")
    run("nmcli", "radio", "wifi", "on")


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def write(path, text, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)


def main():
    os.umask(0o077)
    if os.geteuid() != 0 or len(sys.argv) != 2:
        raise SystemExit("Run as root with the expected payload SHA256")
    expected = sys.argv[1]
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise SystemExit("Invalid payload digest")
    if DONE.exists():
        if DONE.read_text().strip() != expected:
            raise SystemExit("Existing installation differs; refusing an implicit upgrade")
        return
    account = pwd.getpwnam("desk")
    payload = Path("/boot/firmware/desk-payload.tar.xz")
    with payload.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != expected:
        raise SystemExit("Offline payload checksum mismatch")
    APP.mkdir(parents=True, exist_ok=True)
    APP.chmod(0o755)
    with tarfile.open(payload) as archive:
        archive.extractall(APP, filter="data")
    # The cloud-init installer may be a corrected version of the one embedded
    # in the unchanged payload. Keep the installed maintenance source in sync.
    installed_script = APP / "scripts/pi/firstboot.py"
    if Path(__file__).resolve() != installed_script.resolve():
        shutil.copyfile(__file__, installed_script)
    headless_source = Path("/usr/local/lib/desk-usb-headless.py")
    if headless_source.is_file():
        shutil.copyfile(headless_source, APP / "scripts/pi/setup_usb_headless.py")
    # tar's data filter deliberately omits directory modes; with our private
    # umask those start at 0700. This payload contains public code/dependencies,
    # so make it traversable by the non-root service (credentials are separate).
    for root, dirs, files in os.walk(APP, followlinks=False):
        os.chmod(root, 0o755)
        for name in files:
            path = Path(root) / name
            if not path.is_symlink():
                path.chmod(0o755 if path.stat().st_mode & 0o111 else 0o644)
    # All dependencies were resolved against this exact Pi image's dpkg status.
    debs = sorted((APP / "offline-debs").glob("*.deb"))
    if not debs:
        raise SystemExit("Offline dependencies missing")
    run("dpkg", "-i", *map(str, debs), env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"})
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    models = STATE / "models"
    if not models.exists():
        models.symlink_to(APP / "models", target_is_directory=True)
    secret = Path("/etc/desk-provision/qwen.env")
    key_path = HOME_DIR / ".config/desk-companion/qwen.env"
    # A failed previous run may already have moved the private bootstrap key.
    # Retrying must not silently turn off the owner's configured provider.
    provider = "qwen_omni" if key_path.is_file() else "none"
    if secret.is_file():
        key_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copyfile(secret, key_path)
        key_path.chmod(0o600)
        secret.unlink()
        provider = "qwen_omni"
    write(
        STATE / "service.env",
        "\n".join(
            [
                f"DESK_RUNTIME_DIR={STATE}",
                "DESK_NATIVE_CLIENTS=1",
                f"DESK_VOICE_PROVIDER={provider}",
                f"DESK_QWEN_CREDENTIAL_FILE={key_path}",
                "DESK_TEXT_PROVIDER=none",
                "DESK_TEXT_BACKGROUND=0",
                "DESK_ALLOW_REPLAY=0",
                "DESK_COMPUTER_ENABLED=1",
                "DESK_LINUX_DESKTOP_ENABLED=1",
                "",
            ]
        ),
    )
    spec = importlib.util.spec_from_file_location("installer", APP / "scripts/install_linux.py")
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    units = HOME_DIR / ".config/systemd/user"
    for name, content in installer.render(APP, STATE).items():
        write(units / name, content, 0o644)
    wants = units / "default.target.wants"
    wants.mkdir(parents=True, exist_ok=True)
    link = wants / "desk-companion.service"
    if not link.exists():
        link.symlink_to("../desk-companion.service")
    write(
        HOME_DIR / ".config/autostart/desk-companion.desktop",
        """[Desktop Entry]
Type=Application
Name=Desk Companion setup
Exec=/opt/desk-companion/scripts/pi/session.sh
Terminal=false
X-GNOME-Autostart-enabled=true
""",
        0o644,
    )
    desktop = HOME_DIR / "Desktop/Desk Companion.desktop"
    write(
        desktop,
        """[Desktop Entry]
Type=Application
Name=Desk Companion
Exec=/opt/desk-companion/scripts/pi/session.sh
Icon=preferences-desktop
Terminal=false
""",
        0o755,
    )
    # Keep CA validation enabled. The student enters their own CNA/password
    # locally after boot; no school credentials are baked into the image.
    write(
        Path("/etc/NetworkManager/system-connections/FYP-VTC-Student.nmconnection"),
        f"""[connection]
id=FYP-VTC-Student
uuid={WIFI_UUID}
type=wifi
autoconnect=false
permissions=user:desk:;

[wifi]
mode=infrastructure
ssid=VTC-Student

[wifi-security]
key-mgmt=wpa-eap

[802-1x]
eap=peap;
identity=ENTER_YOUR_CNA_USERNAME
phase2-auth=mschapv2
ca-cert=/etc/ssl/certs/ca-certificates.crt
domain-suffix-match=vtc.edu.hk
password-flags=2

[ipv4]
method=auto

[ipv6]
method=auto
""",
    )
    # Normal desktop login owns the API and its app processes. No root API,
    # background audio worker or persistent SSH access is installed.
    for base in [STATE, HOME_DIR / ".config", HOME_DIR / "Desktop"]:
        for root, dirs, files in os.walk(base, followlinks=False):
            os.chown(root, account.pw_uid, account.pw_gid)
            for name in dirs + files:
                os.lchown(Path(root) / name, account.pw_uid, account.pw_gid)
    for path in [HOME_DIR / ".local", HOME_DIR / ".local/share"]:
        os.chown(path, account.pw_uid, account.pw_gid)
        path.chmod(0o700)
    run(
        "runuser",
        "-u",
        "desk",
        "--",
        "env",
        f"PYTHONPATH={APP / 'backend'}",
        str(APP / ".venv/bin/python"),
        "-c",
        f"from desk.store import Store; Store({str(STATE)!r}); print('Fresh owner database initialized')",
    )
    configure_wifi_country()
    if not USB_READY.is_file():
        run("raspi-config", "nonint", "do_ssh", "1")
    run(
        "raspi-config", "nonint", "do_boot_behaviour", "B4", env={**os.environ, "SUDO_USER": "desk"}
    )
    run("nmcli", "connection", "reload")
    write(DONE, expected + "\n")
    print("Offline installation complete. Reboot into the local setup screen.")


if __name__ == "__main__":
    main()

"""Regressions from the first physical Pi boot, without opening real devices."""

import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


def script(name):
    path = Path(__file__).resolve().parents[1] / "scripts/pi" / name
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_country_setup_needs_no_desktop_bus_and_preserves_kernel_options(tmp_path, monkeypatch):
    module = script("firstboot.py")
    cmdline = tmp_path / "cmdline.txt"
    cmdline.write_text(
        "root=PARTUUID=example-02 rootwait cfg80211.ieee80211_regdom=US video=HDMI-A-1:1280x720@60D\n"
    )
    calls = []
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("DBUS_SESSION_BUS_ADDRESS", raising=False)
    monkeypatch.setattr(module, "run", lambda *args: calls.append(args))
    module.configure_wifi_country(cmdline)
    expected = cmdline.read_text()
    assert expected.count("cfg80211.ieee80211_regdom=") == 1
    assert "cfg80211.ieee80211_regdom=HK" in expected
    assert "root=PARTUUID=example-02 rootwait" in expected
    assert "video=HDMI-A-1:1280x720@60D" in expected
    assert calls == [
        ("iw", "reg", "set", "HK"),
        ("rfkill", "unblock", "wifi"),
        ("nmcli", "radio", "wifi", "on"),
    ]
    module.configure_wifi_country(cmdline)
    assert cmdline.read_text() == expected


def test_country_setup_refuses_invalid_boot_file_before_writing(tmp_path, monkeypatch):
    module = script("firstboot.py")
    path = tmp_path / "cmdline.txt"
    path.write_text("root=a\nroot=b\n")
    monkeypatch.setattr(module, "run", lambda *args: pytest.fail("Must not run commands"))
    with pytest.raises(RuntimeError):
        module.configure_wifi_country(path)
    assert path.read_text() == "root=a\nroot=b\n"


def test_usb_recovery_works_before_app_install_and_still_requires_guard(tmp_path, monkeypatch):
    module = script("setup_usb_headless.py")
    home = tmp_path / "desk"
    (home / ".ssh").mkdir(parents=True)
    (home / ".ssh/authorized_keys").write_text("synthetic-owner-public-key\n")
    monkeypatch.setattr(module.os, "geteuid", lambda: 0)
    monkeypatch.setattr(module.os, "umask", lambda mask: 0o022)
    monkeypatch.setattr(
        module.pwd,
        "getpwnam",
        lambda name: SimpleNamespace(pw_dir=str(home), pw_uid=os.getuid(), pw_gid=os.getgid()),
    )
    calls, files = [], {}
    monkeypatch.setattr(module, "run", lambda *args: calls.append(args))
    monkeypatch.setattr(module.subprocess, "run", lambda args, **kwargs: calls.append(tuple(args)))
    monkeypatch.setattr(
        module, "write", lambda path, text, mode=0o644: files.__setitem__(str(path), text)
    )
    monkeypatch.setattr(module.os, "chown", lambda *args: None)
    module.main()  # No app, venv or successful application marker exists.
    assert calls.index(("systemctl", "start", "desk-usb-ssh-guard.service")) < calls.index(
        ("systemctl", "enable", "--now", "ssh.service")
    )
    assert (
        "Requires=desk-usb-ssh-guard.service"
        in files["/etc/systemd/system/ssh.service.d/desk-usb-only.conf"]
    )
    assert "address=127.0.0.1" in files[str(home / ".config/desk-companion/wayvnc.conf")]
    assert "/var/lib/desk-companion-usb-ready" in files


def test_usb_recovery_does_not_enable_access_without_owner_key(tmp_path, monkeypatch):
    module = script("setup_usb_headless.py")
    monkeypatch.setattr(module.os, "geteuid", lambda: 0)
    monkeypatch.setattr(module.os, "umask", lambda mask: 0o022)
    monkeypatch.setattr(
        module.pwd,
        "getpwnam",
        lambda name: SimpleNamespace(pw_dir=str(tmp_path), pw_uid=os.getuid(), pw_gid=os.getgid()),
    )
    monkeypatch.setattr(module, "run", lambda *args: pytest.fail("Must not enable access"))
    with pytest.raises(SystemExit, match="No owner SSH public key"):
        module.main()


def test_desktop_recovery_keeps_password_private_stable_and_listener_on_loopback(tmp_path):
    module = script("setup_usb_headless.py")
    config, credentials = module.configure_vnc(tmp_path)
    first = json.loads(credentials.read_text())["password"]
    assert len(first) == 8
    assert config.stat().st_mode & 0o777 == 0o600
    assert credentials.stat().st_mode & 0o777 == 0o600
    assert "address=127.0.0.1\n" in config.read_text()
    assert "enable_auth=true\n" in config.read_text()
    module.configure_vnc(tmp_path)
    assert json.loads(credentials.read_text())["password"] == first

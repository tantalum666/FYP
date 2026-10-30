"""Portable networking boundaries; no live radios or user credentials."""

import json
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "pi"


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import setup_network_access as network
    import prepare_network_sd as prepare

    return network, prepare


def interface(name, ip, prefix=24, up=True):
    return {
        "ifname": name,
        "flags": ["UP", "LOWER_UP"] if up else ["UP"],
        "addr_info": [{"family": "inet", "scope": "global", "local": ip, "prefixlen": prefix}],
    }


def test_connected_wired_and_known_wifi_follow_actual_private_subnets(modules):
    n, _ = modules
    values = [interface("eth0", "172.18.37.28"), interface("wlan0", "192.168.0.52")]
    assert n.admitted_networks(values, {"wlan0": n.HOME_UUID}) == [
        ("eth0", "172.18.37.0/24"),
        ("wlan0", "192.168.0.0/24"),
    ]
    assert n.admitted_networks([interface("eth0", "10.104.53.20", 21)], {}) == [
        ("eth0", "10.104.48.0/21")
    ]
    assert n.admitted_networks([interface("wlan0", "192.168.49.5")], {"wlan0": n.CLASSROOM_UUID})


@pytest.mark.parametrize(
    "value",
    [
        interface("eth0", "8.8.8.8"),
        interface("eth0", "169.254.1.1", 16),
        interface("eth0", "10.1.2.3", 8),
        interface("eth0", "192.168.0.2", up=False),
        interface("wlan0", "192.168.0.2"),
        interface("tun0", "10.1.2.3"),
    ],
)
def test_unadmitted_networks_never_expand_ssh_access(modules, value):
    n, _ = modules
    assert n.admitted_networks([value], {"wlan0": "unselected-profile"}) == []


def test_guard_preserves_usb_without_flushing_system_rules(modules):
    n, _ = modules
    rules = n.rules_for([("eth0", "10.104.53.20/21")])
    assert 'iifname "usb0"' in rules and 'iifname "lo"' in rules
    assert "ip saddr 10.104.48.0/21" in rules
    assert "tcp dport 22 counter drop" in rules
    assert "flush ruleset" not in rules and "8831" not in rules and "5900" not in rules
    with pytest.raises(ValueError):
        n.rules_for([("eth0; unsafe", "192.168.0.0/24")])


def test_render_preserves_users_keys_and_keeps_credential_out_of_argv(modules):
    n, p = modules
    user, meta = p.render("Fixture WiFi", "fixture-passphrase", "192.168.0.7", "trial")
    data = json.loads(user.split("\n", 1)[1])
    assert data["users"] == [] and data["ssh_deletekeys"] is False and data["ssh_pwauth"] is False
    assert data["package_update"] is False and data["package_upgrade"] is False
    assert data["runcmd"] == [["/usr/bin/python3", n.SCRIPT]]
    entries = {v["path"]: v for v in data["write_files"]}
    wifi = entries[str(n.PROFILE_ROOT / "FYP-Home.nmconnection")]
    wired = entries[str(n.PROFILE_ROOT / "FYP-Wired.nmconnection")]
    assert wifi["permissions"] == wired["permissions"] == "0600"
    assert "ssid=Fixture\\sWiFi" in wifi["content"]
    assert "method=auto" in wired["content"] and "interface-name=eth0" in wired["content"]
    assert "route-metric=50" in wifi["content"] and "route-metric=100" in wired["content"]
    assert "fixture-passphrase" not in meta
    assert "fixture-passphrase" not in str(data["runcmd"])


def test_target_requires_same_removable_card_uuid_size_and_root(modules, tmp_path):
    _, p = modules
    boot = tmp_path / "bootfs"
    boot.mkdir()
    (boot / "cmdline.txt").write_text("console=tty1 root=PARTUUID=fixture-02 rootwait")
    expected = {
        "volume_uuid": "fixture-volume",
        "capacity": 128000000000,
        "root_partuuid": "fixture-02",
    }
    volume = {
        "ParentWholeDisk": "disk4",
        "MountPoint": str(boot),
        "VolumeName": "bootfs",
        "Content": "Windows_FAT_32",
        "VolumeUUID": "fixture-volume",
    }
    disk = {"DeviceIdentifier": "disk4", "RemovableMedia": True, "TotalSize": expected["capacity"]}

    def inspect(target):
        return disk if target == "disk4" else volume

    assert p.verify_target(boot, expected, inspect)["device"] == "disk4"
    disk["RemovableMedia"] = False
    with pytest.raises(ValueError):
        p.verify_target(boot, expected, inspect)
    disk["RemovableMedia"] = True
    volume["VolumeUUID"] = "another-card"
    with pytest.raises(ValueError):
        p.verify_target(boot, expected, inspect)


def prepare_fixture(p, tmp_path, monkeypatch):
    boot = tmp_path / "bootfs"
    boot.mkdir()
    old = {
        name: ("original-" + name).encode()
        for name in ("user-data", "meta-data", "config.txt", "cmdline.txt", "network-config")
    }
    for name, content in old.items():
        (boot / name).write_bytes(content)
    credentials = tmp_path / "wifi.json"
    credentials.write_text(json.dumps({"ssid": "Fixture", "password": "fixture-only"}))
    credentials.chmod(0o600)
    monkeypatch.setattr(p, "verify_target", lambda *a: {"device": "fixture"})
    return boot, old, credentials


def test_prepare_backups_and_writes_only_two_boot_files(modules, tmp_path, monkeypatch):
    _, p = modules
    boot, old, credentials = prepare_fixture(p, tmp_path, monkeypatch)
    result = p.prepare(boot, tmp_path / "private", {}, credentials, "192.168.0.7", apply=True)
    assert result["changed_boot_files"] == ["user-data", "meta-data"]
    for name in ("config.txt", "cmdline.txt", "network-config"):
        assert (boot / name).read_bytes() == old[name]
    backup = Path(result["backup_directory"])
    for name in old:
        assert (backup / ("before-" + name)).read_bytes() == old[name]
    assert (backup / "user-data").stat().st_mode & 0o777 == 0o600


def test_second_file_failure_restores_original_seed(modules, tmp_path, monkeypatch):
    _, p = modules
    boot, old, credentials = prepare_fixture(p, tmp_path, monkeypatch)
    write = p.atomic_write
    failures = []

    def interrupted(path, text, *args):
        if path == boot / "meta-data" and not failures:
            failures.append(True)
            raise OSError("fixture write failure")
        return write(path, text, *args)

    monkeypatch.setattr(p, "atomic_write", interrupted)
    with pytest.raises(OSError):
        p.prepare(boot, tmp_path / "private", {}, credentials, "192.168.0.7", apply=True)
    for name in old:
        assert (boot / name).read_bytes() == old[name]


def test_bad_or_world_readable_credentials_are_rejected(modules, tmp_path):
    _, p = modules
    path = tmp_path / "wifi.json"
    path.write_text(json.dumps({"ssid": "Fixture\nunsafe", "password": "fixture-only"}))
    path.chmod(0o600)
    with pytest.raises(ValueError):
        p.secret_file(path)
    path.write_text(json.dumps({"ssid": "Fixture", "password": "fixture-only"}))
    path.chmod(0o644)
    with pytest.raises(ValueError):
        p.secret_file(path)


@pytest.mark.parametrize("wired_carrier", [False, True])
def test_boot_keeps_classroom_wifi_disables_dorm_retries_and_attempts_home(
    modules, tmp_path, monkeypatch, wired_carrier
):
    from types import SimpleNamespace
    import subprocess

    n, p = modules
    commands, notifications = [], []
    real_path = Path

    def rooted(value):
        return tmp_path / str(value).lstrip("/")

    marker = rooted("/var/lib/desk-companion-provisioned")
    marker.parent.mkdir(parents=True)
    marker.touch()
    carrier = rooted("/sys/class/net/eth0/carrier")
    if wired_carrier:
        carrier.parent.mkdir(parents=True)
        carrier.write_text("1")
    profile_root = tmp_path / "profiles"
    profile_root.mkdir()
    for name in ("FYP-Home", "FYP-Wired"):
        target = profile_root / (name + ".nmconnection")
        target.write_text("fixture")
        target.chmod(0o600)
    guard, unit = tmp_path / "guard.nft", tmp_path / "guard.service"
    guard.write_text("old guard")
    unit.write_text("old unit")
    access = SimpleNamespace(
        GUARD=guard, UNIT=unit, check_owner_auth=lambda: None, atomic_write=p.atomic_write
    )

    def command(*args, **kwargs):
        commands.append(args)
        if args[:4] == ("nmcli", "-t", "-f", "UUID"):
            return subprocess.CompletedProcess(
                args, 0, "\n".join([n.CLASSROOM_UUID, n.STUDENT_UUID, n.HALLS_UUID]), ""
            )
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(n, "Path", rooted)
    monkeypatch.setattr(n, "PROFILE_ROOT", profile_root)
    monkeypatch.setattr(n, "run", command)
    monkeypatch.setattr(n, "apply_guard", lambda access: [("wlan0", "192.168.0.0/24")])
    monkeypatch.setattr(n, "public_status", lambda policy, phase, **kw: {"phase": phase, **kw})
    monkeypatch.setattr(n, "save_status", lambda *args: None)
    monkeypatch.setattr(n, "notify_owner", lambda policy, state: notifications.append(state))
    monkeypatch.setattr(n.time, "sleep", lambda value: None)
    n.install({"trial_id": "fixture", "country": "CN"}, access)
    assert ("nmcli", "--wait", "40", "connection", "up", "uuid", n.HOME_UUID) in commands
    wired = ("nmcli", "--wait", "30", "connection", "up", "uuid", n.WIRED_UUID)
    assert (wired in commands) == wired_carrier
    for identifier in (n.STUDENT_UUID, n.HALLS_UUID):
        assert (
            "nmcli",
            "connection",
            "modify",
            identifier,
            "connection.autoconnect",
            "no",
        ) in commands
    assert any(
        c[:5] == ("nmcli", "connection", "modify", n.CLASSROOM_UUID, "connection.autoconnect")
        and c[5] == "yes"
        for c in commands
    )
    assert real_path(str(guard) + ".before-portable-network").read_text() == "old guard"
    assert len(notifications) == 30 and all(x["phase"] == "network_ready" for x in notifications)

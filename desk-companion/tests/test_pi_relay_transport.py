"""Fixed target transport and offline binary integrity; no live proxy credentials."""

import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "pi"


@pytest.fixture
def transport(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import setup_relay_transport as module

    monkeypatch.setattr(module.os, "sync", lambda: None)
    return module


@pytest.fixture
def inputs(transport, tmp_path):
    binary = bytearray(64)
    binary[:6] = b"\x7fELF\x02\x01"
    binary[18:20] = struct.pack("<H", 183)
    binary += b"fixture-binary"
    archive = tmp_path / "client.gz"
    archive.write_bytes(gzip.compress(binary))
    runtime = {
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
        "profile": {"store-selected": False, "store-fake-ip": False},
        "geo-auto-update": False,
        "proxies": [
            {
                "name": "FYP-RELAY",
                "type": "vless",
                "server": "198.51.100.23",
                "port": 443,
                "uuid": "00000000-0000-0000-0000-000000000001",
                "network": "tcp",
                "tls": True,
                "reality-opts": {
                    "public-key": "A" * 43,
                    "short-id": "abcd",
                    "support-x25519mlkem768": False,
                },
            }
        ],
        "rules": ["MATCH,REJECT"],
        "tunnels": [
            {
                "network": ["tcp"],
                "address": "127.0.0.1:22422",
                "target": "198.51.100.23:22",
                "proxy": "FYP-RELAY",
            }
        ],
    }
    config = {
        "trial_id": "a" * 32,
        "relay_host": "198.51.100.23",
        "runtime_config": runtime,
        "archive_name": transport.ARCHIVE_NAME,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "binary_sha256": hashlib.sha256(binary).hexdigest(),
        "binary_size": len(binary),
        "version": "fixture",
    }
    return config, archive, bytes(binary)


@pytest.mark.parametrize(
    "change",
    [
        "tun",
        "dns",
        "generic_proxy",
        "public_listener",
        "other_destination",
        "other_node",
        "controller",
        "other_interface",
        "private_server_key",
    ],
)
def test_config_cannot_become_a_global_or_general_proxy(transport, inputs, change):
    config, _, _ = inputs
    runtime = config["runtime_config"]
    if change == "tun":
        runtime["tun"]["enable"] = True
    elif change == "dns":
        runtime["dns"]["enable"] = True
    elif change == "generic_proxy":
        runtime["socks-port"] = 1080
    elif change == "public_listener":
        runtime["tunnels"][0]["address"] = "0.0.0.0:22422"
    elif change == "other_destination":
        runtime["tunnels"][0]["target"] = "198.51.100.99:22"
    elif change == "other_node":
        runtime["proxies"][0]["server"] = "198.51.100.99"
    elif change == "controller":
        runtime["external-controller"] = "0.0.0.0:9090"
    elif change == "other_interface":
        runtime["interface-name"] = "eth0"
    else:
        runtime["proxies"][0]["reality-opts"]["private-key"] = "fixture-forbidden"
    with pytest.raises(ValueError):
        transport.validate(config)


def test_valid_offline_arm64_binary_is_installed_and_read_back(transport, inputs, tmp_path):
    config, archive, binary = inputs
    transport.validate(config)
    target = tmp_path / "installed/client"
    transport.install_binary(config, archive, target)
    assert target.read_bytes() == binary and target.stat().st_mode & 0o777 == 0o755
    target.chmod(0o600)
    before = target.stat().st_mtime_ns
    transport.install_binary(config, archive, target)
    assert target.stat().st_mtime_ns == before and target.stat().st_mode & 0o777 == 0o755


@pytest.mark.parametrize("corruption", ["archive", "binary_hash", "oversize", "wrong_arch"])
def test_bad_artifact_keeps_previous_binary(transport, inputs, tmp_path, corruption):
    config, archive, binary = inputs
    target = tmp_path / "installed"
    target.write_bytes(b"previous-safe")
    if corruption == "archive":
        archive.write_bytes(b"corrupted")
    elif corruption == "binary_hash":
        config["binary_sha256"] = "0" * 64
    elif corruption == "oversize":
        config["binary_size"] -= 1
    else:
        changed = bytearray(binary)
        changed[18:20] = struct.pack("<H", 62)
        archive.write_bytes(gzip.compress(changed))
        config["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
        config["binary_sha256"] = hashlib.sha256(changed).hexdigest()
    with pytest.raises(ValueError):
        transport.install_binary(config, archive, target)
    assert target.read_bytes() == b"previous-safe"


def protected_bundle(config, archive, tmp_path):
    key = tmp_path / "key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    manifest = {k: config[k] for k in ["archive_sha256", "binary_sha256", "binary_size", "version"]}
    manifest["archive_file"] = str(archive)
    paths = {}
    for name, value in [("manifest", manifest), ("transport", config["runtime_config"])]:
        p = tmp_path / (name + ".json")
        p.write_text(json.dumps(value))
        p.chmod(0o600)
        paths[name] = str(p)
    bundle = {
        "host": config["relay_host"],
        "port": 22,
        "remote_port": 22073,
        "user": "fyp-fixture",
        "server_host_key": " ".join(key.with_suffix(".pub").read_text().split()[:2]),
        "private_key_file": str(key),
        "transport_manifest_file": paths["manifest"],
        "transport_config_file": paths["transport"],
    }
    p = tmp_path / "bundle.json"
    p.write_text(json.dumps(bundle))
    p.chmod(0o600)
    return p


def test_transport_seed_runs_network_then_transport_then_pinned_relay(transport, inputs, tmp_path):
    import prepare_network_sd as prepare
    import setup_owner_relay as relay
    import network_bootstrap as bootstrap

    config, archive, _ = inputs
    bundle = protected_bundle(config, archive, tmp_path)
    boot = tmp_path / "boot"
    boot.mkdir()
    user, meta = prepare.render(
        "Fixture", "fixture-only", "192.168.0.7", "a" * 32, relay_bundle=bundle
    )
    (boot / "user-data").write_text(user)
    (boot / "meta-data").write_text(meta)
    plan = bootstrap.read_plan(boot)
    assert [c[1] for c in plan["commands"]] == [
        bootstrap.NETWORK,
        bootstrap.TRANSPORT,
        bootstrap.RELAY,
    ]
    relay_config = json.loads(
        next(row["content"] for row in plan["entries"] if row["path"] == str(relay.CONFIG))
    )
    assert relay.dial_target(relay_config) == ("127.0.0.1", 22422)
    unit = relay.service_text(relay_config)
    assert "desk-relay-transport.service" in unit and "StrictHostKeyChecking=yes" in unit
    assert "fyp-fixture@127.0.0.1" in unit and "HostKeyAlias=desk-owner-relay-vps" in unit


def test_seed_failure_restores_prior_archive_and_boot_files(
    transport, inputs, tmp_path, monkeypatch
):
    import prepare_network_sd as prepare

    config, archive, _ = inputs
    bundle = protected_bundle(config, archive, tmp_path)
    boot = tmp_path / "boot"
    boot.mkdir()
    previous = {}
    for name in [
        "user-data",
        "meta-data",
        "config.txt",
        "cmdline.txt",
        "network-config",
        transport.ARCHIVE_NAME,
    ]:
        value = ("before-" + name).encode()
        (boot / name).write_bytes(value)
        previous[name] = value
    credentials = tmp_path / "wifi.json"
    credentials.write_text(json.dumps({"ssid": "Fixture", "password": "fixture-only"}))
    credentials.chmod(0o600)
    monkeypatch.setattr(prepare, "verify_target", lambda *a: {"device": "fixture"})
    original = prepare.atomic_write
    failed = []

    def write(path, text, *args):
        if path == boot / "meta-data" and not failed:
            failed.append(True)
            raise OSError("fixture second-file failure")
        return original(path, text, *args)

    monkeypatch.setattr(prepare, "atomic_write", write)
    with pytest.raises(OSError):
        prepare.prepare(
            boot,
            tmp_path / "private",
            {},
            credentials,
            "192.168.0.7",
            apply=True,
            relay_bundle=bundle,
        )
    assert all((boot / name).read_bytes() == value for name, value in previous.items())


def test_installer_uses_user_owned_state_and_does_not_claim_banner_is_auth(
    transport, inputs, tmp_path, monkeypatch
):
    import os
    from types import SimpleNamespace
    import setup_classroom_access as access_module

    config, _, _ = inputs
    marker = tmp_path / "var/lib/desk-companion-provisioned"
    marker.parent.mkdir(parents=True)
    marker.touch()
    monkeypatch.setattr(transport, "Path", lambda value: tmp_path / str(value).lstrip("/"))
    for name, value in [
        ("USER_DIR", tmp_path / "home/config/relay"),
        ("DATA", tmp_path / "home/state/relay"),
        ("RUNTIME_CONFIG", tmp_path / "home/config/relay/transport.json"),
        ("BINARY", tmp_path / "bin/client"),
        ("UNIT", tmp_path / "unit.service"),
        ("STATUS", tmp_path / "status.json"),
    ]:
        monkeypatch.setattr(transport, name, value)
    monkeypatch.setattr(transport.platform, "machine", lambda: "aarch64")
    monkeypatch.setattr(transport, "install_binary", lambda *args: None)
    monkeypatch.setattr(
        transport.pwd,
        "getpwnam",
        lambda user: SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid()),
    )
    monkeypatch.setattr(transport.os, "chown", lambda *args: None)
    monkeypatch.setattr(transport.time, "sleep", lambda seconds: None)
    commands = []

    def command(*args):
        commands.append(args)
        if args[:5] == ("runuser", "-u", "desk", "--", "mkdir"):
            Path(args[-1]).mkdir(parents=True)
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(transport, "run", command)

    class Peer:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def settimeout(self, value):
            pass

        def recv(self, size):
            return b"SSH-2.0-fixture\r\n"

    monkeypatch.setattr(transport.socket, "create_connection", lambda *args, **kwargs: Peer())
    transport.install(
        config,
        SimpleNamespace(check_owner_auth=lambda: None, atomic_write=access_module.atomic_write),
    )
    assert commands[0][:5] == ("runuser", "-u", "desk", "--", "mkdir")
    assert all(c[0] in ["runuser", "systemctl"] for c in commands)
    assert transport.RUNTIME_CONFIG.stat().st_mode & 0o777 == 0o600
    assert transport.DATA.stat().st_mode & 0o777 == 0o700
    state = json.loads(transport.STATUS.read_text())
    assert state["ssh_banner_observed"] is True and state["authenticated_vps"] is False
    assert state["global_proxy_or_routes_changed"] is False

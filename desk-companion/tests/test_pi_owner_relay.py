"""Owner-hosted transport boundaries; generated fixture keys, no live accounts."""

import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "pi"


@pytest.fixture
def relay(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import setup_owner_relay

    return setup_owner_relay


@pytest.fixture
def bundle(tmp_path):
    key = tmp_path / "relay-key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    public = " ".join(key.with_suffix(".pub").read_text().split()[:2])
    config = {
        "host": "198.51.100.23",
        "port": 22,
        "remote_port": 22073,
        "user": "fyp-fixture-relay",
        "server_host_key": public,
        "private_key_file": str(key),
    }
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    return config, path, key


@pytest.mark.parametrize(
    "changes",
    [
        {"host": "127.0.0.1"},
        {"host": "0.0.0.0"},
        {"host": "fe80::1%eth0"},
        {"user": "root"},
        {"user": "fyp-fixture\nUser=root"},
        {"port": "22"},
        {"remote_port": 22},
        {"remote_port": True},
        {"server_host_key": "ssh-ed25519 invalid"},
    ],
)
def test_relay_config_cannot_expand_user_listener_or_unit_syntax(relay, bundle, changes):
    config, _, _ = bundle
    with pytest.raises((ValueError, TypeError)):
        relay.validate({**config, **changes})


def test_seed_credentials_remain_private_and_do_not_reach_metadata_or_argv(relay, bundle):
    import prepare_network_sd as prepare

    config, path, key = bundle
    user, meta = prepare.render(
        "Fixture", "fixture-only", "192.168.0.7", "fixture", country="HK", relay_bundle=path
    )
    data = json.loads(user.split("\n", 1)[1])
    files = {row["path"]: row for row in data["write_files"]}
    assert files[str(relay.KEY)]["content"] == key.read_text()
    assert files[str(relay.KEY)]["permissions"] == "0600"
    assert files[str(relay.KNOWN)]["permissions"] == "0600"
    assert (
        files[str(relay.KNOWN)]["content"]
        == relay.HOST_ALIAS + " " + config["server_host_key"] + "\n"
    )
    assert data["runcmd"][0][:2] == ["/usr/bin/python3", "-c"]
    assert data["runcmd"][0][-2:] == ["run", "-"]
    assert len(data["runcmd"]) == 1
    assert data["users"] == [] and data["ssh_deletekeys"] is False
    assert key.read_text() not in meta + json.dumps(data["runcmd"])
    assert str(key) not in user


def test_world_readable_or_symlinked_relay_inputs_are_rejected(relay, bundle, tmp_path):
    _, path, key = bundle
    path.chmod(0o644)
    with pytest.raises(ValueError):
        relay.seed_files(path, "fixture")
    path.chmod(0o600)
    key.chmod(0o644)
    with pytest.raises(ValueError):
        relay.seed_files(path, "fixture")
    key.chmod(0o600)
    link = tmp_path / "alias.json"
    link.symlink_to(path)
    with pytest.raises(ValueError):
        relay.seed_files(link, "fixture")


def test_service_is_nonroot_pinned_and_has_one_loopback_ssh_destination(relay, bundle):
    config, _, _ = bundle
    unit = relay.service_text(config)
    assert "User=desk\nGroup=desk" in unit and "User=root" not in unit
    assert "127.0.0.1:22073:127.0.0.1:22" in unit
    assert "StrictHostKeyChecking=yes" in unit and "IdentityAgent=none" in unit
    assert "ExitOnForwardFailure=yes" in unit and "UpdateHostKeys=no" in unit
    assert "0.0.0.0:" not in unit and "accept-new" not in unit
    assert "Restart=on-failure" in unit and "NoNewPrivileges=yes" in unit


def test_installer_requires_existing_owner_auth_before_writes(relay, bundle, tmp_path, monkeypatch):
    config, _, _ = bundle
    marker = tmp_path / "marker"
    marker.touch()
    monkeypatch.setattr(relay, "Path", lambda value: marker)

    def deny():
        raise RuntimeError("fixture original auth is unsafe")

    def no_write(*args):
        raise AssertionError("must not mutate before owner-auth check")

    with pytest.raises(RuntimeError):
        relay.install(config, SimpleNamespace(check_owner_auth=deny, atomic_write=no_write))


def test_installer_reports_service_state_without_claiming_authenticated_pi(
    relay, bundle, tmp_path, monkeypatch
):
    import setup_classroom_access as access_module

    config, _, _ = bundle
    config = {**config, "trial_id": "fixture"}
    marker = tmp_path / "marker"
    marker.touch()
    monkeypatch.setattr(relay, "Path", lambda value: marker)
    directory = tmp_path / "relay"
    directory.mkdir()
    key = directory / "key"
    known = directory / "known"
    key.write_text("fixture unchanged key")
    known.write_text("fixture pin")
    for name, value in [
        ("ROOT", directory),
        ("KEY", key),
        ("KNOWN", known),
        ("UNIT", tmp_path / "unit"),
        ("BOOT_STATUS", tmp_path / "status.json"),
    ]:
        monkeypatch.setattr(relay, name, value)
    monkeypatch.setattr(
        relay.pwd, "getpwnam", lambda value: SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())
    )
    monkeypatch.setattr(relay.os, "chown", lambda *args: None)
    monkeypatch.setattr(relay.time, "sleep", lambda value: None)
    commands = []

    def run(*args):
        commands.append(args)
        return SimpleNamespace(
            stdout="Connection timed out" if args[0] == "journalctl" else "ActiveState=active\n"
        )

    monkeypatch.setattr(relay, "run", run)

    def unreachable(*args, **kwargs):
        raise TimeoutError("fixture no route")

    monkeypatch.setattr(relay.socket, "create_connection", unreachable)
    relay.install(
        config,
        SimpleNamespace(check_owner_auth=lambda: None, atomic_write=access_module.atomic_write),
    )
    status = json.loads(relay.BOOT_STATUS.read_text())
    assert status["authenticated_pi_access_verified"] is False
    assert status["vps_tcp"] == "TimeoutError" and status["error_hints"] == ["Connection timed out"]
    assert ("systemctl", "enable", "--now", relay.UNIT_NAME) in commands
    assert key.read_text() == "fixture unchanged key" and known.read_text() == "fixture pin"

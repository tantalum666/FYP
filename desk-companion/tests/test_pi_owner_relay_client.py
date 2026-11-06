"""Reject unsafe owner routing inputs before creating a management tunnel."""

import json
from pathlib import Path
import shlex
import subprocess

import pytest


@pytest.fixture
def relay_client(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts" / "pi"))
    import owner_relay_client

    return owner_relay_client


@pytest.fixture
def client_config(tmp_path):
    known = tmp_path / "known hosts"
    known.touch()
    config = {
        "version": 1,
        "host": "8.8.8.8",  # Parsing fixture only; these tests never connect.
        "port": 22,
        "user": "fixture",
        "host_key_alias": "fixture-vps",
        "known_hosts_file": str(known),
        "remote_port": 22073,
    }
    path = tmp_path / "client.json"
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    return config, path


@pytest.mark.parametrize("change", [
    {"host": "127.0.0.1"}, {"host": "10.0.0.1"}, {"host": "-oProxyCommand=bad"},
    {"user": "fixture;touch unexpected"}, {"host_key_alias": "fixture\nHost *"},
    {"remote_port": True}, {"remote_port": 65536}, {"port": "22"},
    {"version": True}, {"proxy_command": "unexpected"},
])
def test_unsafe_routes_fail_before_ssh(relay_client, client_config, change):
    config, path = client_config
    path.write_text(json.dumps({**config, **change}))
    with pytest.raises((ValueError, TypeError)):
        relay_client.proxy_command(path)


def test_configuration_must_be_owner_private_and_not_a_symlink(relay_client, client_config):
    _, path = client_config
    path.chmod(0o644)
    with pytest.raises(ValueError):
        relay_client.proxy_command(path)
    path.chmod(0o600)
    link = path.with_name("linked.json")
    link.symlink_to(path)
    with pytest.raises(ValueError):
        relay_client.proxy_command(link)


def test_openssh_tokens_in_paths_are_rejected(relay_client, client_config, tmp_path):
    config, path = client_config
    known = tmp_path / "%h known"
    known.touch()
    path.write_text(json.dumps({**config, "known_hosts_file": str(known)}))
    with pytest.raises(ValueError):
        relay_client.proxy_command(path)


def test_shell_path_remains_one_literal_argument(relay_client, client_config, tmp_path):
    config, path = client_config
    known = tmp_path / "$(touch injected); known hosts"
    known.touch()
    path.write_text(json.dumps({**config, "known_hosts_file": str(known)}))
    proxy = relay_client.proxy_command(path)
    # Exercise the shell boundary without executing SSH or any network request.
    result = subprocess.run(
        ["/bin/sh", "-c", "set -- " + proxy + '; printf "%s\\n" "$@"'],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert result.stdout.splitlines() == shlex.split(proxy)
    assert not (tmp_path / "injected").exists()
    assert "StrictHostKeyChecking=yes" in result.stdout.splitlines()
    assert "UserKnownHostsFile=" + str(known) in result.stdout.splitlines()
    assert "127.0.0.1:22073" in result.stdout.splitlines()

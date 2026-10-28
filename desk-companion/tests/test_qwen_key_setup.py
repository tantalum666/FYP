import importlib.util
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location(
    "qwen_key_setup", Path(__file__).parents[1] / "scripts" / "configure_qwen.py"
)
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)
KEY = "fixture_" * 4


def test_private_staging_stays_disabled_and_status_never_exposes_key(tmp_path):
    target = tmp_path / "private" / "qwen.env"
    setup.write_config(target, KEY)
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    status = setup.safe_status(target)
    assert status["credential_present"] is True
    assert status["provider_enabled"] is False
    assert KEY not in json.dumps(status)
    assert not list(target.parent.glob(".qwen-setup-*"))


def test_existing_config_is_preserved(tmp_path):
    target = tmp_path / "qwen.env"
    setup.write_config(target, KEY)
    before = target.read_bytes()
    with pytest.raises(FileExistsError):
        setup.write_config(target, KEY + "replacement")
    assert target.read_bytes() == before
    assert not list(tmp_path.glob(".qwen-setup-*"))


def test_ancestor_symlink_is_refused(tmp_path):
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(OSError):
        setup.write_config(alias / "private" / "qwen.env", KEY)
    assert not list(real.iterdir())


def test_destination_symlink_is_preserved(tmp_path):
    victim = tmp_path / "other.env"
    victim.write_text("preserve")
    target = tmp_path / "qwen.env"
    target.symlink_to(victim)
    with pytest.raises(FileExistsError):
        setup.write_config(target, KEY)
    assert victim.read_text() == "preserve"
    assert target.is_symlink()


def test_env_injection_is_refused_without_echo(tmp_path):
    target = tmp_path / "qwen.env"
    value = KEY + "\nDESK_VOICE_PROVIDER=qwen_audio"
    with pytest.raises(setup.SetupError) as caught:
        setup.write_config(target, value)
    assert KEY not in str(caught.value)
    assert not target.exists()


def test_world_readable_config_is_refused(tmp_path):
    target = tmp_path / "qwen.env"
    setup.write_config(target, KEY)
    os.chmod(target, 0o644)
    with pytest.raises(setup.SetupError):
        setup.safe_status(target)


def test_native_cancel_does_not_return_a_key(tmp_path, monkeypatch):
    monkeypatch.setattr(setup.sys, "platform", "darwin")
    monkeypatch.setattr(
        setup.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="(-128)"),
    )
    assert setup.read_native_key(tmp_path / "qwen.env") is None

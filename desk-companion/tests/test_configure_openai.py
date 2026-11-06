import stat

import pytest

from scripts.configure_openai import configure


def inputs(tmp_path):
    key = (tmp_path / "project.env").resolve()
    key.write_text("OPENAI_API_KEY=sk-fixture-private-project-key\n")
    key.chmod(0o600)
    runtime = (tmp_path / "state").resolve()
    runtime.mkdir(mode=0o700)
    return runtime, key


def test_configure_references_key_and_preserves_unrelated_settings(tmp_path):
    runtime, key = inputs(tmp_path)
    env = runtime / "service.env"
    env.write_text(
        "DESK_VOICE_PROVIDER=qwen_omni\nDESK_VOICE_API_KEY=old-vendor\nDESK_NATIVE_CLIENTS=1\n"
    )
    env.chmod(0o600)
    result = configure(runtime, key, region_unavailable=True)
    body = env.read_text()
    assert "DESK_NATIVE_CLIENTS=1" in body and 'DESK_VOICE_PROVIDER="openai_realtime"' in body
    assert 'DESK_OPENAI_REGION_UNSUPPORTED="1"' in body
    assert "old-vendor" not in body and "sk-fixture-private-project-key" not in body
    assert stat.S_IMODE(env.stat().st_mode) == 0o600 and result["model_requests"] == 0
    assert key.read_text() == "OPENAI_API_KEY=sk-fixture-private-project-key\n"


def test_configure_refuses_unsafe_destination_and_key(tmp_path):
    runtime, key = inputs(tmp_path)
    other = tmp_path / "other"
    other.write_text("preserve")
    (runtime / "service.env").symlink_to(other)
    with pytest.raises(ValueError):
        configure(runtime, key)
    assert other.read_text() == "preserve"
    (runtime / "service.env").unlink()
    key.chmod(0o644)
    with pytest.raises(ValueError):
        configure(runtime, key)
    assert not (runtime / "service.env").exists()

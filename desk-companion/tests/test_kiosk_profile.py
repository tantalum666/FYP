import json
import stat

import pytest

from scripts.pi.kiosk_profile import prepare


def test_kiosk_has_private_permissions_and_does_not_save_browser_passwords(tmp_path):
    root = prepare(tmp_path / "kiosk")
    prefs = root / "Default/Preferences"
    value = json.loads(prefs.read_text())
    assert value["credentials_enable_service"] is False
    assert value["profile"]["password_manager_enabled"] is False
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(prefs.stat().st_mode) == 0o600
    value["profile"]["content_settings"] = {"keep": True}
    prefs.write_text(json.dumps(value))
    prepare(root)
    assert json.loads(prefs.read_text())["profile"]["content_settings"] == {"keep": True}


def test_ordinary_profile_or_link_is_not_adopted(tmp_path):
    with pytest.raises(ValueError):
        prepare(tmp_path / "personal-chrome")
    other = tmp_path / "other"
    other.mkdir()
    (tmp_path / "kiosk").symlink_to(other)
    with pytest.raises(ValueError):
        prepare(tmp_path / "kiosk")

"""Check the actual systemd dependency graph; no units are installed or started."""

from pathlib import Path
import shutil
import subprocess

import pytest


pytestmark = pytest.mark.skipif(
    shutil.which("systemd-analyze") is None,
    reason="Dependency graph verification requires a Linux systemd host",
)
SOURCE = Path(__file__).resolve().parents[1] / "scripts/pi"


def verify_pair(tmp_path, *, legacy_timer=False):
    paths = []
    for name in ("desk-auto-wake.service", "desk-auto-wake.timer"):
        text = (SOURCE / name).read_text()
        if legacy_timer and name.endswith(".timer"):
            text = text.replace("DefaultDependencies=no\n", "").replace(
                "Before=sysinit.target timers.target shutdown.target\n", ""
            )
        path = tmp_path / name
        path.write_text(text)
        paths.append(str(path))
    return subprocess.run(
        ["systemd-analyze", "verify", *paths], capture_output=True, text=True, timeout=15
    )


def test_early_alarm_and_periodic_timer_have_no_ordering_cycle(tmp_path):
    result = verify_pair(tmp_path)
    assert result.returncode == 0, result.stderr


def test_legacy_timer_after_sysinit_recreates_the_regression(tmp_path):
    result = verify_pair(tmp_path, legacy_timer=True)
    assert result.returncode != 0 and "cycle" in result.stderr.lower(), result.stderr

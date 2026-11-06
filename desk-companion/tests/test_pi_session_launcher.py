import os
from pathlib import Path
import shutil
import subprocess


def test_graphical_session_launches_kiosk_from_its_own_release(tmp_path):
    root = tmp_path / "release with spaces"
    scripts = root / "scripts"
    (scripts / "pi").mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / "scripts/pi/session.sh"
    shutil.copyfile(source, scripts / "pi/session.sh")
    (scripts / "kiosk.sh").write_text('#!/bin/sh\nprintf "kiosk-ready\\n" >> "$CHECK_LOG"\n')
    (scripts / "kiosk.sh").chmod(0o755)
    bins = tmp_path / "bin"
    bins.mkdir()
    for name in ["systemctl", "dbus-update-activation-environment"]:
        path = bins / name
        path.write_text('#!/bin/sh\nprintf "%s %s\\n" "' + name + '" "$*" >> "$CHECK_LOG"\n')
        path.chmod(0o755)
    log = tmp_path / "calls.txt"
    subprocess.run(
        ["/bin/sh", str(scripts / "pi/session.sh")], check=True,
        env={**os.environ, "PATH": str(bins) + os.pathsep + os.environ["PATH"], "CHECK_LOG": str(log)},
    )
    calls = log.read_text()
    assert "systemctl --user restart desk-companion.service" in calls
    assert calls.endswith("kiosk-ready\n")

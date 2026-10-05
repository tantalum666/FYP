"""Prepare user-level Linux service files. Defaults to a reviewable dry run.

--install writes this application's files only. --enable explicitly starts the API.
Camera, voice and actuator workers remain opt-in and are not started by this tool.
"""

import argparse
import os
import platform
import subprocess
from pathlib import Path


def service(root, description, command, after="network-online.target"):
    def quote(value):
        return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'

    return f"""[Unit]
Description={description}
After={after}

[Service]
Type=simple
WorkingDirectory={quote(root)}
Environment=PYTHONUNBUFFERED=1
Environment={quote("PYTHONPATH=" + str(root / "backend"))}
EnvironmentFile={quote("-" + str(root / ".runtime/service.env"))}
ExecStart={" ".join(quote(v) for v in command)}
Restart=on-failure
RestartSec=3
UMask=0077
NoNewPrivileges=true

[Install]
WantedBy=default.target
"""


def render(root):
    python = root / ".venv/bin/python"
    return {
        "desk-companion.service": service(
            root,
            "Desk Companion local API",
            [
                root / ".venv/bin/uvicorn",
                "desk.app:create_app",
                "--factory",
                "--app-dir",
                root / "backend",
                "--host",
                "127.0.0.1",
                "--port",
                "8831",
                "--workers",
                "1",
                "--no-access-log",
            ],
        ),
        "desk-camera.service": service(
            root,
            "Desk Companion optional camera worker",
            [python, "-m", "desk.agents.camera", "--camera", "0"],
            "desk-companion.service",
        ),
        "desk-voice.service": service(
            root,
            "Desk Companion optional wake and voice worker",
            [python, "-m", "desk.agents.voice"],
            "desk-companion.service",
        ),
        "desk-outputs.service": service(
            root,
            "Desk Companion optional commissioned output worker",
            [
                python,
                "-m",
                "desk.agents.outputs",
                "--driver",
                "pca9685",
                "--config",
                root / ".runtime/outputs.json",
            ],
            "desk-companion.service",
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--enable", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    units = render(root)
    if not args.install:
        target = root / ".runtime/linux-preview"
        target.mkdir(parents=True, exist_ok=True)
        for name, text in units.items():
            (target / name).write_text(text)
        print("Reviewable service files: " + str(target))
        return
    if platform.system() != "Linux":
        raise SystemExit("Installation only runs on Linux. Use the default preview on macOS.")
    if not (root / "frontend/dist/index.html").is_file() or not python_exists(root):
        raise SystemExit("Install locked dependencies and build the frontend first.")
    target = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "systemd/user"
    target.mkdir(parents=True, exist_ok=True)
    for name, text in units.items():
        path = target / name
        if path.exists() and path.read_text() != text:
            path.with_suffix(".service.previous").write_text(path.read_text())
        path.write_text(text)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    if args.enable:
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", "desk-companion.service"], check=True
        )
    print("API unit installed. Optional camera, voice and output units remain disabled.")


def python_exists(root):
    return (root / ".venv/bin/python").is_file()


if __name__ == "__main__":
    main()

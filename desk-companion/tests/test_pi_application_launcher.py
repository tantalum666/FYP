"""Exercise resource admission without starting an engine or changing the host."""

import json
import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.skipif(os.getuid() == 0, reason="Pi launcher requires an ordinary owner")
@pytest.mark.parametrize(
    "memory,opt_in,expected", [(False, False, 2), (False, True, 0), (True, False, 0)]
)
def test_missing_memory_controller_requires_explicit_operator_choice(
    tmp_path, memory, opt_in, expected
):
    runtime = tmp_path / ".local/share/desk-companion-apps"
    for name in ("support", "inputs", "workspace"):
        (runtime / name).mkdir(parents=True)
    (runtime / "chromium-seccomp.json").write_text("{}")
    binary = tmp_path / "bin"
    binary.mkdir()
    stub = binary / "podman"
    stub.write_text("""#!/usr/bin/env python3
import json,os,sys,pathlib
args=sys.argv[1:]
if 'info' in args:
 print('true' if 'Rootless' in args[-1] else os.environ['QA_CONTROLLERS'])
elif 'inspect' in args: print('arm64')
elif 'exists' in args: sys.exit(1)
elif 'run' in args: pathlib.Path(os.environ['QA_COMMAND']).write_text(json.dumps(args))
else: sys.exit(99)
""")
    stub.chmod(0o755)
    result_file = tmp_path / "command.json"
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "PATH": str(binary) + os.pathsep + os.environ["PATH"],
        "QA_CONTROLLERS": json.dumps(["cpu", "pids"] + (["memory"] if memory else [])),
        "QA_COMMAND": str(result_file),
        "DESK_APP_ALLOW_UNBOUNDED_MEMORY": "1" if opt_in else "0",
    }
    script = Path(__file__).resolve().parents[1] / "scripts/pi/start_applications.sh"
    result = subprocess.run(
        ["sh", str(script), "sha256:" + "a" * 64], env=env, capture_output=True, text=True
    )
    assert result.returncode == expected, result.stderr
    if expected:
        assert not result_file.exists()
    else:
        args = json.loads(result_file.read_text())
        assert ("--memory" in args) == memory
        assert args[args.index("--network") + 1] == "none"
        assert "--pull=never" in args and "--userns=keep-id:uid=501,gid=1000" in args
        assert args[args.index("--pids-limit") + 1] == "256"
        assert "--init" in args and "--http-proxy=false" in args

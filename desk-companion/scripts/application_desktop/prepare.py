#!/usr/bin/env python3
"""Prepare only the disposable application mount; never copy keys or the oracle.

Downloads a pinned Moby seccomp profile and preserves its rules except for three
namespace syscalls required by Chromium's own sandbox. Does not start a VM or
change Docker's active context. See docs/application-execution.md for startup.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from urllib.request import urlopen

PROJECT = Path(__file__).resolve().parents[2]
REVISION = "4b8214fc4971e06172938a1f1554ccff6647ee80"
PROFILE_HASH = "a894b5730caa168d88da7fffe8ace974ad05fb84547e1766fa879d75d3ac6ba2"
PROFILE_URL = f"https://raw.githubusercontent.com/moby/profiles/{REVISION}/seccomp/default.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=PROJECT / ".runtime/app-desktop")
    parser.add_argument("--copy-fictional-inputs", action="store_true")
    args = parser.parse_args()
    root = args.runtime.absolute()
    if root.resolve() != root or not root.is_relative_to(PROJECT / ".runtime"):
        parser.error("Use a real directory below this checkout's .runtime")
    for name in ("support", "inputs", "workspace"):
        directory = root / name
        if directory.is_symlink() or directory.resolve() != directory.absolute():
            parser.error("Application mount directories must not be symbolic links")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    cache = root / "moby-default.json"
    if cache.exists():
        body = cache.read_bytes()
    else:
        with urlopen(PROFILE_URL, timeout=20) as response:
            body = response.read(100001)
        if len(body) > 100000:
            raise ValueError("Unexpected seccomp profile size")
    profile = json.loads(body)
    canonical = json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != PROFILE_HASH:
        raise ValueError("Pinned upstream seccomp content differs; review before using it")
    cache.write_bytes(body)
    profile["syscalls"].append(
        {
            "names": ["clone", "unshare", "setns"],
            "action": "SCMP_ACT_ALLOW",
            "comment": "Chromium sandbox namespaces inside the isolated FYP VM; no added capabilities.",
        }
    )
    (root / "chromium-seccomp.json").write_text(json.dumps(profile, indent=2) + "\n")
    for name in ("application_bridge.py", "application_desktop.py"):
        shutil.copyfile(PROJECT / "backend/desk" / name, root / "support" / name)
    if args.copy_fictional_inputs:
        source = PROJECT / "evals/app_workflow_v1/inputs"
        # Refuse to replace an operator's different input pack on a later run.
        expected = {
            str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*") if p.is_file()
        }
        current = {
            str(p.relative_to(root / "inputs")): p.read_bytes()
            for p in (root / "inputs").rglob("*")
            if p.is_file()
        }
        if current and current != expected:
            raise ValueError("Input directory already contains a different dataset")
        shutil.copytree(source, root / "inputs", dirs_exist_ok=True)
    print(
        json.dumps(
            {
                "prepared": str(root),
                "source_profile_revision": REVISION,
                "source_profile_sha256_canonical": PROFILE_HASH,
                "started": False,
            }
        )
    )


if __name__ == "__main__":
    main()

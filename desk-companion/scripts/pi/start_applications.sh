#!/bin/sh
# Start the separately prepared, offline application desktop as the Pi user.
# Do not run with sudo. Image and dependencies must already be installed.
set -eu
if [ "$(id -u)" = 0 ]; then
  echo 'Run as the desktop owner, without sudo.' >&2
  exit 2
fi
image=${1:?Pass the inspected local sha256 image ID}
image_uid=${2:-501}
image_gid=${3:-1000}
runtime="$HOME/.local/share/desk-companion-apps"
python3 - "$image" "$image_uid" "$image_gid" "$runtime" <<'PY'
import os, re, sys
from pathlib import Path
image, uid, gid, raw = sys.argv[1:]
if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
    raise SystemExit('Use an exact inspected image ID; no tag or remote pull')
if not all(v.isdecimal() and 0 < int(v) < 65536 for v in (uid, gid)):
    raise SystemExit('The image desktop user must be non-root')
root = Path(raw)
for path in [root, *(root / p for p in ('support', 'inputs', 'workspace', 'chromium-seccomp.json'))]:
    if path.resolve() != path or path.stat().st_uid != os.getuid():
        raise SystemExit('Use real, owner-controlled runtime paths')
PY
test "$(podman --remote=false info --format '{{.Host.Security.Rootless}}')" = true
test "$(podman --remote=false image inspect "$image" --format '{{.Architecture}}')" = arm64
# A prior instance may hold unfinished files; never replace it implicitly.
if podman --remote=false container exists desk-applications; then
  echo 'desk-applications already exists; inspect it and start/restart that exact container.' >&2
  exit 2
fi
exec podman --remote=false run -d --pull=never --name desk-applications \
  --label fyp.executor=applications --network none \
  --user desk --userns="keep-id:uid=$image_uid,gid=$image_gid" \
  --shm-size 256m --memory 2g --cpus 2 --pids-limit 256 \
  --security-opt "seccomp=$runtime/chromium-seccomp.json" \
  --mount "type=bind,src=$runtime/support,dst=/opt/desk,readonly" \
  --mount "type=bind,src=$runtime/inputs,dst=/inputs,readonly" \
  --mount "type=bind,src=$runtime/workspace,dst=/workspace" \
  "$image"

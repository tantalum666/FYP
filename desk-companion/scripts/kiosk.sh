#!/usr/bin/env bash
set -euo pipefail
if [[ "$(uname -s)" != Linux ]]; then
  echo "This launcher is for the Linux desk display." >&2
  exit 1
fi
desk_url="${DESK_KIOSK_URL:-http://127.0.0.1:8831/?surface=device}"
desk_state="${XDG_STATE_HOME:-$HOME/.local/state}/desk-companion"
desk_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$desk_state"
chmod 700 "$desk_state"
python3 "$desk_root/scripts/pi/kiosk_profile.py" "$desk_state/kiosk"
if command -v chromium >/dev/null; then
  desk_browser="$(command -v chromium)"
elif command -v chromium-browser >/dev/null; then
  desk_browser="$(command -v chromium-browser)"
else
  echo "Install Chromium for this Linux distribution first." >&2
  exit 1
fi
# On X11, keep only this logged-in kiosk session awake. No system-wide changes.
if [[ "${XDG_SESSION_TYPE:-}" == x11 ]] && command -v xset >/dev/null; then
  xset s off || true
  xset -dpms || true
fi
# This profile contains only the local display; do not save browser passwords or
# attach a personal profile. FYP's own OAuth tokens stay in its encrypted vault.
exec "$desk_browser" --kiosk --no-first-run --disable-session-crashed-bubble --disable-sync --password-store=basic --user-data-dir="$desk_state/kiosk" "$desk_url"

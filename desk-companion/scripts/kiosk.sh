#!/usr/bin/env bash
set -euo pipefail
if [[ "$(uname -s)" != Linux ]]; then
  echo "This launcher is for the Linux desk display." >&2
  exit 1
fi
desk_url="${DESK_KIOSK_URL:-http://127.0.0.1:8831/?surface=device}"
desk_state="${XDG_STATE_HOME:-$HOME/.local/state}/desk-companion"
mkdir -p "$desk_state/chromium"
chmod 700 "$desk_state" "$desk_state/chromium"
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
exec "$desk_browser" --kiosk --no-first-run --disable-session-crashed-bubble --user-data-dir="$desk_state/chromium" "$desk_url"

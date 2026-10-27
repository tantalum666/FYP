#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
if [[ ! -d .venv || ! -d frontend/node_modules ]]; then
  echo "Install dependencies first: uv sync --frozen; then npm ci in frontend/." >&2
  exit 1
fi
# The port check uses the venv created by `uv sync`. A later shell does not
# need `uv` itself on PATH.
.venv/bin/python - <<'PY'
import socket
for port in (8831, 5190):
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"Port {port} is in use. An existing preview may already be running.")
PY
api_pid=""
ui_pid=""
cleanup() {
  trap - EXIT INT TERM
  [[ -z "$ui_pid" ]] || kill "$ui_pid" 2>/dev/null || true
  [[ -z "$api_pid" ]] || kill "$api_pid" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM
.venv/bin/uvicorn desk.app:create_app --factory --app-dir backend --host 127.0.0.1 --port 8831 &
api_pid=$!
node frontend/node_modules/vite/bin/vite.js frontend --host 127.0.0.1 --port 5190 --strictPort &
ui_pid=$!
echo "Desk Companion: http://127.0.0.1:5190/"
echo "Account: owner. Local password: .runtime/credentials.json"
while kill -0 "$api_pid" 2>/dev/null && kill -0 "$ui_pid" 2>/dev/null; do
  sleep 1
done
exit 1

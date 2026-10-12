#!/usr/bin/env bash
# Frozen software checks. No provider account, device, or private runtime is needed.
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"

install=0
offline=0
check_assets=1
for argument in "$@"; do
  case "$argument" in
    --install) install=1 ;;
    --offline) offline=1 ;;
    --skip-assets) check_assets=0 ;;
    --help)
      echo "Usage: scripts/check_software.sh [--install] [--offline] [--skip-assets]"
      echo "--install: install frozen dependencies; --offline: require existing caches."
      echo "--skip-assets: explicitly omit bundled-image hash checks for partial checkouts."
      exit 0
      ;;
    *) echo "Unknown option: $argument" >&2; exit 2 ;;
  esac
done

for tool in uv node npm; do
  command -v "$tool" >/dev/null || { echo "Required tool is missing: $tool" >&2; exit 1; }
done
node --input-type=module -e '
const [major, minor] = process.versions.node.split(".").map(Number);
if (major < 22 || (major === 22 && minor < 12)) {
  throw new Error("Node 22.12 or newer is required");
}'

# Clear inherited app configuration in this child shell, without reading secret values.
while IFS= read -r name; do
  unset "$name"
done < <(compgen -A variable DESK_ || true)
export DESK_TEXT_PROVIDER=none DESK_VOICE_PROVIDER=none DESK_TEXT_BACKGROUND=0
export DESK_COMPUTER_ENABLED=0 DESK_ALLOW_REPLAY=0
export PYTHONDONTWRITEBYTECODE=1
if ((offline)); then
  export UV_OFFLINE=1 npm_config_offline=true
fi
runtime_dir="$(mktemp -d "${TMPDIR:-/tmp}/desk-software-check.XXXXXXXX")"
trap 'rm -rf -- "$runtime_dir"' EXIT
export DESK_RUNTIME_DIR="$runtime_dir"

if ((install)); then
  uv_flags=(--frozen)
  npm_flags=(--ignore-scripts --no-audit --no-fund)
  if ((offline)); then
    uv_flags+=(--offline)
    npm_flags+=(--offline)
  fi
  uv sync "${uv_flags[@]}"
  (cd frontend && npm ci "${npm_flags[@]}")
fi
if [[ ! -x .venv/bin/python || ! -d frontend/node_modules ]]; then
  echo "Install locked dependencies first, or use --install." >&2
  exit 1
fi

if ((check_assets)); then
  uv run --no-sync python scripts/check_assets.py
else
  echo "PARTIAL CHECKOUT: bundled asset hash checks explicitly skipped."
fi
uv run --no-sync ruff check backend scripts tests
uv run --no-sync pytest -q
(cd frontend && npm test && npm run build)
echo "Software checks passed. Live providers, browser interactions and hardware are separate checks."

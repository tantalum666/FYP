#!/bin/bash
set -euo pipefail
export DESK_PI_LINK=lan
export DESK_PI_HOST="${DESK_PI_HOST:-desk-companion.local}"
desk_connector="$(dirname "$0")/connect_mac.command"
if [[ ! -f "$desk_connector" ]]; then
  desk_connector="$(dirname "$0")/Connect-Pi-from-Mac.command"
fi
exec /bin/bash "$desk_connector"

#!/bin/bash
set -euo pipefail
export DESK_PI_LINK=relay
exec /bin/bash "$(dirname "$0")/connect_mac.command"

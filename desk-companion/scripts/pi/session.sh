#!/bin/sh
set -eu
# Resolve the active release, including when it is outside the original /opt path.
desk_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
# Inherit only this graphical session; the API remains a non-root user service.
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_SESSION_TYPE DBUS_SESSION_BUS_ADDRESS
dbus-update-activation-environment --systemd DISPLAY WAYLAND_DISPLAY XDG_SESSION_TYPE
systemctl --user restart desk-companion.service
exec "$desk_root/scripts/kiosk.sh"

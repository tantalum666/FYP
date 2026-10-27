#!/bin/sh
set -eu
# Inherit only this graphical session; the API remains a non-root user service.
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_SESSION_TYPE DBUS_SESSION_BUS_ADDRESS
dbus-update-activation-environment --systemd DISPLAY WAYLAND_DISPLAY XDG_SESSION_TYPE
systemctl --user restart desk-companion.service
exec /usr/bin/python3 /opt/desk-companion/scripts/pi/welcome.py

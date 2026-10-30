#!/bin/sh
set -eu
# This display belongs only to this disposable container. Docker restart leaves
# its writable /tmp layer intact after terminating the former X server.
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1440x1000x24 -nolisten tcp &
until xdpyinfo >/dev/null 2>&1; do sleep 0.1; done
openbox >/tmp/desk-openbox.log 2>&1 &
x11vnc -display :99 -localhost -forever -shared -nopw -quiet >/tmp/desk-vnc.log 2>&1 &
websockify --web=/usr/share/novnc 6080 localhost:5900 >/tmp/desk-websockify.log 2>&1 &
exec dbus-run-session -- python3 /opt/desk/application_desktop.py

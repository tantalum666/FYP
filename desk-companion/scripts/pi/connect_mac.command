#!/bin/bash
set -euo pipefail
desk_keys="$HOME/.config/desk-companion/pi5-usb"
desk_host="${DESK_PI_HOST:-10.12.194.1}"
desk_link="${DESK_PI_LINK:-usb}"
desk_pid=""
cleanup() {
  if [[ -n "$desk_pid" ]]; then kill "$desk_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM
if [[ ! -r "$desk_keys/id_ed25519" ]]; then
  echo "Missing the private pairing key for this Pi: $desk_keys/id_ed25519"
  exit 1
fi
for desk_port in 8891 5901; do
  if /usr/sbin/lsof -nP -iTCP:"$desk_port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $desk_port is already in use. Close the earlier Pi connection first."
    exit 1
  fi
done
if [[ "$desk_link" == lan ]]; then
  desk_host=$(/usr/bin/python3 - "$desk_host" <<'PY'
import ipaddress, re, socket, subprocess, sys
addresses = {r[4][0] for r in socket.getaddrinfo(sys.argv[1], 22, socket.AF_INET)}
for value in sorted(addresses):
    ip = ipaddress.IPv4Address(value)
    if ip.is_loopback or ip.is_multicast or ip.is_unspecified:
        continue
    route = subprocess.run(['/sbin/route', '-n', 'get', value], capture_output=True, text=True)
    match = re.search(r'interface:\s+(en\d+)\b', route.stdout)
    if not match:
        continue
    config = subprocess.check_output(['/sbin/ifconfig', match[1]], text=True)
    local = re.search(r'inet (\S+) netmask (0x[0-9a-f]+)', config)
    if local:
        mask = str(ipaddress.IPv4Address(int(local[2], 16)))
        network = ipaddress.IPv4Network(local[1]+'/'+mask, strict=False)
        if ip in network and value != local[1]:
            print(value)
            break
else:
    raise SystemExit('No Pi address on the Mac directly connected LAN; no SSH attempted.')
PY
  )
elif [[ "$desk_link" != usb ]]; then
  echo "DESK_PI_LINK must be usb or lan."
  exit 1
fi
desk_interface=$(/sbin/route -n get "$desk_host" 2>/dev/null | /usr/bin/awk '/interface:/ {print $2}')
desk_wired=$(/usr/sbin/networksetup -listallhardwareports | /usr/bin/awk \
  -v target="$desk_interface" '/^Hardware Port:/ {name=$0} /^Device:/ && $2==target {print name}')
if [[ "$desk_link" == usb && ! "$desk_wired" =~ (USB|Ethernet|Gadget|Raspberry) ]]; then
  echo "The USB network is not ready. No SSH connection was attempted over Wi-Fi or VPN."
  echo "Wait for the first-boot restart, then check the data cable and try again."
  exit 1
fi
echo "Connecting to the Pi over $desk_link using the existing paired SSH key."
/usr/bin/ssh -F /dev/null -i "$desk_keys/id_ed25519" \
  -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile="$desk_keys/known_hosts" \
  -o HostKeyAlias=desk-companion-pi5-usb -o ProxyCommand=none \
  -o BatchMode=yes -o ConnectTimeout=15 -o ConnectionAttempts=2 \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
  -N -L 127.0.0.1:8891:127.0.0.1:8831 -L 127.0.0.1:5901:127.0.0.1:5900 \
  "desk@$desk_host" &
desk_pid=$!
desk_ready=0
desk_desktop=0
for ((desk_try=0; desk_try<35; desk_try++)); do
  if ! kill -0 "$desk_pid" 2>/dev/null; then
    wait "$desk_pid" || true
    echo "The Pi is not reachable yet. Check the data cable, power and first-boot restart."
    exit 1
  fi
  if /usr/bin/curl --noproxy '*' --silent --fail --max-time 1 http://127.0.0.1:8891/api/health >/dev/null; then
    desk_ready=1
  fi
  desk_banner=$(/usr/bin/nc -G 1 -w 1 127.0.0.1 5901 </dev/null 2>/dev/null | /usr/bin/head -c 12 || true)
  if [[ "$desk_banner" == RFB* ]]; then
    desk_desktop=1
  fi
  if [[ "$desk_ready" == 1 || "$desk_desktop" == 1 ]]; then
    break
  fi
  sleep 1
done
if [[ "$desk_ready" != 1 ]]; then
  echo "SSH connected; the app is not ready yet. Desktop access remains available for recovery."
fi
echo "Connected. Closing this terminal or pressing Ctrl-C ends the tunnels."
echo "Web: http://127.0.0.1:8891/   Desktop: vnc://127.0.0.1:5901"
if [[ -r "$HOME/.config/desk-companion/pi5-classroom/desktop-login.json" ]]; then
  echo "Screen Sharing password: ~/.config/desk-companion/pi5-classroom/desktop-login.json"
fi
if [[ "${DESK_PI_NO_OPEN:-0}" != 1 ]]; then
  if [[ "$desk_ready" == 1 ]]; then /usr/bin/open 'http://127.0.0.1:8891/?lang=zh'; fi
  /usr/bin/open 'vnc://127.0.0.1:5901'
fi
wait "$desk_pid"

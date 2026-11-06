# Pi networking across home, classroom and dorm

**5 November: dorm wired DHCP, fixed443 relay and original Pi SSH authentication passed, including recovery after the owner's normal restart. Mac HTTP login/core API and VNC protocol passed. Home/classroom profiles remain; classroom wired still requires a field test. Power stability remains open. [Current QA](../../output/qa/2026-11-05-pi-443-transport/verification.md).**

31 October 2026. The owner resumed Pi work and specified this arrangement:

| Place | Prepared connection | Priority |
|---|---|---|
| Home | Owner-supplied Wi-Fi, stored privately as `FYP-Home` | Route metric 50 |
| Classroom | Previously working `NETGEAR02` Wi-Fi plus ordinary wired DHCP | Wired metric 100; classroom Wi-Fi 600 |
| Dorm | Ordinary wired DHCP | `FYP-Wired`, autoconnect on `eth0` |

The old Student/Halls credentials remain on the Pi for manual diagnosis, but their automatic connection attempts are disabled. Classroom Wi-Fi remains enabled. No campus Ethernet authentication, captive-portal requirement or network-isolation rule is presumed to be solved by writing a DHCP profile; those need a visit and actual connection evidence.

## What is installed

[`setup_network_access.py`](../scripts/pi/setup_network_access.py) loads the home and wired NetworkManager profiles into the existing OS. It retains the original `desk` user, paired SSH key, host keys, app installation and data. It adds a NetworkManager dispatcher callback for connection-up/down and IPv4 lease changes, and replaces only the project's own `desk_usb_ssh` nft table.

SSH remains public-key-only. Its allowed sources are the directly attached private IPv4 networks on wired `eth0` and explicitly known Wi-Fi profiles on `wlan0`. Networks broader than /20, public networks, link-local addresses, down interfaces, unrelated tunnels and unselected Wi-Fi are refused. USB and loopback access remain. Other firewall tables are not flushed; app/VNC continue listening on Pi loopback and are reached through SSH forwarding.

This avoids carrying the old classroom-only subnet rule into every location. It does not bridge separate campus VLANs or make a sleeping/disconnected computer reachable. Mac and Pi must have a permitted route between them; the existing connector checks the direct LAN rather than trying through a VPN by accident. An explicit `allow_routed_owner` policy can add the selected private owner IPv4/32 on a live private eth0 link; it does not admit that owner’s whole VLAN. It defaults off and retains the existing key-only authentication. The generic Mac connector still checks a direct subnet; routed diagnosis must bind its SSH transport to the real network interface and require the recorded host identity. A VPS relay is a separate option if actual campus isolation makes it necessary.

The home session used `CN`; the current dorm seed explicitly selects `HK`, independently read back from the running regulatory domain and boot argument. `--country` accepts only CN/HK. In HK, setup preserves the home profile without forcing a40-second home activation attempt. Confirm the physical country when moving location. Wired DHCP is independent of that setting. No MAC cloning, account guessing, router admin changes or campus-security bypass is included.

## Card update and rollback

[`prepare_network_sd.py`](../scripts/pi/prepare_network_sd.py) reads Wi-Fi credentials from an owner-private local file, never from command arguments. It verifies the original removable card using capacity, boot-volume UUID and Linux root PARTUUID. The Mac's internal SD reader reports Internal=true and RemovableMedia=true, so disk-number or external-only guesses are not used.

Preparation saves private copies of the five existing boot files. `--apply` changes `user-data` and `meta-data`; when the optional fixed443 transport is selected, it also writes the verified `desk-relay-mihomo.gz` archive. Exact bytes are independently read back, and `network-config`, `config.txt` and `cmdline.txt` remain unchanged. A later write failure restores the original seed and previous archive state. The Mac does not write the Linux/application partition. A new NoCloud instance runs the network update once; users/SSH-host-key regeneration, package updates and reinstall are disabled.

The rendered boot seed contains a Wi-Fi credential and must remain private, like the existing personal image and NetworkManager files. Repository evidence contains only redacted status and source code. Private backups and credentials are under the owner's `~/.config/desk-companion/pi5-home/`, not Git. The Pi also preserves its original guard/unit as `.before-portable-network` files.

## Connect and verify

Use the existing paired-key launcher, with `DESK_PI_LINK=lan` and the Pi's observed address or `desk-companion.local`. The Mac forwards web port8891 to Pi127.0.0.1:8831 and desktop5901 to Pi127.0.0.1:5900. The known SSH host identity must match; do not delete it to bypass a mismatch.

The initial update emits nonce-filtered, nonsecret address/status packets to the Mac for one bounded startup window. A packet is only a discovery hint, not authenticated completion. Confirm the pinned SSH host, actual active profile/IP, service listeners and app health independently. If no packet arrives, inspect the actual LAN/mDNS or the card's `desk-network-status.json`; do not infer Wi-Fi success from the prepared files.

**Status freshness fix, 4 November:** the previously installed helper only wrote boot status during setup. New source writes it on guard/NetworkManager events and includes the boot ID; UDP delivery failure does not prevent local recording. Authenticated readback after5November restart confirms the new boot ID and active wired profile. Transport/install receipts remain one-time historical records; current service state and original-key SSH must be checked separately. Setup discovery defaults to60seconds, accepts an explicit maximum600seconds, and stops on its monotonic deadline. Later events send a single diagnostic packet. Saved timestamps may precede clock synchronization.

Historical home acceptance is in the [31October QA](../../output/qa/2026-10-31-pi-home-resume/verification.md). The Pi has now separately received the backed-up [5November mainabf6387 update](../../output/qa/2026-11-05-pi-runtime-upgrade/verification.md). No paid-model budget is reopened by restoring networking or updating the app.

## Live acceptance on 31 October

The owner reinserted the original card and powered the Pi without Ethernet. Its home profile connected; the supplied SSID was compared privately, the original SSH host identity matched, and the actual app and VNC listeners remained on loopback. Mac-side owner login, rendered Alice/device page and Screen Sharing all passed. NetworkManager readback confirms the table above, including disabled Student/Halls autoconnect. No cable was present at the last observation; wired DHCP and school reachability remain untested.

The current home address was192.168.0.105 after profile activation; mDNS initially reported a different lease, so this is not a static-IP setting. The running tunnel uses the existing paired-key connector and local ports8891/5901. The initial diagnostic UDP window had no packet because discovery continued separately; its empty result did not establish a failed boot.

Two OS-level observations remain explicit: cloud-init finished with no fatal errors but a recoverable missing `cc_netplan_nm_patch` warning, matching an [official issue report](https://github.com/raspberrypi/trixie-feedback/issues/45); `raspi-config` country command returned1, while both the global regulatory domain and persisted `cfg80211.ieee80211_regdom=CN` argument were read back. Mac did not modify cmdline.txt; the authorized Pi-side country setter did. The warning was not concealed by changing vendor cloud-init configuration or rerunning provisioning.

The31October Pi-local Chromium run produced kernel-confirmed undervoltage. Fresh5November boots also recorded undervoltage; the latest inspected post-restart interval had11 episodes followed by normalization, with a later0x50000 snapshot showing no active flags. Boot-reported capability remains3000mA, not measured current draw or proof of the physical PSU. Owner confirms the official27W supply and asks to prioritize software. Sustained load is unverified; no current-limit override or warning suppression is used. [Official power guidance](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply), [status-bit meanings](https://www.raspberrypi.com/documentation/computers/os.html#get_throttled).

## Owner relay and interrupted setup

The optional [owner-hosted relay and verified bootstrap](pi-owner-relay.md) preserve all three local profile paths. A fresh card readback confirmed wired DHCP and the intended source rule. A later incomplete relay installation exposed the need to verify actual root-file contents and setup receipts, not only FAT seed bytes or process exit0. The new recovery is locally validated; Pi SSH and classroom/mainland field tests are still distinct.

## Primary references

- [Raspberry Pi cloud-init boot files](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/)
- [Raspberry Pi configuration](https://www.raspberrypi.com/documentation/computers/configuration.html)
- [NetworkManager keyfiles and private permissions](https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html)
- [NetworkManager dispatcher event contract](https://networkmanager.dev/docs/api/latest/NetworkManager-dispatcher.html)

These describe supported configuration mechanisms. They do not prove that a particular home AP, school socket or VPS is currently reachable.

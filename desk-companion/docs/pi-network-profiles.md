# Pi networking across home, classroom and dorm

**31 October latest: Pi work is paused by the owner. The results below are preserved checkpoints; resume hardware only on a new owner instruction. Active personal-agent software is [PR74](https://github.com/tantalum666/FYP/pull/74).**

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

This avoids carrying the old classroom-only subnet rule into every location. It does not bridge separate campus VLANs or make a sleeping/disconnected computer reachable. Mac and Pi must have a permitted route between them; the existing connector checks the direct LAN rather than trying through a VPN by accident. A VPS relay is a separate option if actual campus isolation makes it necessary.

Current wireless country input is `CN` for the home session. When physically back in Hong Kong, check/set the WLAN country to `HK` before Wi-Fi acceptance. Wired DHCP is independent of that setting. No MAC cloning, account guessing, router admin changes or campus-security bypass is included.

## Card update and rollback

[`prepare_network_sd.py`](../scripts/pi/prepare_network_sd.py) reads Wi-Fi credentials from an owner-private local file, never from command arguments. It verifies the original removable card using capacity, boot-volume UUID and Linux root PARTUUID. The Mac's internal SD reader reports Internal=true and RemovableMedia=true, so disk-number or external-only guesses are not used.

Preparation saves private copies of the five existing boot files. `--apply` changes only `user-data` and `meta-data`, independently reads back their exact bytes, and verifies that `network-config`, `config.txt` and `cmdline.txt` are unchanged. A second-file failure restores the original seed. The Mac does not write the Linux/application partition. A new NoCloud instance runs the network update once; users/SSH-host-key regeneration, package updates and reinstall are disabled.

The rendered boot seed contains a Wi-Fi credential and must remain private, like the existing personal image and NetworkManager files. Repository evidence contains only redacted status and source code. Private backups and credentials are under the owner's `~/.config/desk-companion/pi5-home/`, not Git. The Pi also preserves its original guard/unit as `.before-portable-network` files.

## Connect and verify

Use the existing paired-key launcher, with `DESK_PI_LINK=lan` and the Pi's observed address or `desk-companion.local`. The Mac forwards web port8891 to Pi127.0.0.1:8831 and desktop5901 to Pi127.0.0.1:5900. The known SSH host identity must match; do not delete it to bypass a mismatch.

The initial update emits nonce-filtered, nonsecret address/status packets to the Mac for one bounded startup window. A packet is only a discovery hint, not authenticated completion. Confirm the pinned SSH host, actual active profile/IP, service listeners and app health independently. If no packet arrives, inspect the actual LAN/mDNS or the card's `desk-network-status.json`; do not infer Wi-Fi success from the prepared files.

Status and real acceptance are tracked in [this session's QA](../../output/qa/2026-10-31-pi-home-resume/verification.md). The current software main and the Pi's older installed app remain distinct until an explicit backed-up software update is completed. No paid-model budget is reopened by restoring networking.

## Live acceptance on 31 October

The owner reinserted the original card and powered the Pi without Ethernet. Its home profile connected; the supplied SSID was compared privately, the original SSH host identity matched, and the actual app and VNC listeners remained on loopback. Mac-side owner login, rendered Alice/device page and Screen Sharing all passed. NetworkManager readback confirms the table above, including disabled Student/Halls autoconnect. No cable was present at the last observation; wired DHCP and school reachability remain untested.

The current home address was192.168.0.105 after profile activation; mDNS initially reported a different lease, so this is not a static-IP setting. The running tunnel uses the existing paired-key connector and local ports8891/5901. The initial diagnostic UDP window had no packet because discovery continued separately; its empty result did not establish a failed boot.

Two OS-level observations remain explicit: cloud-init finished with no fatal errors but a recoverable missing `cc_netplan_nm_patch` warning, matching an [official issue report](https://github.com/raspberrypi/trixie-feedback/issues/45); `raspi-config` country command returned1, while both the global regulatory domain and persisted `cfg80211.ieee80211_regdom=CN` argument were read back. Mac did not modify cmdline.txt; the authorized Pi-side country setter did. The warning was not concealed by changing vendor cloud-init configuration or rerunning provisioning.

Starting Pi-local Chromium produced an undervoltage warning confirmed in the kernel log. Its window was closed; later `0x50000` records historical undervoltage/throttling rather than active flags. Boot-reported supply capability is3000mA, not a measurement of current draw or proof of the physical PSU's rating. Confirm the supply/cable before the next bounded load test or software upgrade. Never force a higher USB-current limit or suppress voltage warnings to pass acceptance. [Official power guidance](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply), [status-bit meanings](https://www.raspberrypi.com/documentation/computers/os.html#get_throttled).

## Primary references

- [Raspberry Pi cloud-init boot files](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/)
- [Raspberry Pi configuration](https://www.raspberrypi.com/documentation/computers/configuration.html)
- [NetworkManager keyfiles and private permissions](https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html)
- [NetworkManager dispatcher event contract](https://networkmanager.dev/docs/api/latest/NetworkManager-dispatcher.html)

These describe supported configuration mechanisms. They do not prove that a particular home AP, school socket or VPS is currently reachable.

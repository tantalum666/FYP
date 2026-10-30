# Group 2 Current Handoff

31 October 2026, Asia/Shanghai. **Home Wi-Fi, pinned-key SSH, the Pi-served web app and Mac Screen Sharing have passed live checks.** A real undervoltage event occurred when starting Pi-local Chromium; power remains the next gate. [Draft PR73](https://github.com/tantalum666/FYP/pull/73) publishes network source `bdd9c6d` and sanitized evidence; it is not merged. Current branch: `codex/pi-home-resume-20261031` in `/Users/tantalum/.codex/worktrees/all-pr-review-20261030/FYP`, based on merged main `dac527b` (PR5/PR72 complete).

## Prepared and written

[Network contract](desk-companion/docs/pi-network-profiles.md), [QA](output/qa/2026-10-31-pi-home-resume/verification.md) and [reading scope](output/qa/2026-10-31-pi-home-resume/reading-record.json). Existing128GB SD identity, root partition and recorded paired SSH public key match. After private backups, only user-data/meta-data were changed and independently read back; config.txt/cmdline.txt/network-config and the Linux partition were not written by Mac. FAT read-only check returned0; card safely ejected.

Actual profiles read back: home Wi-Fi metric50, wired DHCP100, classroom NETGEAR02 Wi-Fi600; all three autoconnect. Student/Halls credentials remain but autoconnect is off. The owned SSH guard follows admitted active private LANs and keeps original key-only authentication/USB access. App/VNC stay loopback.25local Pi checks plus Ruff passed during preparation; this continuation changed documentation/evidence only. Ethernet is configured but untested; `eth0` last had no carrier.

A generic Mac launcher is now `~/Downloads/Desk-Companion-Pi5/Connect-Pi-over-LAN.command`, reusing the existing pairing/route checks. The paired key and known_hosts remain under `~/.config/desk-companion/pi5-usb/`. Home preparation/credential-bearing backups are only under `~/.config/desk-companion/pi5-home/`; do not print or publish them.

## Current live status and boundaries

Owner confirmed reinsertion/power. mDNS found the Pi; its address changed during activation from `.101` to **192.168.0.105**, reached directly via Mac `en0`. The original pinned host key matched. Home SSID equality was checked privately; `FYP-Home` connected, boot phase `network_ready`, API health `ok`, app/VNC services active. The current SSH tunnel exposes [web](http://127.0.0.1:8891/) and desktop `vnc://127.0.0.1:5901`; retain its terminal while using them. The browser tab was left available. DHCP addresses can change; rediscover before reconnecting.

The Pi's own browser rendered the device page after cancelling an unsolicited new-keyring password prompt; no keyring/password was created. The kernel then recorded undervoltage at04:29:57, normalized at04:29:59. Chromium's window was closed. Subsequent `get_throttled=0x50000` has historical undervoltage/throttling bits, no current flags; a one-off rail reading was5.04242V. Boot-reported supply capability is3000mA, actual PSU/cable type awaits the owner. This is not sustained-load acceptance; avoid further browser/media load or app/database upgrades until power is checked.

`cloud-init` finished with errors=[] and a recoverable missing `cc_netplan_nm_patch` warning (`degraded done`, exit2); same symptom is documented in the [official OS tracker](https://github.com/raspberrypi/trixie-feedback/issues/45). The country command returned1, but global regulatory domain and persisted boot argument both read CN. Neither warning was hidden by rerunning provisioning, editing vendor configuration or clearing flags.

The user-referenced VPS chat was read during preparation. No VPS, Mac proxy or VPN configuration was changed. Old paid-model rounds remain closed. No microphone/camera/arm activation or latest-main app/database upgrade was performed. The Pi still runs its Oct22 app plus Oct26 repairs; networking, software merge and device deployment are separate facts. Private diagnostic JSON and actual GUI screenshots are under `~/.config/desk-companion/pi5-home/`; only selected nonsecret evidence is published.

## One next step

Confirm the owner's present PSU/cable, correct the supply if needed, then perform one bounded power/stability retest. An optional home-router Ethernet test was also offered; no reply/cable was observed. Do not record classroom/dorm Ethernet acceptance without onsite evidence. Preserve the original card/data and do not reflash as a shortcut.

Current software main already includes PR5 retained Work/canonical memory and explicit schema migrations. Read [migration contract](desk-companion/docs/pr5-integration.md) before any later Pi app update; preserve a coherent stopped-store backup. [Personal-agent research](research/personal-agent-research-index.md) remains the route for mailbox/consumer-task goals after this Pi work.

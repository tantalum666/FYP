# Group 2 Current Handoff

31 October 2026, Asia/Shanghai. The owner has **resumed Pi work** at home and requested home Wi-Fi, classroom Wi-Fi plus wired Ethernet, and dorm Ethernet. [Draft PR73](https://github.com/tantalum666/FYP/pull/73) publishes sourcebdd9c6d and sanitized evidence; it is not merged. Current branch: `codex/pi-home-resume-20261031` in `/Users/tantalum/.codex/worktrees/all-pr-review-20261030/FYP`, based on merged main `dac527b` (PR5/PR72 complete).

## Prepared and written

[Network contract](desk-companion/docs/pi-network-profiles.md), [QA](output/qa/2026-10-31-pi-home-resume/verification.md) and [reading scope](output/qa/2026-10-31-pi-home-resume/reading-record.json). Existing128GB SD identity, root partition and recorded paired SSH public key match. After private backups, only user-data/meta-data were changed and independently read back; config.txt/cmdline.txt/network-config and the Linux partition were not written by Mac. FAT read-only check returned0; card safely ejected.

Home Wi-Fi is stored privately. FYP-Wired uses DHCP/autoconnect; prior classroom NETGEAR02 stays enabled; Student/Halls credentials remain but autoconnect is off. The owned SSH guard follows admitted active private LANs and keeps original key-only authentication/USB access. App/VNC stay loopback.25local Pi checks plus Ruff pass; these are not onsite Ethernet or new live Wi-Fi results.

A generic Mac launcher is now `~/Downloads/Desk-Companion-Pi5/Connect-Pi-over-LAN.command`, reusing the existing pairing/route checks. The paired key and known_hosts remain under `~/.config/desk-companion/pi5-usb/`. Home preparation/credential-bearing backups are only under `~/.config/desk-companion/pi5-home/`; do not print or publish them.

## Current live status and boundaries

Owner was asked to reinsert the ejected card and power the Pi using home Wi-Fi first. No new Pi address, SSH connection or app result has yet been verified. The initial bounded UDP observer received no matching packet in its window; this does not establish a failed boot. Start a fresh bounded observer or resolve the Pi when power is confirmed. A diagnostic packet is only discovery; verify the pinned SSH key independently.

Read the user-referenced VPS chat before relying on it. No VPS, Mac proxy or VPN configuration was changed. Old paid-model rounds remain closed. No microphone/camera/arm activation or latest-main app/database upgrade was performed. The Pi still has its earlier app until independently inspected and updated; networking, software merge and device deployment are separate facts.

## One next step

After the owner confirms power, verify home Wi-Fi and pinned-key SSH, then independently read app health and desktop listeners through the existing loopback tunnels. Inspect the boot status if discovery fails; preserve the current card/data and do not reflash as a shortcut.

Current software main already includes PR5 retained Work/canonical memory and explicit schema migrations. Read [migration contract](desk-companion/docs/pr5-integration.md) before any later Pi app update; preserve a coherent stopped-store backup. [Personal-agent research](research/personal-agent-research-index.md) remains the route for mailbox/consumer-task goals after this Pi work.
